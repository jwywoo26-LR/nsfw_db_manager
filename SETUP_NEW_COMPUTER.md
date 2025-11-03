# Setup Guide for New Computer

This guide explains how to set up and run the NSFW Database Manager on a new computer.

## Prerequisites

Before you start, make sure you have:

### 1. **Python 3.10+**
```bash
# Check your Python version
python3 --version

# Should show Python 3.10 or higher
```

If you don't have Python installed:
- **macOS**: `brew install python@3.12` or download from [python.org](https://www.python.org)
- **Linux**: `sudo apt install python3 python3-pip python3-venv`
- **Windows**: Download from [python.org](https://www.python.org)

### 2. **Git** (to clone the repository)
```bash
git --version
```

If not installed:
- **macOS**: `brew install git` or install Xcode Command Line Tools
- **Linux**: `sudo apt install git`
- **Windows**: Download from [git-scm.com](https://git-scm.com)

## Step-by-Step Setup

### Step 1: Clone the Repository

```bash
cd ~/your-projects-folder
git clone <your-repo-url>
cd webtoon-cut-assets
```

### Step 2: Check Required Files

Make sure these files exist:
```bash
ls -la resources/csvs/nsfw_data_v3.csv
ls -la resources/nsfw_data/*.png | head -5
ls -la nsfw_db_manager/backend/.env
```

### Step 3: Install Backend Dependencies

```bash
cd nsfw_db_manager/backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Expected packages**: fastapi, uvicorn, sqlalchemy, boto3, python-dotenv, pillow, pydantic, python-multipart

### Step 4: Configure Environment

Check the `.env` file exists and has the correct settings:

```bash
cd nsfw_db_manager/backend
cat .env
```

It should contain:
```env
# Database - Using SQLite for local storage
DATABASE_URL=sqlite:///./nsfw_assets.db

# Storage Configuration - Use local file storage
USE_LOCAL_STORAGE=true
LOCAL_UPLOAD_DIR=uploads/images
```

**IMPORTANT**: Make sure there's NO system-level `DATABASE_URL` variable:
```bash
env | grep DATABASE_URL
```

If you see a PostgreSQL URL, unset it:
```bash
unset DATABASE_URL

# Make it permanent (add to ~/.bashrc or ~/.zshrc):
echo 'unset DATABASE_URL' >> ~/.bashrc  # or ~/.zshrc
```

### Step 5: Run the Setup Script

From the project root:

```bash
cd /path/to/webtoon-cut-assets

# Make script executable (first time only)
chmod +x setup_and_upload.sh

# Run the setup
./setup_and_upload.sh
```

This will:
1. Stop any running backend
2. Clean old databases
3. Start the backend server
4. Upload all 700 images from the CSV

**Expected output:**
```
====================================================================
NSFW DB Manager - Setup and Upload
====================================================================
...
Backend is ready!
✓ Backend is running

[4/4] Uploading CSV data to database...
...
Total images: 700
✓ Successful: 682 (or similar)
Success rate: 97.4%
```

### Step 6: Verify Setup

```bash
# Check database was created
ls -lh nsfw_db_manager/backend/nsfw_assets.db

# Check images were uploaded
du -sh nsfw_db_manager/backend/uploads/images/

# Test API
curl http://127.0.0.1:8001/api/health
```

## Quick Reference Commands

### Start Backend Only (without upload)
```bash
cd nsfw_db_manager/backend
unset DATABASE_URL  # Important!
source .venv/bin/activate
python run_server.py
```

### Upload CSV Data Only (backend must be running)
```bash
cd /path/to/webtoon-cut-assets
python3 upload_csv_to_db.py
```

### Stop Backend
```bash
pkill -f "python.*run_server"
```

### View API Documentation
Once backend is running:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution**: Make sure virtual environment is activated and dependencies are installed:
```bash
cd nsfw_db_manager/backend
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: "DATABASE_URL pointing to PostgreSQL"
**Solution**: Unset the environment variable:
```bash
unset DATABASE_URL
# Then restart backend
```

To make permanent, add to your shell config:
```bash
echo 'unset DATABASE_URL' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # reload config
```

### Issue: "Port 8001 already in use"
**Solution**: Stop any existing backend:
```bash
pkill -f "python.*run_server"
# Wait 2 seconds, then restart
```

### Issue: "Images not found during upload"
**Solution**: Make sure you're running from the project root:
```bash
cd /path/to/webtoon-cut-assets
python3 upload_csv_to_db.py
```

And that images exist:
```bash
ls resources/nsfw_data/*.png | wc -l
# Should show 700 files
```

### Issue: Script fails with "bash: ./setup_and_upload.sh: Permission denied"
**Solution**: Make script executable:
```bash
chmod +x setup_and_upload.sh
```

## Files You Need

When setting up on a new computer, you need these files/folders:

### Required Files
```
webtoon-cut-assets/
├── resources/
│   ├── csvs/
│   │   └── nsfw_data_v3.csv          # CSV with metadata
│   └── nsfw_data/                     # 700 PNG files
│       └── *.png
├── nsfw_db_manager/
│   └── backend/
│       ├── .env                       # Environment config
│       ├── requirements.txt           # Python dependencies
│       ├── run_server.py             # Backend startup
│       └── src/                       # Backend source code
│           ├── main.py
│           ├── models.py
│           ├── database.py
│           ├── schemas.py
│           └── s3_utils.py
├── upload_csv_to_db.py               # Upload script
└── setup_and_upload.sh               # Automated setup script
```

### Auto-Generated (don't need to copy)
```
nsfw_db_manager/backend/
├── .venv/                            # Virtual environment (auto-created)
├── nsfw_assets.db                    # Database (auto-created)
└── uploads/images/                   # Uploaded images (auto-created)
```

## Transfer to New Computer

### Option 1: Git Clone (Recommended)
```bash
# On new computer
git clone <repo-url>
cd webtoon-cut-assets
./setup_and_upload.sh
```

**Note**: If images are not in git (too large), you'll need to copy them separately.

### Option 2: Manual Copy

Copy these folders to the new computer:
```bash
# On old computer, create archive
cd /path/to/webtoon-cut-assets
tar -czf nsfw-db-transfer.tar.gz \
  resources/ \
  nsfw_db_manager/backend/src/ \
  nsfw_db_manager/backend/.env \
  nsfw_db_manager/backend/requirements.txt \
  nsfw_db_manager/backend/run_server.py \
  upload_csv_to_db.py \
  setup_and_upload.sh

# Transfer nsfw-db-transfer.tar.gz to new computer

# On new computer
tar -xzf nsfw-db-transfer.tar.gz
cd webtoon-cut-assets
./setup_and_upload.sh
```

### Option 3: Copy Existing Database

If you already have the database set up and just want to move it:

```bash
# On old computer
cd nsfw_db_manager/backend
tar -czf db-and-images.tar.gz nsfw_assets.db uploads/

# Transfer to new computer
# On new computer
cd nsfw_db_manager/backend
tar -xzf db-and-images.tar.gz

# Start backend only (no need to re-upload)
source .venv/bin/activate
python run_server.py
```

## System Requirements

- **Python**: 3.10 or higher
- **Disk Space**: ~8 GB (for images + database)
- **RAM**: 2 GB minimum
- **OS**: macOS, Linux, or Windows

## Summary

**Minimum steps on a new computer:**

1. Install Python 3.10+
2. Clone/copy the repository
3. Install dependencies: `cd nsfw_db_manager/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
4. Unset DATABASE_URL if needed: `unset DATABASE_URL`
5. Run setup: `./setup_and_upload.sh`

**That's it!** The script handles everything else automatically.

## Need Help?

- Check backend logs: `tail -f nsfw_db_manager/backend/backend.log`
- Check API health: `curl http://127.0.0.1:8001/api/health`
- See detailed docs: [DB_SETUP_SUMMARY.md](DB_SETUP_SUMMARY.md)
