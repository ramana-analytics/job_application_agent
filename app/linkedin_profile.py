import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def _fetch_with_headers(url: str, headers: dict, timeout: int = 20):
    try:
        return requests.get(url, headers=headers, timeout=timeout)
    except Exception:
        return None


def _fetch_linkedin_page(url: str, headers: dict) -> tuple[str, str]:
    """Return (content, source) with multiple fallbacks for blocked LinkedIn pages."""
    candidates = [
        url,
        url.replace("www.linkedin.com", "m.linkedin.com"),
        f"https://r.jina.ai/http://{url.replace('https://', '').replace('http://', '')}",
    ]

    for candidate in candidates:
        resp = _fetch_with_headers(candidate, headers=headers, timeout=25)
        if resp is None:
            continue
        if resp.status_code >= 400:
            continue
        text = resp.text or ""
        if text.strip():
            return text, candidate

    return "", ""


def _normalize_linkedin_url(linkedin_url: str) -> str:
    url = (linkedin_url or "").strip()
    if not url:
        raise ValueError("LinkedIn URL is required")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if "linkedin.com" not in host:
        raise ValueError("Please provide a valid LinkedIn URL")

    return url


def _extract_person_from_json_ld(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") in {"Person", "ProfilePage"}:
                return item
            if isinstance(item.get("mainEntity"), dict) and item["mainEntity"].get("@type") == "Person":
                return item["mainEntity"]
    return {}


def _guess_skills(text: str) -> list:
    if not text:
        return []

    common_skills = [
        "Python", "Java", "JavaScript", "TypeScript", "SQL", "R", "Scala", "Go",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "FastAPI", "Django", "Flask", "React", "Node.js", "Spring",
        "Machine Learning", "Data Science", "Deep Learning", "NLP",
        "Tableau", "Power BI", "Snowflake", "Databricks",
        "Git", "CI/CD", "Microservices", "REST", "GraphQL",
    ]

    lowered = text.lower()
    found = []
    for skill in common_skills:
        if skill.lower() in lowered:
            found.append(skill)
    return found[:20]


def _parse_name_and_headline(candidate: str) -> tuple[str, str]:
    raw = (candidate or "").strip()
    if not raw:
        return "", ""

    # Common format: "Name - Headline | LinkedIn"
    m = re.search(r"^(.+?)\s[-\u2013|]\s(.+?)\s\|\sLinkedIn", raw, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Another frequent format: "Name | LinkedIn"
    m2 = re.search(r"^(.+?)\s\|\sLinkedIn", raw, flags=re.IGNORECASE)
    if m2:
        return m2.group(1).strip(), ""

    # Fallback: pick first two-words+ token sequence that looks like a person name.
    name_guess = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z][A-Za-z'-]+)\b", raw)
    return (name_guess.group(1).strip() if name_guess else ""), ""


def _extract_summary_from_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Keep a short summary-sized snippet from the first meaningful sentence block.
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    snippet = " ".join(parts[:2]).strip()
    return snippet[:500]


def extract_profile_from_linkedin_url(linkedin_url: str) -> dict:
    """Best-effort extraction of profile fields from a public LinkedIn URL."""
    url = _normalize_linkedin_url(linkedin_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    html, source = _fetch_linkedin_page(url, headers)
    if not html:
        raise ValueError(
            "Unable to access LinkedIn profile URL. LinkedIn may block automated access for this page."
        )

    soup = BeautifulSoup(html, "html.parser")
    person = _extract_person_from_json_ld(soup)

    title_text = (soup.title.string if soup.title else "") or ""
    og_title = (soup.find("meta", attrs={"property": "og:title"}) or {}).get("content", "")
    og_desc = (soup.find("meta", attrs={"property": "og:description"}) or {}).get("content", "")
    full_text = soup.get_text(" ", strip=True)

    # If we fetched from a mirror endpoint, text may be markdown-like.
    if "r.jina.ai" in source and not (og_title or title_text):
        first_line = (html.splitlines()[0] if html.splitlines() else "")
        title_text = first_line[:200]

    name = person.get("name", "") if person else ""
    if not name:
        candidate = og_title or title_text or full_text[:250]
        name, parsed_headline = _parse_name_and_headline(candidate)
    else:
        parsed_headline = ""

    summary = ""
    if person:
        summary = person.get("description", "") or ""
    if not summary:
        summary = og_desc or ""
    if not summary:
        summary = _extract_summary_from_text(full_text)

    headline = ""
    candidate_title = og_title or title_text
    if candidate_title:
        # Try to keep role/company part from title after first separator.
        parts = re.split(r"\s[-|\u2013]\s", candidate_title)
        if len(parts) > 1:
            headline = parts[1].replace("LinkedIn", "").strip()
    if not headline:
        headline = parsed_headline

    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", full_text)

    skills = _guess_skills(" ".join([summary, headline, og_desc, full_text]))

    profile = {
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "linkedin": url,
        "github": "",
        "website": "",
        "summary": summary,
        "skills": skills,
        "education": "",
        "certifications": [],
        "work_preferences": headline,
    }

    if not any([profile["name"], profile["summary"], profile["work_preferences"], profile["email"], profile["phone"]]):
        raise ValueError(
            "LinkedIn limited this page for automated access. Try a public profile URL or fill fields manually."
        )

    return profile
