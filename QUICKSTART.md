# Quick Start Guide

## Fast Setup

1. Check prerequisites:
```bash
python3 --version
copilot --version
copilot -p "hello world"
```

2. Install dependencies:
```bash
cd /Users/venkat/Documents/Desktop/work/resumes/code/resume_builder
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Start the app:
```bash
python -m app.main
```

Open: **http://localhost:8000**

## What You Can Do

1. Add a job and keep its summary, notes, and linked resume together.
2. Upload a resume in PDF, DOCX, TXT, or LaTeX format.
3. Generate Copilot recommendations and then apply them to create a new tailored resume.
4. Use the LaTeX editor to adjust font size, format source, save, and compile to PDF.
5. Generate a cover letter and export PDF/DOCX files from the app.

## Useful Checks

```bash
gh auth status
gh extension list | grep copilot
```

## Project Layout

```text
resume_builder/
├── app/
│   ├── main.py
│   ├── resume_manager.py
│   ├── tailoring.py
│   ├── job_tracker.py
│   ├── resume_parser.py
│   └── static/
├── data/
├── uploads/
├── requirements.txt
└── README.md
```

## Notes

- LaTeX resumes keep both original and updated source files.
- Copilot prompt history is saved in the browser.
- Generated files are listed in the Job Applications area.
