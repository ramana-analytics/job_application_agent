# Job Application Agent — Resume + Job Tracker

Job Application Agent is a FastAPI-based web app for managing resumes and tracking job applications. It integrates GitHub Copilot-powered AI recommendations, supports LaTeX resume editing and PDF compilation, performs ATS compatibility analysis, and provides end-to-end workflows for creating tailored resumes and cover letters from job descriptions.

## Features

✅ **Job Tracking** - Store job details, status, notes, resume linkage, and Copilot summary data  
✅ **Resume Management** - Upload PDF, DOCX, TXT, and LaTeX resume files with versioning  
✅ **LaTeX Resume Editor** - Edit `.tex` resumes in-browser, format source, adjust font size, and compile to PDF  
✅ **ATS Compatibility Checker** - Score resumes against job descriptions, detect missing keywords, flag anti-patterns, and get actionable suggestions  
✅ **Copilot AI Suggestions** - Generate ATS-optimized resume recommendations and cover letters via GitHub Copilot CLI with selectable models  
✅ **Model Selection** - Choose from 15+ supported AI models (Claude, Gemini, GPT families) with capability and context-size metadata  
✅ **Recommendation-to-Resume Flow** - Apply Copilot suggestions to create a new tailored resume automatically  
✅ **LinkedIn Profile Parsing** - Fetch and extract skills, experience, and education from a LinkedIn profile URL  
✅ **Job Scraping** - Scrape job postings from LinkedIn, Indeed, Glassdoor, and generic HTML pages  
✅ **Multi-Format Export** - Export resumes to PDF or DOCX; generated files persist in the Job Applications view  
✅ **User Authentication** - Register/login with PBKDF2-SHA256 password hashing and 30-day session tokens  
✅ **Web-Based Interface** - Three-pane single-page UI with persistent layout controls and job/resume navigation

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.8+** installed
2. **GitHub Copilot CLI** installed - [Get it](https://github.com/github/copilot-cli)
3. **GitHub Copilot Access** - Requires active Copilot subscription
4. **Copilot Authentication** - Run: `copilot login`

Verify setup:
```bash
copilot -p "hello world"
```

## Installation

1. **Clone or navigate to the project:**
```bash
cd /Users/venkat/Documents/Desktop/work/resumes/code/resume_builder
```

2. **Create a virtual environment (optional but recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Application

1. **Start the server:**
```bash
python -m app.main
```

Or:
```bash
cd app
python main.py
```

Or with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **Open in browser:**
Navigate to `http://localhost:8000`

## How to Use

### Step 1: Add Job Posting
- Paste the job URL or add a job description
- Click the job scrape/fill actions to populate the job record
- Review the extracted job title, company, description, and summary

### Step 2: Upload Your Resume
- Select your resume file (PDF, DOCX, TXT, or LaTeX)
- Click "Upload Resume"
- Preview the extracted text

### Step 3: Review Suggestions
- Click "Get Recommendation" to generate ATS-friendly improvements
- Click "Update the Resume with this Recommendation" to create a new tailored resume
- Click "Generate Cover Letter" to create a tailored cover letter
- Use the Copilot Prompt tab for prompt history and reusable context

### Step 4: Edit and Export Resume
- Use the LaTeX editor when a .tex resume is selected
- Adjust editor font size, format the source, and compile to PDF
- Export the optimized resume in PDF or DOCX format

## Project Structure

```
resume_builder/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application, all API routes
│   ├── auth.py                  # User registration, login, session token management
│   ├── storage.py               # JSON file persistence helpers
│   ├── resume_manager.py        # Resume CRUD, versioning, ATS updates
│   ├── resume_parser.py         # Resume parsing (PDF/DOCX/TXT/LaTeX), export to PDF/DOCX
│   ├── tailoring.py             # Copilot-based ATS tailoring and cover letter generation
│   ├── copilot_integration.py   # GitHub Copilot CLI wrapper + model catalog (15+ models)
│   ├── ats_checker.py           # ATS keyword scoring, section detection, anti-pattern flags
│   ├── job_scraper.py           # Job posting scraper (LinkedIn, Indeed, Glassdoor, generic HTML)
│   ├── job_tracker.py           # Job CRUD, pipeline status, match scoring helpers
│   ├── linkedin_profile.py      # LinkedIn profile URL parser (skills, experience, education)
│   └── static/
│       ├── index.html           # Main single-page app shell
│       ├── login.html           # Login/register page
│       ├── style.css            # Application styling
│       ├── script.js            # Frontend logic, apiFetch, auth guard
│       └── latex_line_numbers.js # LaTeX editor line-number helper
├── data/                        # JSON data store (jobs, resumes, users, sessions, files)
├── uploads/                     # Uploaded and AI-generated files (.tex, .pdf, .aux, .docx)
├── requirements.txt             # Python dependencies
└── setup.sh                     # Convenience environment setup script
```

## Architecture (high level)

- **Backend**: FastAPI application in `app/` that serves static frontend files and exposes JSON REST APIs under `/api/*`.
- **Frontend**: Vanilla JavaScript + HTML/CSS in `app/static/` — single-page app shell that switches views via `data-tab` attributes and stores lightweight state in `localStorage`.
- **Data Storage**: Simple JSON files in `data/` (`jobs.json`, `resumes.json`, `users.json`, `sessions.json`, `application_files.json`) and uploaded/generated files in `uploads/`.
- **AI Integration**: GitHub Copilot CLI is invoked via `app/copilot_integration.py` with support for 15+ models. `app/tailoring.py` builds structured prompts that include ATS keyword gaps, job responsibilities/requirements, and master profile skills. `app/ats_checker.py` handles local keyword scoring independently of Copilot.
- **Auth**: Lightweight session tokens (UUIDs, 30-day TTL) persisted in `data/sessions.json` and validated by `app/auth.py`; tokens are sent from the browser using the `X-Auth-Token` header.
- **LinkedIn Integration**: `app/linkedin_profile.py` fetches and parses public LinkedIn profile pages with multiple URL fallback strategies.
- **Job Scraping**: `app/job_scraper.py` handles site-specific extraction for LinkedIn, Indeed, Glassdoor, and falls back to generic HTML parsing with BeautifulSoup.

Data flow summary:
- Browser UI → `fetch('/api/...')` calls → FastAPI handlers → business logic modules (`resume_manager`, `job_tracker`, `tailoring`, `ats_checker`) → storage layer (`storage.py`) → `uploads/` or `data/`.

## Helper scripts & developer tools

- `setup.sh` — convenience script for environment setup (virtualenv, pip install). Run with `bash setup.sh`.
- `requirements.txt` — Python packages required for running the app. Install via `pip install -r requirements.txt`.
- `app/main.py` — run with Uvicorn for live reload during development:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- `app/static/login.html` — standalone login/register page used for authentication flow.
- Browser state keys (do not rename unless migrating):
	- `rops_token` — session token stored in `localStorage` after login
	- `rops_username` — username for UI display
	- `resumeops.*` keys — layout and preferences (left pane size, copilot runs, etc.)

## Authentication details

- Password hashing: PBKDF2-HMAC-SHA256 (stdlib `hashlib`) with a per-user salt and iteration count.
- Endpoints:
	- `POST /api/auth/register` — create local user (username, hashed password, optional email)
	- `POST /api/auth/login` — return `token` (UUID) and username
	- `POST /api/auth/logout` — invalidate token
	- `GET /api/auth/me` — validate `X-Auth-Token` and return `{username:...}`
- Sessions: stored in `data/sessions.json` with expiry TTL (default 30 days); the frontend injects `X-Auth-Token` into all `/api/*` requests.

## Frontend notes

- Main UI entry: `app/static/index.html` (served at `/app`), static assets served from `/static/`.
- `app/static/script.js` contains helper utilities `apiFetch` and `apiJSON`, plus an auth guard that redirects to `/login` when the user is not authenticated.
- Cache busting: static file URLs include `?v=N` query parameters for CSS/JS versioning. Bump the `v` number on deploy to force reloads.

## Data files and backups

- `data/*.json` contain the canonical application state for jobs, resumes, users, and sessions. Back these up before bulk edits.
- `uploads/` contains uploaded files and generated artifacts (.tex, .pdf, .aux). These files are not automatically removed — include them in your backup/cleanup policy.

## Testing & quick checks

- Smoke test the auth flow with `curl`:

```bash
# register
curl -X POST -H "Content-Type: application/json" -d '{"username":"me","password":"pw"}' http://localhost:8000/api/auth/register

# login
curl -X POST -H "Content-Type: application/json" -d '{"username":"me","password":"pw"}' http://localhost:8000/api/auth/login

# validate
curl -H "X-Auth-Token: <token>" http://localhost:8000/api/auth/me
```

## Deployment notes

- Use Uvicorn + a process manager (systemd, Docker, or process manager) in production.
- Secure the `uploads/` and `data/` directories — they contain sensitive applicant data.
- Consider replacing JSON-based storage with a small database (SQLite/Postgres) for concurrency and durability under load.

## Contributing & helpers

- When changing frontend `script.js` or `style.css`, increment the `?v=N` query strings in `index.html` to force client cache invalidation.
- Use `app/storage.py` helpers to read/write `data/*.json` files programmatically when writing migration scripts.
- Add helper scripts under `tools/` if you need repeatable migrations or backups.

---

**Last Updated:** May 2026  
**Primary entrypoint:** `app/main.py`


## API Endpoints

### Auth
- `POST /api/auth/register` — create a new user account
- `POST /api/auth/login` — return session `token` and username
- `POST /api/auth/logout` — invalidate session token
- `GET /api/auth/me` — validate `X-Auth-Token` and return `{username:...}`

### Resumes
- `GET /api/resumes` — list all resumes
- `POST /api/resumes/upload` — upload and parse a resume file
- `PATCH /api/resumes/{resume_id}/text` — save edited resume text
- `POST /api/resumes/{resume_id}/compile-pdf` — compile LaTeX resume to PDF
- `GET /api/resumes/{resume_id}/download` — download resume file
- `DELETE /api/resumes/{resume_id}` — delete a resume

### Jobs
- `GET /api/jobs` — list all jobs
- `POST /api/jobs` — add a new job
- `GET /api/jobs/{job_id}` — get job details
- `PATCH /api/jobs/{job_id}` — update job fields
- `DELETE /api/jobs/{job_id}` — delete a job
- `POST /api/jobs/{job_id}/recommendations` — generate ATS-tailored resume recommendations
- `POST /api/jobs/{job_id}/recommendations/apply` — create a new tailored resume from recommendations

### AI / Copilot
- `POST /api/cover-letter` — generate a tailored cover letter
- `GET /api/models` — list available Copilot models with metadata

### Application Files & Utilities
- `GET /api/application-files` — list generated files (PDFs, DOCX, etc.)
- `POST /api/scrape-job` — scrape a job posting URL
- `POST /api/ats-check` — run ATS compatibility check on resume + job description
- `POST /api/linkedin-profile` — parse a LinkedIn profile URL

## Supported AI Models

`app/copilot_integration.py` maintains a catalog of models available to the Copilot CLI:

| Model ID | Display Name | Context | Capabilities |
|---|---|---|---|
| `auto` | Auto | — | — |
| `claude-haiku-4.5` | Claude Haiku 4.5 | 160K | Tools, Vision |
| `claude-sonnet-4.5` | Claude Sonnet 4.5 | 160K | Tools, Vision |
| `claude-sonnet-4.6` | Claude Sonnet 4.6 | 160K | Tools, Vision |
| `gemini-2.5-pro` | Gemini 2.5 Pro | 173K | Tools, Vision |
| `gemini-3-flash-preview` | Gemini 3 Flash (Preview) | 173K | Tools, Vision |
| `gemini-3.1-pro-preview` | Gemini 3.1 Pro (Preview) | 173K | Tools, Vision |
| `gemini-3.5-flash` | Gemini 3.5 Flash | 192K | Tools, Vision |
| `gpt-4.1` | GPT-4.1 | 128K | Tools, Vision |
| `gpt-5-mini` | GPT-5 mini | 192K | Tools, Vision |
| `gpt-5.2` | GPT-5.2 | 192K | Tools, Vision |
| `gpt-5.2-codex` | GPT-5.2 Codex | 400K | Tools, Vision |
| `gpt-5.3-codex` | GPT-5.3 Codex | 400K | Tools, Vision |
| `gpt-5.4` | GPT-5.4 | 400K | Tools, Vision |
| `gpt-5.4-mini` | GPT-5.4 mini | 400K | Tools, Vision |
| `raptor-mini-preview` | Raptor mini (Preview) | 264K | Tools, Vision |

The CLI wrapper in `gh_copilot_suggest_with_meta()` automatically falls back to the base command (no `--model` flag) if the installed CLI version does not support `--model`.

## Troubleshooting

### "GitHub Copilot CLI is not available"
- Ensure `gh` CLI is installed: `which gh`
- Ensure the Copilot extension is installed and authenticated
- Authenticate with GitHub: `gh auth login`
- Test Copilot CLI access with a simple prompt

### Resume not parsing correctly
- Ensure file is valid PDF or DOCX
- Try re-exporting the file from your document editor
- Check file permissions

### LaTeX compile fails
- Make sure the selected resume is a `.tex` file
- Use the compile button in the LaTeX editor
- Review the compiler error output and install any missing packages it lists

### Job scraping fails
- Verify the URL is correct and publicly accessible
- Some websites may require authentication or block scraping
- Try a different job board URL

## Supported Job Boards

- LinkedIn Jobs
- Indeed
- Glassdoor
- Generic HTML job pages

## Dependencies

- **FastAPI** - Modern web framework
- **python-docx** - DOCX file handling
- **pdfplumber** - PDF reading
- **PyPDF2** - PDF utilities
- **reportlab** - PDF generation
- **requests** - HTTP requests
- **beautifulsoup4** - HTML parsing
- **Uvicorn** - Local ASGI server
- **GitHub Copilot CLI** - AI generation and tailoring

## Notes

- The application stores uploaded files in the `uploads/` directory
- Job descriptions are scraped in real-time from the provided URLs
- LaTeX resumes keep both the original and updated source files
- The Job Tracker and Resumes views are linked through `resume_id`
- Copilot prompt history is stored locally in the browser

## License

This project is open source and available for personal use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify GitHub CLI setup
3. Check browser console for errors
4. Review FastAPI logs in terminal

---

**Last Updated:** May 2026
**Python Version:** 3.8+
**FastAPI Version:** 0.104.1+
