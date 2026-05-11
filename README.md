# Resume Builder - Resume + Job Tracker

A web application for managing resumes and job applications in one place. It tracks jobs, stores resumes, generates Copilot-powered recommendations, supports LaTeX editing and PDF preview, and can create tailored resume drafts from a job recommendation flow.

## Features

✅ **Job Tracking** - Store job details, status, notes, resume linkage, and Copilot summary data
✅ **Resume Management** - Upload PDF, DOCX, TXT, and LaTeX resume files
✅ **LaTeX Resume Editor** - Edit .tex resumes directly, format source, adjust editor font size, and compile to PDF
✅ **Copilot Suggestions** - Generate resume recommendations, summaries, and cover letters with GitHub Copilot
✅ **Recommendation-to-Resume Flow** - Apply recommendations to create a new tailored resume and open it in Resumes
✅ **Multi-Format Export** - Export resumes to PDF or DOCX and keep generated files in the Job Applications view
✅ **Web-Based Interface** - Three-pane UI with persistent layout controls and job/resume navigation

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
│   ├── main.py                  # FastAPI application and API routes
│   ├── storage.py               # JSON persistence helpers
│   ├── resume_manager.py        # Resume CRUD, versioning, ATS updates
│   ├── tailoring.py             # Copilot-based tailoring and cover letters
│   ├── copilot_integration.py   # GitHub Copilot CLI wrapper
│   ├── job_scraper.py           # Job posting scraper
│   ├── job_tracker.py           # Job CRUD and pipeline helpers
│   ├── resume_parser.py         # Resume parsing, LaTeX extraction, export
│   └── static/
│       ├── index.html           # Frontend UI
│       ├── style.css            # Styling
│       └── script.js            # Frontend logic
├── data/                        # JSON data store for jobs, resumes, files
├── uploads/                     # Uploaded and generated files
└── requirements.txt             # Python dependencies
```

## API Endpoints

- `GET /` - Serve the main app UI
- `GET /api/resumes` - List resumes
- `POST /api/resumes/upload` - Upload and parse a resume
- `PATCH /api/resumes/{resume_id}/text` - Save edited resume text
- `POST /api/resumes/{resume_id}/compile-pdf` - Compile LaTeX resume to PDF
- `GET /api/jobs` - List jobs
- `POST /api/jobs/{job_id}/recommendations` - Generate resume recommendations
- `POST /api/jobs/{job_id}/recommendations/apply` - Create a tailored resume from recommendations
- `POST /api/cover-letter` - Generate a tailored cover letter
- `GET /api/application-files` - List generated files

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
