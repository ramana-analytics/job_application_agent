#!/bin/bash

echo "🚀 Resume Builder Setup"
echo "======================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check GitHub Copilot CLI
if ! command -v copilot &> /dev/null; then
    echo "❌ GitHub Copilot CLI not found."
    echo "Download from: https://github.com/github/copilot-cli"
    exit 1
fi

echo "✅ GitHub Copilot CLI found"

# Check authentication
if ! copilot -p "test" &> /dev/null; then
    echo "⚠️  Copilot not authenticated."
    echo "Running: copilot login"
    copilot login
fi

echo "✅ Copilot authentication verified"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup Complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python -m app.main"
echo "  3. Open: http://localhost:8000"
echo ""
