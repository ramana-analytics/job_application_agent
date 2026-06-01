"""
Main FastAPI application — Resume + Job Tracker v2.0
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.auth import register_user, login_user, validate_token, logout_user
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid
import subprocess
import re
import tempfile

from app import storage
from app.job_scraper import scrape_job_description, parse_job_description_from_html
from app.resume_parser import (
    ensure_compilable_latex_source,
    extract_resume_text,
    save_resume_as_pdf,
    save_resume_as_docx,
    convert_resume,
)
from app.resume_manager import (
    create_resume_entry, list_resumes, get_resume,
    update_resume_text, update_resume_tags, archive_resume,
    delete_resume, reanalyze_resume,
    get_resume_semantic_text,
)
from app.job_tracker import (
    add_job, list_jobs, get_job, update_job_status,
    update_job_match, update_job, delete_job, get_job_stats,
)
from app.ats_checker import check_ats_compatibility
from app.tailoring import tailor_resume, generate_cover_letter_with_meta
from app.copilot_integration import gh_copilot_suggest_with_meta
from app.copilot_integration import get_available_models

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Resume & Job Tracker", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _is_latex_resume(resume: dict) -> bool:
    if not resume:
        return False
    if (resume.get("source_format") or "").lower() == "latex":
        return True
    paths = [resume.get("file_path"), resume.get("original_file_path"), resume.get("updated_file_path")]
    return any(str(path or "").lower().endswith(".tex") for path in paths)


def _resume_file_path(resume: dict, kind: str = "current") -> str:
    if kind == "original":
        return resume.get("original_file_path") or resume.get("file_path") or ""
    if kind == "updated":
        return resume.get("updated_file_path") or resume.get("file_path") or ""
    return resume.get("updated_file_path") or resume.get("file_path") or ""


def _resume_prompt_text(resume: dict) -> str:
    if not resume:
        return ""
    if _is_latex_resume(resume):
        return (resume.get("text") or "").strip()
    return get_resume_semantic_text(resume)


def _latex_install_hints(missing_files: list[str]) -> list[str]:
    """Map common missing LaTeX style files to practical tlmgr install commands."""
    if not missing_files:
        return []

    sty_to_pkg = {
        "fontawesome5.sty": "fontawesome5",
        "enumitem.sty": "enumitem",
        "hyperref.sty": "hyperref",
        "geometry.sty": "geometry",
        "xcolor.sty": "xcolor",
        "titlesec.sty": "titlesec",
        "fancyhdr.sty": "fancyhdr",
        "tabularx.sty": "tabularx",
        "parskip.sty": "parskip",
        "ragged2e.sty": "ragged2e",
        "microtype.sty": "microtype",
        "setspace.sty": "setspace",
        "lastpage.sty": "lastpage",
        "bookmark.sty": "bookmark",
        "iftex.sty": "iftex",
    }

    hints = []
    seen = set()
    for item in missing_files:
        package = sty_to_pkg.get(item.strip().lower())
        if not package:
            package = Path(item).stem
        if package in seen:
            continue
        seen.add(package)
        hints.append(f"tlmgr install {package}")

    if hints:
        hints.append("If tlmgr needs admin rights: sudo tlmgr install <package>")
    return hints


def _latex_failure_excerpt(log: str) -> str:
    """Return a focused compile excerpt centered on the last LaTeX error line."""
    lines = [line.rstrip() for line in (log or "").splitlines()]
    if not lines:
        return "No compiler output captured."

    err_indexes = [i for i, line in enumerate(lines) if line.startswith("! ")]
    if err_indexes:
        idx = err_indexes[-1]
        start = max(0, idx - 10)
        end = min(len(lines), idx + 24)
        return "\n".join(lines[start:end])

    # Fallback: show the tail where fatal stops usually appear.
    return "\n".join(lines[-180:])


def _extract_latex_errors(log: str) -> list[dict]:
    """Extract structured LaTeX errors with best-effort line numbers."""
    lines = [line.rstrip() for line in (log or "").splitlines()]
    errors: list[dict] = []

    for idx, line in enumerate(lines):
        if not line.startswith("! "):
            continue

        message = line[2:].strip() or "LaTeX error"
        line_no = None
        context = ""

        for look_ahead in lines[idx + 1: idx + 8]:
            match = re.match(r"^l\.(\d+)\s?(.*)$", look_ahead.strip())
            if match:
                line_no = int(match.group(1))
                context = (match.group(2) or "").strip()
                break

        errors.append({"line": line_no, "message": message, "context": context})

    return errors


def _create_tailored_resume_entry(
    *,
    source_resume: dict,
    tailored_text: str,
    filename_suffix: str = "_tailored",
) -> dict:
    """Persist a tailored copy of a resume as a brand-new entry."""
    base_name = Path(source_resume.get("filename") or "resume").stem
    source_format = (source_resume.get("source_format") or "").lower()
    is_latex = _is_latex_resume(source_resume)
    file_ext = ".tex" if is_latex else ".txt"
    derived_filename = f"{base_name}{filename_suffix}{file_ext}"
    derived_path = UPLOAD_DIR / f"{uuid.uuid4()}_{derived_filename}"
    derived_path.write_text(tailored_text, encoding="utf-8")

    tags = list(source_resume.get("tags") or [])
    if "tailored" not in {tag.lower() for tag in tags}:
        tags.append("tailored")

    return create_resume_entry(
        filename=derived_filename,
        file_path=str(derived_path),
        resume_text=tailored_text,
        tags=tags,
        job_description="",
        source_format="latex" if is_latex else (source_format or file_ext.lstrip(".")),
    )


# ─── ROOT & AUTH PAGES ─────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/login", status_code=302)


@app.get("/app", include_in_schema=False)
async def app_page():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(BASE_DIR / "static" / "login.html")


# ─── AUTH API ───────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def api_register(data: dict = Body(...)):
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email    = (data.get("email") or "").strip()
    try:
        user = register_user(username, password, email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "username": user["username"]}


@app.post("/api/auth/login")
async def api_login(data: dict = Body(...)):
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    token = login_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"token": token, "username": username}


@app.post("/api/auth/logout")
async def api_logout(data: dict = Body(...)):
    token = (data.get("token") or "").strip()
    if token:
        logout_user(token)
    return {"ok": True}


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    token = (
        request.headers.get("X-Auth-Token")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    user = validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ─── RESUMES ────────────────────────────────────────────────────────────────

@app.get("/api/resumes")
async def api_list_resumes(include_archived: bool = False):
    return list_resumes(include_archived=include_archived)


@app.post("/api/resumes/upload")
async def api_upload_resume(
    file: UploadFile = File(...),
    tags: str = Form(""),
    job_description: str = Form(""),
):
    filename = file.filename or "resume"
    ext = Path(filename).suffix.lower()
    allowed = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/x-tex",
        "text/x-tex",
    }
    if ext not in {".pdf", ".docx", ".txt", ".tex"} and file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT, or LaTeX (.tex) files are supported")

    file_path = UPLOAD_DIR / f"{datetime.now().timestamp()}_{filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    resume_text = extract_resume_text(str(file_path))
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    source_format = "latex" if ext == ".tex" else ext.lstrip(".")

    entry = create_resume_entry(
        filename=filename,
        file_path=str(file_path),
        resume_text=resume_text,
        tags=tag_list,
        job_description=job_description,
        source_format=source_format,
    )
    return entry


@app.get("/api/resumes/{resume_id}")
async def api_get_resume(resume_id: str):
    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r


@app.patch("/api/resumes/{resume_id}/text")
async def api_update_resume_text(resume_id: str, text: str = Body(..., embed=True)):
    r = update_resume_text(resume_id, text)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r


@app.patch("/api/resumes/{resume_id}/tags")
async def api_update_tags(resume_id: str, tags: list = Body(..., embed=True)):
    r = update_resume_tags(resume_id, tags)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r


@app.patch("/api/resumes/{resume_id}/archive")
async def api_archive_resume(resume_id: str, archived: bool = Body(..., embed=True)):
    r = archive_resume(resume_id, archived)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r


@app.delete("/api/resumes/{resume_id}")
async def api_delete_resume(resume_id: str):
    ok = delete_resume(resume_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"deleted": True}


@app.post("/api/resumes/{resume_id}/ats")
async def api_reanalyze_ats(resume_id: str, job_description: str = Body("", embed=True)):
    r = reanalyze_resume(resume_id, job_description)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r["ats_analysis"]


@app.post("/api/resumes/{resume_id}/export")
async def api_export_resume(resume_id: str, payload: dict = Body(default={})):
    fmt = (payload.get("fmt") or "docx").strip().lower()
    job_id = (payload.get("job_id") or "").strip() or None
    if fmt not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported export format")

    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")

    export_id = str(uuid.uuid4())
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(r.get("filename") or f"resume_{resume_id}").stem.replace(" ", "_")
    export_filename = f"{stamp}_{safe_name}_{fmt}.{fmt}"
    export_path = UPLOAD_DIR / export_filename

    if _is_latex_resume(r):
        source_path = _resume_file_path(r, "updated") or _resume_file_path(r, "original")
        if not source_path:
            raise HTTPException(status_code=400, detail="LaTeX source is missing")
        convert_resume(source_path, str(export_path), fmt)
    else:
        if fmt == "pdf":
            save_resume_as_pdf(r["text"], str(export_path))
        else:
            save_resume_as_docx(r["text"], str(export_path))

    job = get_job(job_id) if job_id else None
    storage.save_application_file(
        {
            "id": export_id,
            "resume_id": resume_id,
            "resume_filename": r.get("filename") or "",
            "job_id": job_id,
            "job_title": (job or {}).get("job_title", ""),
            "company": (job or {}).get("company", ""),
            "format": fmt,
            "file_path": str(export_path),
            "file_name": export_filename,
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    return FileResponse(export_path, filename=export_filename)


@app.post("/api/resumes/{resume_id}/compile-pdf")
async def api_compile_latex_pdf(resume_id: str, payload: dict = Body(default={})):
    job_id = (payload.get("job_id") or "").strip() or None
    source_text = payload.get("source_text")

    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not _is_latex_resume(r):
        raise HTTPException(status_code=400, detail="Compile PDF is only available for LaTeX resumes")

    # Compile exactly what is in the editor, even if user did not click Save.
    if isinstance(source_text, str):
        updated = update_resume_text(resume_id, source_text)
        if not updated:
            raise HTTPException(status_code=404, detail="Resume not found")
        r = updated

    source_path = _resume_file_path(r, "updated") or _resume_file_path(r, "original")
    if not source_path:
        raise HTTPException(status_code=400, detail="LaTeX source file is missing")

    source = Path(source_path)
    if not source.exists():
        raise HTTPException(status_code=404, detail="LaTeX source file not found on disk")

    raw_source = source.read_text(encoding="utf-8")
    normalized_source = ensure_compilable_latex_source(
        raw_source,
        Path(r.get("filename") or source.stem).stem,
    )
    if normalized_source != raw_source:
        updated = update_resume_text(resume_id, normalized_source)
        if not updated:
            raise HTTPException(status_code=404, detail="Resume not found")
        r = updated
        source_path = _resume_file_path(r, "updated") or _resume_file_path(r, "original")
        source = Path(source_path)

    export_id = str(uuid.uuid4())
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(r.get("filename") or f"resume_{resume_id}").stem.replace(" ", "_")
    export_filename = f"{stamp}_{safe_name}_compiled.pdf"
    export_path = UPLOAD_DIR / export_filename

    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={UPLOAD_DIR}",
        str(source),
    ]

    try:
        run = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="pdflatex is not installed. Install a LaTeX distribution first.")
    except subprocess.CalledProcessError as err:
        log = ((err.stdout or "") + "\n" + (err.stderr or "")).strip()
        excerpt = _latex_failure_excerpt(log)
        missing = re.findall(r"LaTeX Error: File `([^`]+)` not found", log)
        hint = ""
        if missing:
            hint = "\nMissing packages/files: " + ", ".join(sorted(set(missing)))
        install_hints = _latex_install_hints(missing)
        if install_hints:
            hint += "\n\nInstall hints (MacTeX tlmgr):\n- " + "\n- ".join(install_hints)
        detail = (
            "LaTeX compilation failed.\n\n"
            "Most relevant compiler excerpt:\n"
            f"{excerpt}{hint}"
        ).strip()
        # Keep the end of the message if truncation is needed.
        raise HTTPException(status_code=400, detail=detail[-12000:])

    produced_pdf = UPLOAD_DIR / f"{source.stem}.pdf"
    if not produced_pdf.exists():
        raise HTTPException(status_code=500, detail="Compilation completed but no PDF was produced")

    produced_pdf.replace(export_path)

    job = get_job(job_id) if job_id else None
    storage.save_application_file(
        {
            "id": export_id,
            "resume_id": resume_id,
            "resume_filename": r.get("filename") or "",
            "job_id": job_id,
            "job_title": (job or {}).get("job_title", ""),
            "company": (job or {}).get("company", ""),
            "format": "pdf",
            "source": "latex_compile",
            "file_path": str(export_path),
            "file_name": export_filename,
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    return {
        "ok": True,
        "file_id": export_id,
        "download_url": f"/api/application-files/{export_id}/download",
        "preview_url": f"/api/application-files/{export_id}/preview",
        "file_name": export_filename,
        "compiler_output": (run.stdout or "")[-4000:],
    }


@app.post("/api/resumes/{resume_id}/latex-errors")
async def api_latex_errors(resume_id: str, payload: dict = Body(default={})):
    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not _is_latex_resume(r):
        return {"ok": True, "errors": []}

    source_text = payload.get("source_text")
    source_path = _resume_file_path(r, "updated") or _resume_file_path(r, "original")
    if not source_path:
        return {"ok": False, "errors": [{"line": None, "message": "LaTeX source file is missing", "context": ""}]}

    source = Path(source_path)
    if isinstance(source_text, str):
        raw_source = source_text
    else:
        if not source.exists():
            return {"ok": False, "errors": [{"line": None, "message": "LaTeX source file not found on disk", "context": ""}]}
        raw_source = source.read_text(encoding="utf-8")

    normalized_source = ensure_compilable_latex_source(
        raw_source,
        Path(r.get("filename") or source.stem).stem,
    )

    tex_name = Path(r.get("filename") or source.name or "main.tex").name
    if not tex_name.lower().endswith(".tex"):
        tex_name = f"{Path(tex_name).stem}.tex"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tex_path = tmp_path / tex_name
            tex_path.write_text(normalized_source, encoding="utf-8")

            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={tmp_path}",
                str(tex_path),
            ]
            run = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="pdflatex is not installed. Install a LaTeX distribution first.")

    log = ((run.stdout or "") + "\n" + (run.stderr or "")).strip()
    errors = _extract_latex_errors(log)
    return {
        "ok": run.returncode == 0 and not errors,
        "errors": errors,
        "excerpt": _latex_failure_excerpt(log) if errors else "",
    }


@app.get("/api/resumes/{resume_id}/file")
async def api_download_resume_file(resume_id: str, kind: str = "current"):
    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    file_path = _resume_file_path(r, kind)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Requested resume file not found")
    return FileResponse(file_path, filename=Path(file_path).name)


@app.get("/api/resumes/{resume_id}/preview-pdf")
async def api_preview_pdf(resume_id: str):
    """Serve a dynamic PDF preview for any resume (LaTeX, DOCX, or PDF)."""
    r = get_resume(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = _resume_file_path(r, "current")
    if not file_path or not Path(file_path).exists():
        file_path = _resume_file_path(r, "original")

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Resume file missing")

    path_obj = Path(file_path)
    ext = path_obj.suffix.lower()

    if ext == ".pdf":
        return FileResponse(file_path, media_type="application/pdf")

    if ext == ".tex":
        # Look for the last successfully compiled application file
        files = storage.get_all_application_files()
        latest = next((f for f in files if f.get("resume_id") == resume_id and (f.get("format") or "").lower() == "pdf"), None)
        if latest and Path(latest["file_path"]).exists():
            return FileResponse(latest["file_path"], media_type="application/pdf")
        # Try to compile if it's LaTeX? For simplicity here, just return 400 if not compiled
        raise HTTPException(status_code=400, detail="Please compile the LaTeX resume to view its PDF preview.")

    # Fallback: create PDF from plain text (for .txt, .docx, etc. if needed)
    preview_path = UPLOAD_DIR / f"preview_{resume_id}.pdf"
    save_resume_as_pdf(r.get("text") or "No content available", str(preview_path))
    return FileResponse(preview_path, media_type="application/pdf")


@app.get("/api/application-files")
async def api_list_application_files():
    files = storage.get_all_application_files()
    # Hide stale records pointing to removed files.
    return [f for f in files if Path(f.get("file_path", "")).exists()]


@app.get("/api/application-files/{file_id}/download")
async def api_download_application_file(file_id: str):
    record = storage.get_application_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application file not found")
    file_path = record.get("file_path") or ""
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Generated file is missing")
    return FileResponse(file_path, filename=record.get("file_name") or Path(file_path).name)


@app.get("/api/application-files/{file_id}/preview")
async def api_preview_application_file(file_id: str):
    record = storage.get_application_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application file not found")
    file_path = record.get("file_path") or ""
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Generated file is missing")
    media_type = "application/pdf" if str(record.get("format", "")).lower() == "pdf" else None
    return FileResponse(file_path, media_type=media_type)


@app.delete("/api/application-files/{file_id}")
async def api_delete_application_file(file_id: str):
    record = storage.get_application_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application file not found")
    file_path = record.get("file_path") or ""
    if file_path:
        p = Path(file_path)
        if p.exists():
            p.unlink(missing_ok=True)
    storage.delete_application_file(file_id)
    return {"deleted": True}


# ─── JOBS ───────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
async def api_list_jobs(status: Optional[str] = None):
    return list_jobs(status_filter=status)


@app.get("/api/jobs/stats")
async def api_job_stats():
    return get_job_stats()


@app.post("/api/jobs")
async def api_add_job(payload: dict = Body(...)):
    entry = add_job(
        job_title=payload.get("job_title", ""),
        company=payload.get("company", ""),
        job_url=payload.get("job_url", ""),
        description=payload.get("description", ""),
        resume_text=payload.get("resume_text", ""),
        **{k: v for k, v in payload.items()
           if k not in {"job_title", "company", "job_url", "description", "resume_text"}},
    )
    return entry


@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    j = get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@app.patch("/api/jobs/{job_id}/status")
async def api_update_job_status(job_id: str, status: str = Body(..., embed=True)):
    j = update_job_status(job_id, status)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@app.patch("/api/jobs/{job_id}")
async def api_update_job(job_id: str, fields: dict = Body(...)):
    j = update_job(job_id, fields)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@app.post("/api/jobs/{job_id}/match")
async def api_match_job(job_id: str, resume_id: str = Body(..., embed=True)):
    resume = get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    j = update_job_match(job_id, get_resume_semantic_text(resume))
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@app.delete("/api/jobs/{job_id}")
async def api_delete_job(job_id: str):
    ok = delete_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True}


@app.post("/api/jobs/{job_id}/copilot-fill")
async def api_copilot_fill_job(job_id: str, payload: dict = Body(default={})):
    j = get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")

    desc = (j.get("description") or "").strip()
    my_info = (payload.get("my_info") or j.get("my_info") or "").strip()
    resume_id = (payload.get("resume_id") or j.get("resume_id") or "").strip()

    if not desc and not my_info:
        raise HTTPException(status_code=400, detail="Job has no description or My Info to analyze")

    my_info_section = f"\nADDITIONAL CONTEXT FROM USER:\n{my_info}\n" if my_info else ""

    prompt = f"""You are an expert job analyst. Read the job posting below and return a single JSON object with exactly these keys.
