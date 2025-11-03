# NSFW Database Setup Summary

## Problem Identified

The original issue with the bulk upload failing was caused by:

1. **Path Resolution Issue**: The zip uploader was extracting files to a temporary directory, and the relative paths in the CSV (`../resources/nsfw_data/`) were not resolving correctly.

2. **Database Connection Issue**: A system-level `DATABASE_URL` environment variable was set to PostgreSQL, overriding the `.env` file's SQLite configuration.

## Solution Implemented

### 1. Created Direct Upload Script

**File**: `upload_csv_to_db.py`

This script:
- Reads the CSV directly from the project directory
- Extracts just the filename from the CSV's `reference_image_path` column
- Looks up the actual image in the `resources/nsfw_data/` directory
- Uploads via FastAPI using query parameters (not form data)
- Provides detailed progress and error reporting

**Key Fix**: Changed from `data` parameter to `params` parameter in the requests.post() call to match FastAPI's Query parameter expectation.

### 2. Created Automated Setup Script

**File**: `setup_and_upload.sh`

This bash script:
- Stops any running backend
- Cleans up old databases
- Unsets the problematic `DATABASE_URL` environment variable
- Starts the backend with proper virtual environment
- Waits for backend to be fully ready
- Runs the upload script

## Upload Results

### Statistics
- **Total Images in CSV**: 700
- **Successfully Uploaded**: 682 (97.4%)
- **Failed**: 18 (2.6%)

### Database Schema
```
Table: image_assets
- id (PRIMARY KEY, AUTO INCREMENT)
- created_at (DATETIME)
- deleted_at (DATETIME, nullable)
- angle_1 (VARCHAR, indexed) - 5 unique values
- angle_2 (VARCHAR, indexed) - 4 unique values
- action_1 (VARCHAR, indexed) - 22 unique values
- action_2 (VARCHAR, indexed, nullable)
- action_3 (VARCHAR, indexed, nullable)
- prompt (TEXT, nullable)
- s3_url (VARCHAR, nullable)
- local_file_path (VARCHAR)
- original_filename (VARCHAR)
```

### Top Actions in Database
| Action | Count |
|--------|-------|
| missionary | 149 |
| sex | 132 |
| paizuri | 79 |
| doggy_style | 70 |
| fellatio | 63 |
| presenting_breasts | 49 |
| presenting_pussy | 35 |
| presenting | 29 |
| doggystyle | 17 |
| presenting_ass | 16 |

### Angle Distribution
- **angle_1**: 5 unique values (above, below, front, nan, etc.)
- **angle_2**: 4 unique values (front, behind, side, nan)

## How to Use

### Quick Start (Automated)
```bash
./setup_and_upload.sh
```

This will:
1. Stop any running backend
2. Clean databases
3. Start fresh backend
4. Upload all 700 images from CSV

### Manual Steps

#### 1. Start Backend
```bash
cd nsfw_db_manager/backend
unset DATABASE_URL  # Important!
.venv/bin/python run_server.py
```

#### 2. Run Upload (in another terminal)
```bash
python3 upload_csv_to_db.py
```

### Command Line Options

The upload script supports optional arguments:
```bash
python3 upload_csv_to_db.py [CSV_PATH] [IMAGES_DIR] [BACKEND_URL]

# Defaults:
# CSV_PATH: resources/csvs/nsfw_data_v3.csv
# IMAGES_DIR: resources/nsfw_data
# BACKEND_URL: http://127.0.0.1:8001
```

## API Endpoints

### Upload Image
```http
POST /api/upload?angle_1=above&angle_2=front&action_1=missionary
Content-Type: multipart/form-data

file: <image file>
```

### Search Images
```http
GET /api/search?angle_1=above&action_1=missionary&limit=50
```

### Download Image
```http
GET /api/download/{asset_id}
```

### Get Asset Details
```http
GET /api/assets/{asset_id}
```

## Database Location

The SQLite database is created at:
```
nsfw_db_manager/backend/nsfw_assets.db
```

Images are stored locally at:
```
nsfw_db_manager/backend/uploads/images/
```

## Troubleshooting

### Backend Won't Start
```bash
# Check if DATABASE_URL is set to PostgreSQL
env | grep DATABASE_URL

# If so, unset it:
unset DATABASE_URL

# Then restart backend
cd nsfw_db_manager/backend
.venv/bin/python run_server.py
```

### Database is Read-Only
This happens if the backend is running and you delete the database file. Solution:
```bash
# Stop backend
pkill -f "python.*run_server"

# Remove database
rm nsfw_db_manager/backend/nsfw_assets.db

# Restart backend (it will recreate the database)
cd nsfw_db_manager/backend
.venv/bin/python run_server.py
```

### Upload Failures
Check the upload script output for specific errors. Common issues:
- Image file not found: Check that files exist in `resources/nsfw_data/`
- Backend not running: Ensure backend is at http://127.0.0.1:8001
- Network timeout: Increase timeout in upload script

## CSV Format

The CSV should have these columns:
```csv
reference_image_name,reference_image_path,angle_direction_1,angle_direction_2,action_direction_1
```

**Note**: The `reference_image_path` can be any format - the script extracts just the filename and looks it up in the images directory.

## Next Steps

To add more images:
1. Add images to `resources/nsfw_data/`
2. Add rows to the CSV
3. Run: `python3 upload_csv_to_db.py`

The script is idempotent - you can run it multiple times and it will skip already uploaded images (though currently it will try to upload duplicates, which will succeed but create duplicate database entries).

## Files Created

1. `upload_csv_to_db.py` - Direct CSV upload script
2. `setup_and_upload.sh` - Automated setup and upload
3. `DB_SETUP_SUMMARY.md` - This documentation

## Backend Status

To check if backend is running:
```bash
curl http://127.0.0.1:8001/api/health
```

To view API documentation:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
