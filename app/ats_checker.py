"""
ATS (Applicant Tracking System) Compatibility Checker.
Scores a resume against a job description and provides actionable suggestions.
"""
import re
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Common ATS-friendly section names
# ---------------------------------------------------------------------------

EXPECTED_SECTIONS = [
    "summary", "objective", "profile",
    "experience", "work experience", "employment",
    "education",
    "skills", "technical skills", "core competencies",
    "projects",
    "certifications", "licenses",
    "achievements", "accomplishments",
]

FORMATTING_ANTIPATTERNS = [
    (r"(table|column|header|footer)", "Avoid tables, columns, headers/footers — ATS may not read them."),
    (r"[^\x00-\x7F]+", "Special/unicode characters may be stripped by ATS parsers."),
    (r"http[s]?://\S+", None),  # URLs are OK — skip
]

POWER_VERBS = [
    "led", "built", "developed", "designed", "implemented", "improved",
    "increased", "reduced", "managed", "delivered", "created", "launched",
    "optimized", "automated", "architected", "deployed", "scaled", "drove",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_ats_compatibility(resume_text: str, job_description: str = "") -> Dict:
    """
    Full ATS compatibility check.

    Args:
        resume_text: Plain text of the resume
        job_description: Job posting text for keyword matching

    Returns:
        dict with score, issues, suggestions, keyword_analysis
    """
    issues: List[Dict] = []
    suggestions: List[str] = []

    # 1. Section completeness
    section_score, section_issues = _check_sections(resume_text)
    issues.extend(section_issues)

    # 2. Keyword matching
    keyword_analysis = {}
    keyword_score = 100
    if job_description:
        keyword_analysis = extract_ats_keywords(resume_text, job_description)
        matched = len(keyword_analysis.get("matched", []))
        total = matched + len(keyword_analysis.get("missing", []))
        keyword_score = int((matched / total) * 100) if total else 100
        if keyword_analysis.get("missing"):
            issues.append({
                "type": "keywords",
                "severity": "high",
                "message": f"Missing {len(keyword_analysis['missing'])} important keywords from job description.",
                "detail": ", ".join(keyword_analysis["missing"][:15]),
            })

    # 3. Formatting checks
    format_score, format_issues = _check_formatting(resume_text)
    issues.extend(format_issues)

    # 4. Impact/action verbs
    verb_score, verb_suggestions = _check_action_verbs(resume_text)
    suggestions.extend(verb_suggestions)

    # 5. Length check
    word_count = len(resume_text.split())
    if word_count < 200:
        issues.append({"type": "length", "severity": "medium", "message": "Resume is too short (< 200 words)."})
    elif word_count > 1000:
        issues.append({"type": "length", "severity": "low", "message": "Resume may be too long (> 1000 words) for ATS parsing."})

    # Composite score
    weights = {"section": 0.35, "keyword": 0.40, "format": 0.15, "verb": 0.10}
    final_score = int(
        section_score * weights["section"]
        + keyword_score * weights["keyword"]
        + format_score * weights["format"]
        + verb_score * weights["verb"]
    )

    # Generate improvement suggestions
    for issue in issues:
        if issue["severity"] == "high":
            suggestions.insert(0, issue["message"])
        else:
            suggestions.append(issue["message"])

    return {
        "ats_score": max(0, min(100, final_score)),
        "score": max(0, min(100, final_score)),  # backward compat
        "score_breakdown": {
            "sections": section_score,
            "keywords": keyword_score,
            "formatting": format_score,
            "action_verbs": verb_score,
        },
        "issues": issues,
        "suggestions": suggestions,
        "keyword_analysis": keyword_analysis,
        "word_count": word_count,
    }


def extract_ats_keywords(resume_text: str, job_description: str) -> Dict:
    """
    Compare job description keywords against resume text.

    Returns:
        dict with matched, missing, all_job_keywords
    """
    job_keywords = _extract_keywords(job_description)
    resume_lower = resume_text.lower()

    matched = []
    missing = []

    for kw in job_keywords:
        pattern = re.compile(r'\b' + re.escape(kw.lower()) + r'\b')
        if pattern.search(resume_lower):
            matched.append(kw)
        else:
            missing.append(kw)

    return {
        "matched": matched,
        "matched_keywords": matched,
        "missing": missing,
        "missing_keywords": missing,
        "all_job_keywords": job_keywords,
        "match_percentage": int(len(matched) / len(job_keywords) * 100) if job_keywords else 0,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful multi-word and single-word technical keywords."""
    # Multi-word phrases first (2–4 words)
    phrases = re.findall(r'\b[A-Za-z][A-Za-z0-9\+\#\./\-]{1,}\s[A-Za-z][A-Za-z0-9\+\#\./\-]{1,}(?:\s[A-Za-z][A-Za-z0-9\+\#\./\-]{1,}){0,2}\b', text)

    # Technology tokens: include abbreviations like AI, ML, SQL, APIs
    tokens = re.findall(r'\b[A-Z]{2,}\b|\b[A-Za-z][A-Za-z0-9\+\#\.]{2,}\b', text)

    stopwords = {
        "the", "and", "for", "with", "this", "that", "are", "have", "will",
        "from", "our", "you", "your", "not", "but", "all", "its", "has",
        "been", "more", "than", "can", "may", "also", "into", "over", "each",
        "such", "their", "they", "them", "any", "both", "most", "some", "about",
        "well", "other", "upon", "include", "including", "without", "through",
        "within", "across", "during", "must", "should", "using", "need",
    }

    seen = set()
    keywords = []

    for kw in tokens:
        lkw = kw.lower()
        if lkw not in stopwords and len(lkw) > 2 and lkw not in seen:
            seen.add(lkw)
            keywords.append(kw)

    # Add high-value multi-word phrases
    for phrase in phrases:
        lp = phrase.lower()
        if lp not in seen:
            seen.add(lp)
            keywords.append(phrase)

    return keywords[:80]  # Cap at top-80


def _check_sections(resume_text: str) -> tuple:
    resume_lower = resume_text.lower()
    found = [s for s in EXPECTED_SECTIONS if s in resume_lower]
    critical = {"experience", "education", "skills"}
    missing_critical = critical - set(found)

    issues = []
    for s in missing_critical:
        issues.append({
            "type": "section",
            "severity": "high",
            "message": f"Missing critical section: '{s.title()}'",
            "detail": f"ATS systems look for a dedicated '{s.title()}' area to extract your data. Without it, your information may be indexed incorrectly."
        })

    score = min(100, int((len(found) / max(len(EXPECTED_SECTIONS), 1)) * 100) + 30)
    return min(100, score), issues


def _check_formatting(resume_text: str) -> tuple:
    issues = []
    score = 100

    lines = resume_text.splitlines()
    blank_lines = sum(1 for l in lines if not l.strip())
    if blank_lines > len(lines) * 0.4:
        issues.append({
            "type": "formatting", 
            "severity": "low", 
            "message": "Excessive blank lines may confuse ATS parsers.",
            "detail": f"Resume has {blank_lines} blank lines ({int(blank_lines/len(lines)*100)}% of the file). Aim for a cleaner vertical rhythm."
        })
        score -= 10

    # Check for long unbroken blocks (paragraphs over 150 words)
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', resume_text) if p.strip()]
    for para in paragraphs:
        if len(para.split()) > 150:
            excerpt = para[:100] + "..."
            issues.append({
                "type": "formatting", 
                "severity": "medium", 
                "message": "Long paragraphs detected — break into bullets for ATS readability.",
                "detail": f"Snippet: \"{excerpt}\"\n\nATS parsers and recruiters prefer concise bullet points over blocks of text exceeding 150 words."
            })
            score -= 15
            break

    return max(0, score), issues


def _check_action_verbs(resume_text: str) -> tuple:
    resume_lower = resume_text.lower()
    found_verbs = [v for v in POWER_VERBS if re.search(r'\b' + v + r'\b', resume_lower)]
    suggestions = []

    if len(found_verbs) < 3:
        suggestions.append(
            f"Use more action verbs to strengthen impact (e.g. {', '.join(POWER_VERBS[:6])})."
        )
        return 50, suggestions

    return 100, suggestions
