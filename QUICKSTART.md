# Quick Start Guide

## 🚀 Fast Setup (5 minutes)

### 1. Prerequisites Check
Verify you have installed:
```bash
# Check Copilot CLI
copilot --version

# Check Python
python3 --version

# Verify Copilot is available
copilot -p "hello world"
```

### 2. Run Setup Script (Recommended)
```bash
cd /Users/venkat/Documents/Desktop/work/resumes/code/resume_builder
chmod +x setup.sh
./setup.sh
```

### 3. Start the Application
```bash
source venv/bin/activate
python -m app.main
```

The app will be available at: **http://localhost:8000**

---

## 📋 Manual Setup (Alternative)

```bash
# Navigate to project
cd /Users/venkat/Documents/Desktop/work/resumes/code/resume_builder

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m app.main
```

---

## 🎯 How to Use

1. **Paste Job URL** - Copy any LinkedIn, Indeed, or Glassdoor job link
2. **Upload Resume** - Select your PDF or DOCX resume
3. **Get Suggestions** - AI generates resume improvements
4. **Generate Cover Letter** - Optional: create a tailored cover letter
5. **Download** - Export as PDF or DOCX

---

## 🔧 Troubleshooting

**Issue:** "GitHub Copilot CLI is not available"
```bash
# Install Copilot CLI from GitHub
# Visit: https://github.com/github/copilot-cli

# Or via Homebrew (if available)
brew install copilot

# Login to Copilot
copilot login

# Test
copilot -p "test"
```

**Issue:** Permission denied on setup.sh
```bash
chmod +x setup.sh
```

**Issue:** Module not found
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📁 Project Files Structure

```
resume_builder/
├── app/
│   ├── main.py              # FastAPI server
│   ├── resume_parser.py     # PDF/DOCX handling
│   ├── job_scraper.py       # Web scraping
│   ├── copilot_integration.py # Copilot CLI
│   └── static/              # Frontend (HTML/CSS/JS)
├── uploads/                 # Uploaded files
├── requirements.txt         # Dependencies
├── setup.sh                 # Auto-setup script
└── README.md               # Full documentation
```

---

## 🎨 Features Included

✅ **Multi-Job Board Support**
- LinkedIn Jobs
- Indeed
- Glassdoor
- GitHub Jobs
- Generic HTML parsing

✅ **Resume Management**
- PDF & DOCX parsing
- Text extraction
- Export to PDF or DOCX

✅ **AI Features (via GitHub Copilot)**
- Resume improvement suggestions
- Cover letter generation
- Custom analysis

✅ **Web Interface**
- Step-by-step workflow
- Real-time preview
- Error handling
- Responsive design

---

## 📞 Support

### Common Issues

1. **Copilot Not Working**
   - Verify GitHub authentication: `gh auth status`
   - Check extension: `gh extension list | grep copilot`

2. **File Upload Fails**
   - Ensure file is valid PDF or DOCX
   - Check file size (should be < 10MB)
   - Try re-exporting from Word/Google Docs

3. **Job Scraping Fails**
   - Verify URL is correct
   - Some sites may block scraping
   - Try a different job board

### Environment Variables (Optional)

Create `.env` file:
```
COPILOT_TIMEOUT=60
MAX_FILE_SIZE=10485760
```

---

## 🚀 Deployment

### Local Development
```bash
python -m app.main
```

### Production (Uvicorn)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "app.main"]
```

Run:
```bash
docker build -t resume-builder .
docker run -p 8000:8000 resume-builder
```

---

**Ready?** Let's go! 🎉
