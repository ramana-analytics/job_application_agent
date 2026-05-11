"""
Thread-safe JSON file storage layer.
All data lives in ./data/*.json — no database required.
"""
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Per-file locks for thread-safe reads/writes
_locks: Dict[str, threading.Lock] = {}


def _get_lock(path: str) -> threading.Lock:
    if path not in _locks:
        _locks[path] = threading.Lock()
    return _locks[path]


def _path(filename: str) -> Path:
    return DATA_DIR / filename


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _read(filename: str) -> Any:
    p = _path(filename)
    lock = _get_lock(str(p))
    with lock:
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)


def _write(filename: str, data: Any) -> None:
    p = _path(filename)
    lock = _get_lock(str(p))
    with lock:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------

RESUMES_FILE = "resumes.json"


def get_all_resumes() -> List[Dict]:
    return _read(RESUMES_FILE) or []


def get_resume(resume_id: str) -> Optional[Dict]:
    return next((r for r in get_all_resumes() if r["id"] == resume_id), None)


def save_resume(resume: Dict) -> Dict:
    resumes = get_all_resumes()
    existing = next((i for i, r in enumerate(resumes) if r["id"] == resume["id"]), None)
    if existing is not None:
        resumes[existing] = resume
    else:
        resumes.append(resume)
    _write(RESUMES_FILE, resumes)
    return resume


def delete_resume(resume_id: str) -> bool:
    resumes = get_all_resumes()
    new_list = [r for r in resumes if r["id"] != resume_id]
    if len(new_list) == len(resumes):
        return False
    _write(RESUMES_FILE, new_list)
    return True


def archive_resume(resume_id: str, archived: bool) -> Optional[Dict]:
    resume = get_resume(resume_id)
    if not resume:
        return None
    resume["archived"] = archived
    resume["updated_at"] = _now()
    return save_resume(resume)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

JOBS_FILE = "jobs.json"


def get_all_jobs() -> List[Dict]:
    return _read(JOBS_FILE) or []


def get_job(job_id: str) -> Optional[Dict]:
    return next((j for j in get_all_jobs() if j["id"] == job_id), None)


def save_job(job: Dict) -> Dict:
    jobs = get_all_jobs()
    existing = next((i for i, j in enumerate(jobs) if j["id"] == job["id"]), None)
    if existing is not None:
        jobs[existing] = job
    else:
        jobs.append(job)
    _write(JOBS_FILE, jobs)
    return job


def delete_job(job_id: str) -> bool:
    jobs = get_all_jobs()
    new_list = [j for j in jobs if j["id"] != job_id]
    if len(new_list) == len(jobs):
        return False
    _write(JOBS_FILE, new_list)
    return True


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "default_resume_format": "docx",
    "copilot_timeout": 90,
    "ats_min_score": 70,
}


def get_settings() -> Dict:
    data = _read(SETTINGS_FILE)
    if not data:
        _write(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    return data


def save_settings(settings: Dict) -> Dict:
    _write(SETTINGS_FILE, settings)
    return settings


# ---------------------------------------------------------------------------
# Application files (generated exports used for job applications)
# ---------------------------------------------------------------------------

APPLICATION_FILES_FILE = "application_files.json"


def get_all_application_files() -> List[Dict]:
    files = _read(APPLICATION_FILES_FILE) or []
    return sorted(files, key=lambda x: x.get("created_at", ""), reverse=True)


def save_application_file(entry: Dict) -> Dict:
    files = _read(APPLICATION_FILES_FILE) or []
    existing = next((i for i, f in enumerate(files) if f.get("id") == entry.get("id")), None)
    if existing is not None:
        files[existing] = entry
    else:
        files.append(entry)
    _write(APPLICATION_FILES_FILE, files)
    return entry


def get_application_file(file_id: str) -> Optional[Dict]:
    return next((f for f in get_all_application_files() if f.get("id") == file_id), None)


def delete_application_file(file_id: str) -> bool:
    files = _read(APPLICATION_FILES_FILE) or []
    new_files = [f for f in files if f.get("id") != file_id]
    if len(new_files) == len(files):
        return False
    _write(APPLICATION_FILES_FILE, new_files)
    return True