Return ONLY valid JSON — no markdown, no code fences, no commentary.

JSON keys to populate:
- "summary": Few Paragraphs in plain-English summary of the role, Key skills required, and what makes it unique
- "job_title": official job title
- "company": company name
- "locations": array of location strings (e.g. ["Remote", "New York, NY"])
- "job_type": one of "fulltime", "contract", "parttime", "consulting", or ""
- "sponsorship_required": one of "yes", "no", or ""
- "salary_range": salary or compensation range as string (e.g. "$120k-$160k") or "" or any compensation info found
- "band_level": seniority band or level (e.g. "L5", "Senior", "Director") or ""
- "experience_requirements": years or type of experience required (e.g. "8+ years") or ""
- "deadline": application deadline in YYYY-MM-DD format or ""
{my_info_section}
JOB POSTING:
{desc[:3000]}

JSON:"""

    # Allow caller to request a specific Copilot model (e.g. to choose a cheaper model)
    model = (payload.get("model") or "").strip()
    cli_meta = gh_copilot_suggest_with_meta(prompt, model=model)
    raw = (cli_meta.get("stdout") or "").strip()

    # Parse JSON — strip markdown fences only if present, otherwise use raw directly
    import json, re as _re
    # Remove ```json ... ``` or ``` ... ``` blocks
    stripped = _re.sub(r"```[a-zA-Z]*\n?", "", raw).replace("```", "").strip()
    json_str = stripped if stripped else raw
    try:
        fields = json.loads(json_str)
    except Exception:
        # Try to find first {...} block as fallback
        m = _re.search(r"\{[\s\S]+\}", raw)
        try:
            fields = json.loads(m.group(0)) if m else {}
        except Exception:
            fields = {}

    my_info_lines = []
    if fields.get("summary"):
        my_info_lines.append(f"Summary: {fields['summary']}")
    if fields.get("job_title"):
        my_info_lines.append(f"Job Title: {fields['job_title']}")
    if fields.get("company"):
        my_info_lines.append(f"Company: {fields['company']}")
    if fields.get("locations"):
        my_info_lines.append(f"Locations: {', '.join(fields['locations'])}")
    if fields.get("job_type"):
        my_info_lines.append(f"Job Type: {fields['job_type']}")
    if fields.get("sponsorship_required"):
        my_info_lines.append(f"Sponsorship Required: {fields['sponsorship_required']}")
    if fields.get("salary_range"):
        my_info_lines.append(f"Salary Range: {fields['salary_range']}")
    if fields.get("band_level"):
        my_info_lines.append(f"Band/Level: {fields['band_level']}")
    if fields.get("experience_requirements"):
        my_info_lines.append(f"Experience: {fields['experience_requirements']}")
    if fields.get("deadline"):
        my_info_lines.append(f"Deadline: {fields['deadline']}")
    if my_info.strip():
        my_info_lines.append(f"User Notes:\n{my_info}")

    merged_my_info = "\n\n".join(my_info_lines).strip()
    if merged_my_info:
        fields["my_info"] = merged_my_info

    # Persist extracted fields back onto the job (excluding summary which is display-only)
    updatable = {
        k: fields[k] for k in [
            "job_title", "company", "locations", "job_type",
            "sponsorship_required", "salary_range", "band_level",
            "experience_requirements", "deadline",
        ] if k in fields and fields[k] not in (None, "", [])
    }
    if merged_my_info:
        updatable["my_info"] = merged_my_info
    if fields.get("summary"):
        updatable["copilot_summary"] = fields["summary"]
    if resume_id:
        updatable["resume_id"] = resume_id
    if updatable:
        update_job(job_id, updatable)

    return {
        "fields": fields,
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "model": cli_meta.get("model", "auto"),
            "model_info": cli_meta.get("model_info", {}),
            "tool": "copilot",
            "task": "copilot_fill_job",
        },
    }


# ─── SCRAPE ─────────────────────────────────────────────────────────────────

@app.post("/api/scrape")
async def api_scrape(url: str = Form(...)):
    data = scrape_job_description(url)
    if not data:
        raise HTTPException(status_code=400, detail="Could not scrape job posting")
    return data


@app.post("/api/scrape/html")
async def api_scrape_html(html_content: str = Form(...), source_url: str = Form("")):
    data = parse_job_description_from_html(html_content, source_url)
    if not data:
        raise HTTPException(status_code=400, detail="Could not parse HTML content")
    return data


# ─── ATS QUICK CHECK ────────────────────────────────────────────────────────

@app.post("/api/ats/check")
async def api_ats_check(payload: dict = Body(...)):
    return check_ats_compatibility(
        payload.get("resume_text", ""),
        payload.get("job_description", ""),
    )


@app.post("/api/ats/check-llm")
async def api_ats_check_llm(payload: dict = Body(...)):
    import json as _json
    resume_text = (payload.get("resume_text") or "").strip()
    job_description = (payload.get("job_description") or "").strip()
    model = (payload.get("model") or "").strip()

    prompt = (
        "You are an expert ATS resume analyzer. Return ONLY a valid JSON object — no markdown, "
        "no explanation, no code fences.\n\n"
        "Schema:\n"
        "{\n"
        '  "parsed_resume": {"name":"","contact":{},"sections":[],"skills":[],"work_experience":[]},\n'
        '  "job_description_analysis": {"required_skills":[],"preferred_skills":[],"key_responsibilities":[]},\n'
        '  "ats_score": {"score_percent":0,"breakdown":{"sections":0,"keywords":0,"formatting":0,"impact":0},"label":""},\n'
        '  "gap_analysis": {"missing_keywords":[],"weak_sections":[],"issues":[{"type":"","severity":"","message":"","proof":""}]},\n'
        '  "recommendations": {"priority":[],"quick_wins":[],"rewrites":[]}\n'
        "}\n\n"
        "Rules:\n"
        "- For every issue include a 'proof' field: a short verbatim excerpt from the resume, or the exact keyword/section name that is absent.\n"
        "- severity values: critical | high | medium | low\n"
        "- score_percent: 0-100 integer\n"
        "- Return nothing outside the JSON object.\n\n"
        f"RESUME:\n{resume_text[:20000]}\n\n"
        f"JOB DESCRIPTION:\n{job_description[:20000]}"
    )

    cli_meta = gh_copilot_suggest_with_meta(prompt, model=model)
    stdout = (cli_meta.get("stdout") or "").strip()

    if cli_meta.get("success") and stdout:
        # Strip accidental markdown code fences the LLM may add
        import re as _re2
        clean = _re2.sub(r"^```(?:json)?\s*|\s*```$", "", stdout, flags=_re2.DOTALL).strip()
        try:
            parsed = _json.loads(clean)
            score_data = parsed.get("ats_score", {})
            ats_score = int(score_data.get("score_percent", 0))
            gap = parsed.get("gap_analysis", {})
            issues = gap.get("issues", [])
            return {
                "ats_score": ats_score,
                "score": ats_score,
                "score_breakdown": score_data.get("breakdown", {}),
                "issues": issues,
                "keyword_analysis": {
                    "matched_keywords": [],
                    "missing_keywords": gap.get("missing_keywords", []),
                },
                "recommendations": parsed.get("recommendations", {}),
                "parsed_resume": parsed.get("parsed_resume", {}),
                "job_description_analysis": parsed.get("job_description_analysis", {}),
                "llm": True,
                "cli_status": {
                    "success": True,
                    "model": cli_meta.get("model", "auto"),
                    "model_info": cli_meta.get("model_info", {}),
                },
            }
        except Exception:
            fallback = check_ats_compatibility(resume_text, job_description)
            fallback["llm"] = False
            fallback["cli_status"] = {
                "success": False,
                "error": "invalid_llm_json",
                "raw_output": stdout[:2000],
                "model": cli_meta.get("model", "auto"),
            }
            return fallback

    # Copilot unavailable — deterministic fallback
    fallback = check_ats_compatibility(resume_text, job_description)
    fallback["llm"] = False
    fallback["cli_status"] = {
        "success": False,
        "error": cli_meta.get("stderr", "Copilot unavailable"),
        "model": cli_meta.get("model", "auto"),
    }
    return fallback


# ─── TAILORING ──────────────────────────────────────────────────────────────

@app.post("/api/tailor")
async def api_tailor(payload: dict = Body(...)):
    resume_id = payload.get("resume_id")
    job_id = payload.get("job_id")
    resume = get_resume(resume_id) if resume_id else None
    job = get_job(job_id) if job_id else None
    resume_text = _resume_prompt_text(resume) or payload.get("resume_text", "")
    job_description = (job or {}).get("description") or payload.get("job_description", "")
    sections = (job or {}).get("sections", {})
    model = (payload.get("model") or "").strip()
    return tailor_resume(resume_text, job_description, sections, None, model=model)


@app.post("/api/cover-letter")
async def api_cover_letter(payload: dict = Body(...)):
    resume_id = payload.get("resume_id")
    job_id = payload.get("job_id")
    resume = get_resume(resume_id) if resume_id else None
    job = get_job(job_id) if job_id else None
    resume_text = get_resume_semantic_text(resume) or payload.get("resume_text", "")
    job_description = (job or {}).get("copilot_summary") or (job or {}).get("description") or payload.get("job_description", "")
    company = (job or {}).get("company") or payload.get("company", "the company")
    job_title = (job or {}).get("job_title") or payload.get("job_title", "the role")
    my_info = (job or {}).get("my_info") or payload.get("my_info", "")
    if my_info:
        job_description = f"{job_description}\n\nAdditional context:\n{my_info}"
    model = (payload.get("model") or "").strip()
    result = generate_cover_letter_with_meta(
        resume_text=resume_text,
        job_description=job_description,
        company_name=company,
        job_title=job_title,
        candidate_name="",
        model=model,
    )
    if job_id and resume_id:
        update_job(job_id, {"resume_id": resume_id, "cover_letter": result.get("cover_letter", "")})
    return result


@app.post("/api/jobs/{job_id}/recommendations")
async def api_job_recommendations(job_id: str, payload: dict = Body(default={})): 
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_id = (payload.get("resume_id") or job.get("resume_id") or "").strip()
    resume = get_resume(resume_id) if resume_id else None
    resume_text = get_resume_semantic_text(resume) or payload.get("resume_text", "")
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume is required for recommendations")

    job_summary = job.get("copilot_summary") or job.get("description") or ""
    my_info = payload.get("my_info") or job.get("my_info") or ""

    prompt = f"""You are a senior resume strategist.

