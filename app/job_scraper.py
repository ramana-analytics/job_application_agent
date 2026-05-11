import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import json
import re


def scrape_job_description(url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape job description from a URL.
    Supports multiple job board formats.
    
    Args:
        url: The job posting URL
    
    Returns:
        Dictionary with 'title', 'company', 'description', or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try to detect job board and use appropriate parser
        domain = urlparse(url).netloc.lower()
        parsed = _parse_by_domain(soup, domain, url)

        # Enrich with schema.org JobPosting data if available.
        structured = _parse_jobposting_jsonld(soup)
        merged = _merge_job_data(parsed, structured)
        merged['url'] = url
        return merged
    
    except Exception as e:
        print(f"Error scraping URL: {str(e)}")
        return None


def parse_job_description_from_html(html: str, source_url: str = "") -> Optional[Dict[str, Any]]:
    """
    Parse job description from raw HTML content.

    Args:
        html: Raw HTML extracted from a browser or extension
        source_url: Optional source URL to improve parser selection

    Returns:
        Dictionary with 'title', 'company', 'description', or None if failed
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        domain = urlparse(source_url).netloc.lower() if source_url else ""
        parsed = _parse_by_domain(soup, domain, source_url)
        structured = _parse_jobposting_jsonld(soup)
        merged = _merge_job_data(parsed, structured)
        if source_url and merged is not None and 'url' not in merged:
            merged['url'] = source_url
        return merged
    except Exception as e:
        print(f"Error parsing HTML content: {str(e)}")
        return None


def _parse_by_domain(soup: BeautifulSoup, domain: str, url: str = "") -> Dict[str, Any]:
    """Select parser based on source domain with generic fallback."""
    if 'linkedin.com' in domain:
        return _parse_linkedin(soup, url)
    if 'indeed.com' in domain:
        return _parse_indeed(soup)
    if 'glassdoor.com' in domain:
        return _parse_glassdoor(soup)
    if 'github.com/jobs' in domain:
        return _parse_github_jobs(soup)
    return _parse_generic(soup)


def _parse_linkedin(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Parse LinkedIn job posting."""
    try:
        # LinkedIn job title
        title = soup.find('h1', class_='top-card-layout__title')
        title_text = title.text.strip() if title else "Job Title"
        
        # Company name
        company = soup.find('a', class_='topcard__org-name-link')
        company_text = company.text.strip() if company else "Company"
        
        # Job description - LinkedIn uses specific structure
        description_section = soup.find('div', class_='show-more-less-html__markup')
        description = description_section.text.strip() if description_section else _extract_body_text(soup)
        
        return {
            'title': title_text,
            'company': company_text,
            'description': description,
            'url': url
        }
    except Exception as e:
        print(f"Error parsing LinkedIn: {str(e)}")
        return _parse_generic(soup)


def _parse_indeed(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse Indeed job posting."""
    try:
        title = soup.find('h1', class_='jobsearch-JobInfoHeader-title')
        title_text = title.text.strip() if title else "Job Title"
        
        company = soup.find('div', class_='jobsearch-InlineCompanyRating-companyName')
        company_text = company.text.strip() if company else "Company"
        
        description = soup.find('div', id='jobDescriptionText')
        description_text = description.text.strip() if description else _extract_body_text(soup)
        
        return {
            'title': title_text,
            'company': company_text,
            'description': description_text
        }
    except Exception as e:
        print(f"Error parsing Indeed: {str(e)}")
        return _parse_generic(soup)


def _parse_glassdoor(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse Glassdoor job posting."""
    try:
        title = soup.find('h1', class_='JobTitle_jobTitle__JJBPM')
        title_text = title.text.strip() if title else "Job Title"
        
        company = soup.find('div', class_='EmployerProfile_companyName__coEmh')
        company_text = company.text.strip() if company else "Company"
        
        description = soup.find('div', class_='JobDetails_jobDetails__Zvz9J')
        description_text = description.text.strip() if description else _extract_body_text(soup)
        
        return {
            'title': title_text,
            'company': company_text,
            'description': description_text
        }
    except Exception as e:
        print(f"Error parsing Glassdoor: {str(e)}")
        return _parse_generic(soup)


def _parse_github_jobs(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse GitHub Jobs listing."""
    try:
        title = soup.find('h1')
        title_text = title.text.strip() if title else "Job Title"
        
        company = soup.find('p', class_='company')
        company_text = company.text.strip() if company else "Company"
        
        description = soup.find('div', class_='job-description')
        description_text = description.text.strip() if description else _extract_body_text(soup)
        
        return {
            'title': title_text,
            'company': company_text,
            'description': description_text
        }
    except Exception as e:
        print(f"Error parsing GitHub Jobs: {str(e)}")
        return _parse_generic(soup)


def _parse_generic(soup: BeautifulSoup) -> Dict[str, Any]:
    """Generic fallback parser for any job site."""
    # Try to find title in common locations
    title = (soup.find('h1') or soup.find('h2') or soup.find('title'))
    title_text = title.text.strip() if title else "Job Posting"
    
    # Try to find company from title patterns first (e.g., "... at COMPANY").
    company_text = "Company"
    if title_text and ' at ' in title_text.lower():
        parts = title_text.split(' at ')
        if len(parts) > 1:
            company_candidate = parts[-1].strip()
            if company_candidate:
                company_text = company_candidate

    if company_text == "Company":
        page_title = soup.find('title')
        page_title_text = page_title.get_text(' ', strip=True) if page_title else ''
        if ' at ' in page_title_text.lower():
            parts = page_title_text.split(' at ')
            if len(parts) > 1 and parts[-1].strip():
                company_text = parts[-1].strip()

    # Fallback: search visible text for company hints (exclude script/style content).
    if company_text == "Company":
        company_keywords = ['company', 'employer', 'hiring']
        for keyword in company_keywords:
            company = soup.find(
                string=lambda text: (
                    bool(text)
                    and keyword.lower() in text.lower()
                    and getattr(getattr(text, 'parent', None), 'name', '') not in {'script', 'style', 'noscript'}
                    and len(text.strip()) < 160
                )
            )
            if company:
                company_text = company.strip()
                break
    
    # Prefer meta description if present and keep full body text as fallback.
    meta_description = soup.find('meta', attrs={'name': 'description'})
    description = meta_description.get('content', '').strip() if meta_description else ''
    if not description:
        description = _extract_body_text(soup)
    
    return {
        'title': title_text,
        'company': company_text,
        'description': description
    }


def _parse_jobposting_jsonld(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract structured JobPosting data from JSON-LD scripts when present."""
    scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
    for script in scripts:
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = []
        if isinstance(payload, dict):
            candidates = [payload]
            graph = payload.get('@graph')
            if isinstance(graph, list):
                candidates.extend([node for node in graph if isinstance(node, dict)])
        elif isinstance(payload, list):
            candidates = [node for node in payload if isinstance(node, dict)]

        for node in candidates:
            node_type = node.get('@type', '')
            if isinstance(node_type, list):
                is_job_posting = 'JobPosting' in node_type
            else:
                is_job_posting = node_type == 'JobPosting'
            if not is_job_posting:
                continue

            title = (node.get('title') or '').strip()
            description_html = node.get('description') or ''
            description = _extract_text_from_html_fragment(description_html)

            company = ''
            hiring_org = node.get('hiringOrganization')
            if isinstance(hiring_org, dict):
                company = (hiring_org.get('name') or '').strip()

            result = {
                'title': title or 'Job Title',
                'company': company or 'Company',
                'description': description,
            }
            if node.get('url'):
                result['url'] = node.get('url')
            return result
    return {}


def _merge_job_data(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge parser outputs, preferring meaningful values and longer descriptions."""
    placeholders = {'', 'Job Title', 'Job Posting', 'Company'}

    merged_title = primary.get('title', '').strip()
    if merged_title in placeholders:
        merged_title = secondary.get('title', '').strip() or 'Job Title'

    merged_company = primary.get('company', '').strip()
    invalid_company = (
        merged_company in placeholders
        or merged_company.startswith('{')
        or '"@type":"JobPosting"' in merged_company
    )
    if invalid_company:
        merged_company = secondary.get('company', '').strip() or 'Company'

    primary_desc = primary.get('description', '').strip()
    secondary_desc = secondary.get('description', '').strip()
    merged_description = secondary_desc if len(secondary_desc) > len(primary_desc) else primary_desc

    merged = {
        'title': merged_title,
        'company': merged_company,
        'description': merged_description,
        'sections': _extract_description_sections(merged_description),
    }

    url_val = primary.get('url') or secondary.get('url')
    if url_val:
        merged['url'] = url_val
    return merged


def _extract_text_from_html_fragment(html_fragment: str) -> str:
    """Convert an HTML description fragment into readable text while preserving bullets."""
    if not html_fragment:
        return ''

    fragment_soup = BeautifulSoup(html_fragment, 'html.parser')

    for tag in fragment_soup.find_all('br'):
        tag.replace_with('\n')

    lines = []
    for element in fragment_soup.find_all(['p', 'li']):
        text = element.get_text(' ', strip=True)
        if not text:
            continue
        if element.name == 'li':
            lines.append(f"- {text}")
        else:
            lines.append(text)

    if lines:
        return '\n'.join(lines)

    return fragment_soup.get_text('\n', strip=True)


def _extract_description_sections(description: str) -> Dict[str, str]:
    """Split a job description into practical sections for downstream resume matching."""
    if not description:
        return {}

    section_rules = [
        ("opportunity", ["the opportunity", "opportunity"]),
        ("responsibilities", ["responsibilities", "what you'll do", "what you will do", "key responsibilities", "role responsibilities"]),
        ("requirements", ["what you must have", "minimum qualifications", "minimum requirements", "must have", "required qualifications", "requirements", "qualifications"]),
        ("preferred", ["what sets you apart", "preferred qualifications", "nice to have", "preferred", "bonus points"]),
        ("benefits", ["benefits", "compensation", "salary range", "what we offer"]),
        ("about_company", ["about us", "about the company", "who we are", "about pwc"]),
    ]

    sections: Dict[str, list[str]] = {"overview": []}
    current = "overview"

    lines = [line.strip() for line in description.split('\n') if line.strip()]
    for line in lines:
        normalized = re.sub(r'\s+', ' ', line.lower()).strip(" :-\t")
        matched_section = None

        for key, variants in section_rules:
            if normalized in variants:
                matched_section = key
                break

        # Support lines like "Responsibilities:" or short heading-only lines.
        if not matched_section and len(normalized) <= 40:
            for key, variants in section_rules:
                if any(normalized.startswith(v + ':') for v in variants):
                    matched_section = key
                    break

        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
            continue

        # Keyword-based section switching for long-form job text blocks.
        if 'salary range' in normalized or 'compensation' in normalized or 'benefits' in normalized:
            current = 'benefits'
            sections.setdefault(current, [])
        elif normalized.startswith('as ') and 'equal opportunity employer' in normalized:
            current = 'about_company'
            sections.setdefault(current, [])
        elif normalized.startswith('learn more about how we work') or normalized.startswith('about ') and 'pwc' in normalized:
            current = 'about_company'
            sections.setdefault(current, [])

        sections.setdefault(current, []).append(line)

    compact_sections: Dict[str, str] = {}
    for key, content_lines in sections.items():
        if content_lines:
            compact_sections[key] = '\n'.join(content_lines).strip()

    return compact_sections


def _extract_body_text(soup: BeautifulSoup) -> str:
    """Extract main body text from page."""
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up text
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text
