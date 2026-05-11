"""
Job tracker — manages the jobs JSON store with full CRUD + ATS keyword linking.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import storage
from app.ats_checker import extract_ats_keywords

VALID_STATUSES = {"saved", "applied", "interview", "rejected", "no_response", "offer"}


def add_job(
    job_title: str,
    company: str,
    job_url: str,
    description: str = "",
    resume_text: str = "",
    **extra,
) -> Dict:
    """Create a new tracked job entry."""
    keyword_analysis = extract_ats_keywords(resume_text, description) if resume_text and description else {}

    entry: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "job_title": job_title,
        "company": company,
        "job_url": job_url,
        "description": description,
        "sections": extra.get("sections", {}),

        # Location / logistics
        "locations": extra.get("locations", []),
        "job_type": extra.get("job_type", ""),           # remote / hybrid / onsite
        "sponsorship_required": extra.get("sponsorship_required", ""),

        # Compensation
        "salary_range": extra.get("salary_range", ""),
        "band_level": extra.get("band_level", ""),

        # Requirements
        "experience_requirements": extra.get("experience_requirements", ""),

        # ATS
        "ats_keywords": keyword_analysis.get("all_job_keywords", []),
        "matched_keywords": keyword_analysis.get("matched", []),
        "mismatched_keywords": keyword_analysis.get("missing", []),
        "job_match_percentage": keyword_analysis.get("match_percentage", 0),

        # Dates
        "posting_date": extra.get("posting_date", ""),
        "deadline": extra.get("deadline", ""),
        "applied_date": extra.get("applied_date", ""),

        # Status
        "status": extra.get("status", "saved"),

        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return storage.save_job(entry)


def list_jobs(status_filter: Optional[str] = None) -> List[Dict]:
    jobs = storage.get_all_jobs()
    if status_filter:
        jobs = [j for j in jobs if j.get("status") == status_filter]
    # Sort newest first
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs


def get_job(job_id: str) -> Optional[Dict]:
    return storage.get_job(job_id)


def update_job_status(job_id: str, status: str) -> Optional[Dict]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Choose from {VALID_STATUSES}")
    job = storage.get_job(job_id)
    if not job:
        return None
    job["status"] = status
    if status == "applied" and not job.get("applied_date"):
        job["applied_date"] = datetime.utcnow().isoformat()
    job["updated_at"] = datetime.utcnow().isoformat()
    return storage.save_job(job)


def update_job_match(job_id: str, resume_text: str) -> Optional[Dict]:
    """Recalculate keyword match against a chosen resume."""
    job = storage.get_job(job_id)
    if not job:
        return None
    kw = extract_ats_keywords(resume_text, job.get("description", ""))
    job["matched_keywords"] = kw.get("matched", [])
    job["mismatched_keywords"] = kw.get("missing", [])
    job["job_match_percentage"] = kw.get("match_percentage", 0)
    job["updated_at"] = datetime.utcnow().isoformat()
    return storage.save_job(job)


def update_job(job_id: str, fields: Dict) -> Optional[Dict]:
    job = storage.get_job(job_id)
    if not job:
        return None
    for k, v in fields.items():
        if k not in {"id", "created_at"}:
            job[k] = v
    job["updated_at"] = datetime.utcnow().isoformat()
    return storage.save_job(job)


def delete_job(job_id: str) -> bool:
    return storage.delete_job(job_id)


def get_job_stats() -> Dict:
    jobs = storage.get_all_jobs()
    stats: Dict[str, int] = {s: 0 for s in VALID_STATUSES}
    stats["total"] = len(jobs)
    for j in jobs:
        s = j.get("status", "saved")
        if s in stats:
            stats[s] += 1
    return stats
