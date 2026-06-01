"""
Resume manager — CRUD + versioning on top of the JSON storage layer.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app import storage
from app.resume_parser import ensure_compilable_latex_source, latex_source_to_plain_text
from app.ats_checker import check_ats_compatibility

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def create_resume_entry(
    filename: str,
    file_path: str,
    resume_text: str,
    tags: Optional[List[str]] = None,
    job_description: str = "",
    source_format: str = "",
) -> Dict:
    """Create and persist a new resume entry."""
    resume_id = str(uuid.uuid4())
    is_latex = source_format == "latex" or file_path.lower().endswith(".tex")
    if is_latex:
        resume_text = ensure_compilable_latex_source(resume_text, Path(filename or file_path).stem)
    plain_text = latex_source_to_plain_text(resume_text) if is_latex else resume_text
    updated_file_path = ""
    if is_latex:
        updated_file_path = str(UPLOAD_DIR / f"{resume_id}_updated.tex")
        Path(updated_file_path).write_text(resume_text, encoding="utf-8")

    ats = check_ats_compatibility(plain_text, job_description)
    entry = {
        "id": resume_id,
        "filename": filename,
        "file_path": file_path,
        "original_file_path": file_path,
        "updated_file_path": updated_file_path,
        "source_format": "latex" if is_latex else (source_format or Path(file_path).suffix.lower().lstrip(".")),
        "version": 1,
        "tags": tags or [],
        "archived": False,
        "text": resume_text,
        "plain_text": plain_text,
        "ats_score": ats["score"],
        "ats_analysis": ats,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return storage.save_resume(entry)


def list_resumes(include_archived: bool = False) -> List[Dict]:
    resumes = storage.get_all_resumes()
    if not include_archived:
        resumes = [r for r in resumes if not r.get("archived", False)]
    return resumes


def get_resume(resume_id: str) -> Optional[Dict]:
    return storage.get_resume(resume_id)


def update_resume_text(resume_id: str, new_text: str) -> Optional[Dict]:
    """Save edited resume text, bumping version."""
    resume = storage.get_resume(resume_id)
    if not resume:
        return None
    is_latex = resume.get("source_format") == "latex" or str(resume.get("original_file_path") or resume.get("file_path") or "").lower().endswith(".tex")
    if is_latex:
        new_text = ensure_compilable_latex_source(new_text, Path(resume.get("filename") or resume_id).stem)
    resume["text"] = new_text
    resume["version"] = resume.get("version", 1) + 1
    resume["updated_at"] = datetime.utcnow().isoformat()
    if is_latex:
        updated_path = resume.get("updated_file_path") or str(UPLOAD_DIR / f"{resume_id}_updated.tex")
        Path(updated_path).write_text(new_text, encoding="utf-8")
        resume["updated_file_path"] = updated_path
        resume["source_format"] = "latex"
        resume["plain_text"] = latex_source_to_plain_text(new_text)
        ats_source = resume["plain_text"]
    else:
        resume["plain_text"] = new_text
        ats_source = new_text
    resume["ats_analysis"] = check_ats_compatibility(ats_source)
    resume["ats_score"] = resume["ats_analysis"]["score"]
    return storage.save_resume(resume)


def update_resume_tags(resume_id: str, tags: List[str]) -> Optional[Dict]:
    resume = storage.get_resume(resume_id)
    if not resume:
        return None
    resume["tags"] = tags
    resume["updated_at"] = datetime.utcnow().isoformat()
    return storage.save_resume(resume)


def archive_resume(resume_id: str, archived: bool = True) -> Optional[Dict]:
    return storage.archive_resume(resume_id, archived)


def delete_resume(resume_id: str) -> bool:
    resume = storage.get_resume(resume_id)
    if resume:
        for raw_path in {
            resume.get("file_path"),
            resume.get("original_file_path"),
            resume.get("updated_file_path"),
        }:
            if raw_path:
                p = Path(raw_path)
                if p.exists():
                    p.unlink(missing_ok=True)
    return storage.delete_resume(resume_id)


def reanalyze_resume(resume_id: str, job_description: str = "") -> Optional[Dict]:
    """Re-run ATS check against a new or updated job description."""
    resume = storage.get_resume(resume_id)
    if not resume:
        return None
    ats = check_ats_compatibility(resume.get("plain_text") or resume["text"], job_description)
    resume["ats_analysis"] = ats
    resume["ats_score"] = ats["score"]
    resume["updated_at"] = datetime.utcnow().isoformat()
    return storage.save_resume(resume)


def get_resume_semantic_text(resume: Optional[Dict]) -> str:
    return (resume or {}).get("plain_text") or (resume or {}).get("text") or ""
