"""
Resume tailoring — compare master profile + existing resume against a job description
and generate a tailored resume and cover letter via Copilot.
"""
from typing import Dict, Optional

from app.copilot_integration import gh_copilot_suggest, gh_copilot_suggest_with_meta
from app.ats_checker import extract_ats_keywords


def tailor_resume(
    resume_text: str,
    job_description: str,
    sections: Optional[Dict] = None,
    master_profile: Optional[Dict] = None,
) -> Dict:
    """
    Produce a tailored resume and improvement suggestions for a given job.

    Returns:
        dict with tailored_resume, suggestions, keyword_analysis
    """
    keyword_analysis = extract_ats_keywords(resume_text, job_description)

    # Build a focused prompt from structured sections if available
    responsibilities = sections.get("responsibilities", "") if sections else ""
    requirements = sections.get("requirements", "") if sections else ""
    preferred = sections.get("preferred", "") if sections else ""

    # Summarize master profile skills if provided
    profile_skills = ""
    if master_profile:
        skills = master_profile.get("skills", [])
        if isinstance(skills, list):
            profile_skills = ", ".join(skills[:30])

    prompt = f"""You are an expert resume writer and career coach.

TASK: Rewrite and improve the following resume so it is ATS-optimized and highly tailored for the job below.

JOB TITLE: {_extract_first_line(job_description)}

KEY RESPONSIBILITIES:
{responsibilities or job_description[:600]}

REQUIREMENTS:
{requirements or '(see full description)'}

PREFERRED:
{preferred}

MISSING KEYWORDS TO ADD:
{', '.join(keyword_analysis.get('missing', [])[:20])}

CANDIDATE PROFILE SKILLS: {profile_skills}

CURRENT RESUME:
{resume_text[:2500]}

INSTRUCTIONS:
1. Keep all real facts — do not fabricate experience.
2. Insert missing keywords naturally into existing bullets.
3. Strengthen weak bullet points with quantified impact where possible.
4. Ensure sections: Summary, Skills, Experience, Education.
5. Return only the improved resume text — no commentary.

IMPROVED RESUME:"""

    cli_meta = gh_copilot_suggest_with_meta(prompt)
    tailored = cli_meta.get("stdout", "") if cli_meta.get("success") else ""

    return {
        "tailored_resume": tailored,
        "keyword_analysis": keyword_analysis,
        "matched_keywords": keyword_analysis.get("matched", []),
        "missing_keywords": keyword_analysis.get("missing", []),
        "match_percentage": keyword_analysis.get("match_percentage", 0),
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "tool": "copilot",
            "task": "tailor_resume",
        },
    }


def generate_cover_letter_with_meta(
    resume_text: str,
    job_description: str,
    company_name: str,
    job_title: str,
    candidate_name: str = "",
) -> Dict:
    """
    Generate a professional cover letter tailored to the job with CLI metadata.
    """
    prompt = f"""Write a professional, compelling cover letter for the following job application.

CANDIDATE NAME: {candidate_name or 'the candidate'}
COMPANY: {company_name}
JOB TITLE: {job_title}

JOB DESCRIPTION (key excerpt):
{job_description[:1200]}

CANDIDATE RESUME (key excerpt):
{resume_text[:1200]}

INSTRUCTIONS:
- 3–4 paragraphs
- Opening: express enthusiasm and specific role fit
- Middle: highlight 2–3 most relevant achievements from resume
- Closing: call-to-action, professional sign-off
- Tone: confident, professional, personalized to {company_name}
- Do NOT use generic filler phrases like "I am writing to apply..."

COVER LETTER:"""

    cli_meta = gh_copilot_suggest_with_meta(prompt)
    text = cli_meta.get("stdout", "") if cli_meta.get("success") else ""
    return {
        "cover_letter": text,
        "cli_status": {
            "command": cli_meta.get("command", ""),
            "output": cli_meta.get("stdout", ""),
            "error": cli_meta.get("stderr", ""),
            "returncode": cli_meta.get("returncode", -1),
            "success": cli_meta.get("success", False),
            "tool": "copilot",
            "task": "cover_letter",
        },
    }


def generate_cover_letter(
    resume_text: str,
    job_description: str,
    company_name: str,
    job_title: str,
    candidate_name: str = "",
) -> str:
    """
    Backward-compatible helper that returns only letter text.
    """
    return generate_cover_letter_with_meta(
        resume_text=resume_text,
        job_description=job_description,
        company_name=company_name,
        job_title=job_title,
        candidate_name=candidate_name,
    ).get("cover_letter", "")


def _extract_first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:120]
    return "Job Position"