Based on the JOB SUMMARY and the CURRENT RESUME, write concise ATS-friendly recommendations for how to improve the resume for this role.
Return plain text only. Use 5-8 bullet points. Be specific and practical.

JOB SUMMARY:
{job_summary[:2200]}

CURRENT RESUME:
{resume_text[:3000]}

ADDITIONAL CONTEXT:
{my_info[:1500]}
"""

    model = (payload.get("model") or "").strip()
    cli_meta = gh_copilot_suggest_with_meta(prompt, model=model)
    recommendations = cli_meta.get("stdout", "") if cli_meta.get("success") else ""
    if recommendations:
        updatable = {"resume_recommendations": recommendations}
        if resume_id:
            updatable["resume_id"] = resume_id
        update_job(job_id, updatable)

    return {
        "recommendations": recommendations,
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "model": cli_meta.get("model", "auto"),
            "tool": "copilot",
            "task": "resume_recommendations",
        },
    }


@app.post("/api/jobs/{job_id}/recommendations/apply")
async def api_apply_job_recommendations(job_id: str, payload: dict = Body(default={})): 
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_id = (payload.get("resume_id") or job.get("resume_id") or "").strip()
    if not resume_id:
        raise HTTPException(status_code=400, detail="Resume is required")

    source_resume = get_resume(resume_id)
    if not source_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_text = _resume_prompt_text(source_resume)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume content is required")

    recommendations = (payload.get("recommendations") or job.get("resume_recommendations") or "").strip()
    if not recommendations:
        raise HTTPException(status_code=400, detail="Recommendations are required")

    job_summary = job.get("copilot_summary") or job.get("description") or ""
    is_latex = _is_latex_resume(source_resume)

    prompt = f"""You are an expert resume editor.

