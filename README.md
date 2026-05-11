# Resume Builder - Job URL to Resume Optimizer

A web application that helps you optimize your resume based on job descriptions. It scrapes job postings, analyzes them, and uses GitHub Copilot to suggest improvements to your resume.

## Features

✅ **Job Scraping** - Extract job descriptions from LinkedIn, Indeed, Glassdoor, GitHub Jobs, and other job boards
✅ **Resume Parsing** - Upload and parse PDF and DOCX resume files
✅ **AI-Powered Suggestions** - Get resume improvement suggestions using GitHub Copilot
✅ **Cover Letter Generator** - Automatically generate cover letters tailored to the job
✅ **Multi-Format Export** - Download optimized resume in PDF or DOCX format
✅ **Web-Based Interface** - Clean, intuitive UI with step-by-step workflow

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

2. **Open in browser:**
Navigate to `http://localhost:8000`

## How to Use

### Step 1: Add Job Posting
- Paste the job URL (LinkedIn, Indeed, Glassdoor, etc.)
- Click "Scrape Job Details"
- Review the extracted job title, company, and description

### Step 2: Upload Your Resume
- Select your resume file (PDF or DOCX)
- Click "Upload Resume"
- Preview the extracted text

### Step 3: Review Suggestions
- Click "Get Resume Suggestions" to get AI-powered improvements
- Click "Generate Cover Letter" to create a tailored cover letter
- Review and copy the suggestions

### Step 4: Export Resume
- Enter a filename for your optimized resume
- Download in PDF or DOCX format

## Project Structure

```
resume_builder/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── copilot_integration.py   # GitHub Copilot CLI wrapper
│   ├── job_scraper.py           # Job posting scraper
│   ├── resume_parser.py         # Resume parsing & export
│   └── static/
│       ├── index.html           # Frontend UI
│       ├── style.css            # Styling
│       └── script.js            # Frontend logic
├── uploads/                      # Uploaded files storage
└── requirements.txt              # Python dependencies
```

## API Endpoints

- `GET /` - Serve main page
- `POST /api/scrape-job` - Scrape job description from URL
- `POST /api/upload-resume` - Upload and parse resume
- `POST /api/get-suggestions` - Get resume improvement suggestions
- `POST /api/generate-cover-letter` - Generate cover letter
- `POST /api/export-resume` - Export resume as PDF/DOCX
- `GET /api/health` - Health check

## Troubleshooting

### "GitHub Copilot CLI is not available"
- Ensure `gh` CLI is installed: `which gh`
- Ensure Copilot extension is installed: `gh extension list`
- Authenticate with GitHub: `gh auth login`
- Test: `gh copilot suggest "test"`

### Resume not parsing correctly
- Ensure file is valid PDF or DOCX
- Try re-exporting the file from your document editor
- Check file permissions

### Job scraping fails
- Verify the URL is correct and publicly accessible
- Some websites may require authentication or block scraping
- Try a different job board URL

## Supported Job Boards

- LinkedIn Jobs
- Indeed
- Glassdoor
- GitHub Jobs
- Generic job boards (with basic HTML parsing)

## Dependencies

- **FastAPI** - Modern web framework
- **python-docx** - DOCX file handling
- **pdfplumber** - PDF reading
- **PyPDF2** - PDF utilities
- **reportlab** - PDF generation
- **requests** - HTTP requests
- **beautifulsoup4** - HTML parsing

## Notes

- The application stores uploaded files in the `uploads/` directory
- Job descriptions are scraped in real-time from the provided URLs
- GitHub Copilot suggestions require an active API connection
- This is a client-side optimized tool - all processing happens locally

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
