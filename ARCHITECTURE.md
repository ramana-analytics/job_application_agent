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
           │  - Step-by-step wizard       │
           │  - Form handling             │
           │  - File upload               │
           └──────────┬───────────────────┘
                      │ HTTP Requests
                      ▼
         ┌────────────────────────────┐
         │   FastAPI Server (main.py) │
         │   - REST API endpoints     │
         │   - Request routing        │
         │   - Response handling      │
         └────────┬───────────┬───┬───┘
                  │           │   │
    ┌─────────────▼──┐  ┌──────▼──┐  ┌──────────┬──────────────┐
    │ Job Scraper    │  │Resume   │  │ Copilot  │ File Storage │
    │                │  │Parser   │  │          │              │
    │ - URL fetch    │  │         │  │- gh CLI  │ - Uploads/   │
    │ - HTML parse   │  │- PDF    │  │- Process │ - Temp files │
    │ - Job extract  │  │- DOCX   │  │- Suggest │              │
    │                │  │- Export │  │          │              │
    └────────────────┘  └─────────┘  └──────────┴──────────────┘
                            │
                            ▼
        ┌─────────────────────────────────┐
        │   Local File System             │
        │   - PDF/DOCX files              │
        │   - Uploaded resumes            │
        │   - Generated files             │
        └─────────────────────────────────┘
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/scrape-job` | Extract job details from URL |
| POST | `/api/upload-resume` | Parse uploaded resume (PDF/DOCX) |
| POST | `/api/get-suggestions` | Get resume improvement suggestions |
| POST | `/api/generate-cover-letter` | Create tailored cover letter |
| POST | `/api/export-resume` | Download resume as PDF or DOCX |
| GET | `/api/health` | Check server status |

## Data Flow

```
1. USER ENTERS JOB URL
   └─→ Job Scraper fetches HTML
       └─→ BeautifulSoup parses job details
           └─→ Frontend displays title, company, description

2. USER UPLOADS RESUME
   └─→ File saved to uploads/
       └─→ Resume Parser extracts text
           └─→ Frontend shows preview

3. USER REQUESTS SUGGESTIONS
   └─→ Both texts sent to Copilot Integration
       └─→ gh copilot CLI called
           └─→ AI suggestions returned
               └─→ Displayed in browser

4. USER EXPORTS RESUME
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

### Libraries
- **python-docx** - Create/read .docx files
- **pdfplumber** - Extract text from PDFs
- **PyPDF2** - PDF manipulation
- **reportlab** - Generate PDF files
- **requests** - HTTP client
- **beautifulsoup4** - HTML/XML parsing

### External Services
- **GitHub Copilot CLI** - AI suggestions (via `copilot -p` command)

## File Roles

### Core Application
- `main.py` - FastAPI app, all 7 endpoints
- `copilot_integration.py` - Wraps `gh copilot suggest` command
- `job_scraper.py` - Multi-board job scraping with fallback parser
- `resume_parser.py` - PDF/DOCX read and write operations

### HTML Interface
- `index.html` - 4-step form wizard
- `script.js` - Event handlers, API calls, state management
- `style.css` - Responsive design with gradient theme

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
- Async file uploads with aiofiles
- Streaming responses for downloads
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
- GitHub Jobs (GitHub-specific CSS selectors)

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