TASK:
Revise the CURRENT RESUME using the RECOMMENDATIONS and JOB SUMMARY below.

RULES:
- Keep only real facts from the current resume.
- Strengthen wording, impact, and ATS alignment.
- Do not invent experience or skills.
- If the current resume is LaTeX, return a complete valid LaTeX source document.
- If the current resume is plain text, return a polished plain text resume.
- Return only the updated resume content.

JOB SUMMARY:
{job_summary[:2200]}

RECOMMENDATIONS:
{recommendations[:2500]}

CURRENT RESUME:
{resume_text[:4000]}

UPDATED RESUME:"""

    cli_meta = gh_copilot_suggest_with_meta(prompt)
    tailored_text = cli_meta.get("stdout", "") if cli_meta.get("success") else ""
    if not tailored_text:
        raise HTTPException(status_code=500, detail="Copilot could not generate an updated resume")

    new_resume = _create_tailored_resume_entry(
        source_resume=source_resume,
        tailored_text=tailored_text,
    )

    update_job(job_id, {"resume_id": new_resume.get("id", "")})

    return {
        "resume": new_resume,
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "model": cli_meta.get("model", "auto"),
            "tool": "copilot",
            "task": "apply_resume_recommendations",
        },
    }


@app.post("/api/copilot/prompt")
async def api_copilot_prompt(payload: dict = Body(...)):
    prompt = (payload.get("prompt") or "").strip()
    model = (payload.get("model") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    cli_meta = gh_copilot_suggest_with_meta(prompt, model=model)
    return {
        "result": cli_meta.get("stdout", "") if cli_meta.get("success") else "",
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "model": cli_meta.get("model", "auto"),
            "tool": "copilot",
            "task": "prompt_window",
        },
    }


@app.get("/api/copilot/models")
async def api_copilot_models():
    """Return available Copilot models and their metadata for the UI."""
    return get_available_models()


# ─── SETTINGS ───────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def api_get_settings():
    return storage.get_settings()


@app.put("/api/settings")
async def api_save_settings(settings: dict = Body(...)):
    return storage.save_settings(settings)


# ─── HEALTH ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.exception_handler(HTTPException)
async def http_err(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
