# Resume Builder - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
│                  (http://localhost:8000)                │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
                     │  Frontend (HTML/CSS/JS)      │
                     │  - Three-pane dashboard      │
                     │  - Job tracker               │
                     │  - Resume editor + preview   │
                     │  - Copilot prompt history    │
           └──────────┬───────────────────┘
                      │ HTTP Requests
                      ▼
         ┌────────────────────────────┐
                 │   FastAPI Server (main.py) │
                 │   - REST API endpoints     │
                 │   - Request routing        │
                 │   - Copilot orchestration   │
         └────────┬───────────┬───┬───┘
                  │           │   │
    ┌─────────────▼──┐  ┌──────▼──┐  ┌──────────┬──────────────┐
    │ Job Scraper    │  │Resume   │  │ Copilot  │ File Storage │
    │                │  │Parser   │  │          │              │
    │ - URL fetch    │  │         │  │- gh CLI  │ - uploads/   │
    │ - HTML parse   │  │- PDF    │  │- Prompt  │ - data/      │
    │ - Job extract  │  │- DOCX   │  │- Tailor  │ - generated  │
    │                │  │- LaTeX  │  │- Cover   │              │
    └────────────────┘  └─────────┘  └──────────┴──────────────┘
                            │
                            ▼
        ┌─────────────────────────────────┐
        │   Local File System             │
        │   - PDF/DOCX/TXT/LaTeX files    │
        │   - Uploaded resumes            │
        │   - Generated files             │
        └─────────────────────────────────┘
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/resumes` | List resumes |
| POST | `/api/resumes/upload` | Parse uploaded resume (PDF/DOCX/TXT/LaTeX) |
| PATCH | `/api/resumes/{resume_id}/text` | Save edited resume text |
| POST | `/api/resumes/{resume_id}/compile-pdf` | Compile LaTeX resume to PDF |
| GET | `/api/jobs` | List jobs |
| POST | `/api/jobs/{job_id}/recommendations` | Generate resume recommendations |
| POST | `/api/jobs/{job_id}/recommendations/apply` | Create a tailored resume from recommendations |
| POST | `/api/cover-letter` | Generate a tailored cover letter |
| GET | `/api/application-files` | List generated artifacts |

## Data Flow

```
1. USER ENTERS JOB URL
   └─→ Job Scraper fetches HTML
       └─→ BeautifulSoup parses job details
           └─→ Frontend displays title, company, description, and summary

2. USER UPLOADS RESUME
   └─→ File saved to uploads/
       └─→ Resume Parser extracts text or LaTeX source
           └─→ Frontend shows preview and LaTeX editor when applicable

3. USER REQUESTS RECOMMENDATIONS
   └─→ Job summary + resume text sent to Copilot Integration
       └─→ gh copilot CLI called
           └─→ ATS-friendly recommendations returned
               └─→ Stored on the job and displayed in the browser

4. USER APPLIES RECOMMENDATIONS
   └─→ Recommendation text sent with the source resume
       └─→ Copilot rewrites the resume draft
           └─→ New resume record created
               └─→ Resumes tab opens the new tailored resume

5. USER EXPORTS OR COMPILES RESUME
   └─→ Text converted to PDF or DOCX
       └─→ File saved temporarily
           └─→ Downloaded to user's device
```

## Technology Stack

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Responsive grid/flexbox layout
- **Vanilla JS** - No framework (lightweight)

### Backend
- **FastAPI** - Modern async Python framework
- **Uvicorn** - ASGI web server
- **Pydantic** - Data validation

### State and Storage
- **JSON files** - Persist jobs, resumes, and generated artifacts
- **LocalStorage** - Save UI preferences and Copilot prompt history

### Libraries
- **python-docx** - Create/read .docx files
- **pdfplumber** - Extract text from PDFs
- **PyPDF2** - PDF manipulation
- **reportlab** - Generate PDF files
- **requests** - HTTP client
- **beautifulsoup4** - HTML/XML parsing
- **copilot CLI** - Resume recommendations and tailoring

### External Services
- **GitHub Copilot CLI** - AI suggestions (via `copilot -p` command)

## File Roles

### Core Application
- `main.py` - FastAPI app, API endpoints, and Copilot flows
- `storage.py` - JSON persistence layer
- `resume_manager.py` - Resume CRUD, versioning, ATS updates
- `tailoring.py` - Resume tailoring and cover letter helpers
- `copilot_integration.py` - Wraps `gh copilot suggest` command
- `job_scraper.py` - Multi-board job scraping with fallback parser
- `resume_parser.py` - PDF/DOCX/LaTeX read and write operations

### HTML Interface
- `index.html` - Three-pane dashboard UI
- `script.js` - Event handlers, API calls, state management
- `style.css` - Responsive dashboard styling

### Configuration
- `requirements.txt` - Pinned dependency versions
- `setup.sh` - Automated environment setup
- `.gitignore` - Version control exclusions
- `README.md` - Full documentation
- `QUICKSTART.md` - Quick reference

## Security Considerations

✅ **Implemented**
- File type validation (PDF/DOCX only)
- Input sanitization through BeautifulSoup
- CORS headers for API
- Error handling with proper HTTP status codes
- Resume/job records stored locally in JSON
- LaTeX compile flow with error reporting and package hints
- Recommendation-to-new-resume workflow

⚠️ **For Production**
- Add authentication (OAuth2/JWT)
- Implement rate limiting
- Add request size limits
- Validate file content (magic bytes)
- Use environment variables for config
- Add response compression
- Implement logging/monitoring

## Performance Notes

### Optimizations Applied
- Local file persistence with small JSON records
- Optional PDF preview embedding for LaTeX resumes
- Background task support (for future use)
- Minimal static file sizes

### Scalability Options
- Use database for file metadata
- Implement job queue (Celery/RQ)
- Cache job descriptions
- Use CDN for static files
- Horizontal scaling with load balancer

## Supported Job Boards

**Built-in Parsers:**
- LinkedIn Jobs (LinkedIn-specific CSS selectors)
- Indeed (Indeed-specific CSS selectors)
- Glassdoor (Glassdoor-specific CSS selectors)

**Generic Fallback:**
- Any HTML-based job board (extracts main content)

All sites: Requires public access, no authentication needed

---

**Ready to Launch?**
```bash
chmod +x setup.sh && ./setup.sh
source venv/bin/activate
python -m app.main
# Open http://localhost:8000
```
