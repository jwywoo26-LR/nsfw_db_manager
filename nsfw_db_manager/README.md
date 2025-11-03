# NSFW Image Asset Manager - FastAPI Backend

A FastAPI-based backend service for managing NSFW image assets with S3 storage and metadata management.

## Features

- 📤 **Upload Image Assets**: Upload images to S3 with metadata (angles, actions)
- 🔍 **Search**: Search images by angle and action tags
- 💾 **Database**: SQLAlchemy ORM with support for SQLite/PostgreSQL
- ☁️ **S3 Storage**: Automatic image upload to AWS S3
- 🔄 **Soft Delete**: Support for both soft and hard deletion
- 📊 **Pagination**: Built-in pagination for search results
- 📖 **Auto-docs**: Interactive API documentation with Swagger UI

## Setup

### 1. Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy boto3 python-dotenv pillow pydantic
```

Or add to your `requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
boto3>=1.28.0
python-dotenv>=1.0.0
pillow>=10.0.0
pydantic>=2.0.0
python-multipart>=0.0.6
```

### 2. Environment Variables

Create a `.env` file in the `nsfw_db_manager` directory (copy from `.env.example`):

```env
# Storage Configuration
USE_LOCAL_STORAGE=true  # Set to false to use S3
LOCAL_UPLOAD_DIR=uploads/images

# Database Configuration
DATABASE_URL=sqlite:///./nsfw_assets.db

# AWS S3 Configuration (only needed if USE_LOCAL_STORAGE=false)
# AWS_ACCESS_KEY_ID=your_aws_access_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret_key
# AWS_DEFAULT_REGION=ap-northeast-2
# S3_BUCKET=your-bucket-name
```

**For local development** (default): Images are stored in `backend/uploads/images/` directory.
**For production with S3**: Set `USE_LOCAL_STORAGE=false` and configure AWS credentials.

### 3. Run the Backend Server

```bash
cd nsfw_db_manager/backend
python run_server.py
```

The API will be available at:
- **API**: http://localhost:8001
- **Swagger UI Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### 4. Run the Gradio Frontend (Optional)

In a **separate terminal**:

```bash
cd nsfw_db_manager/frontend
pip install -r requirements.txt
python gradio_app.py
```

The Gradio UI will be available at:
- **Frontend**: http://localhost:7860

**Gradio Features:**
- 📤 Upload images with metadata tags
- 🔍 Search images by angle/action filters
- 📊 View image gallery results
- 📋 Get detailed asset information

## API Endpoints

### Upload Image Asset
```http
POST /api/upload
Content-Type: multipart/form-data

Parameters:
- file: Image file (required)
- angle_1: string (optional)
- angle_2: string (optional)
- action_1: string (optional)
- action_2: string (optional)
- action_3: string (optional)
```

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@image.png" \
  -F "angle_1=front" \
  -F "action_1=standing"
```

**Example using Python:**
```python
import requests

files = {'file': open('image.png', 'rb')}
data = {
    'angle_1': 'front',
    'angle_2': 'side',
    'action_1': 'standing'
}
response = requests.post('http://localhost:8000/api/upload', files=files, data=data)
print(response.json())
```

### Search Image Assets
```http
GET /api/search?angle_1=front&action_1=standing&limit=50&offset=0

Query Parameters:
- angle_1: string (optional)
- angle_2: string (optional)
- action_1: string (optional)
- action_2: string (optional)
- action_3: string (optional)
- include_deleted: boolean (default: false)
- limit: integer (default: 100, max: 1000)
- offset: integer (default: 0)
```

**Example:**
```bash
curl "http://localhost:8000/api/search?angle_1=front&limit=10"
```

### Download Image Asset
```http
GET /api/download/{asset_id}
```

**Example:**
```bash
curl "http://localhost:8000/api/download/1" -L -o downloaded_image.png
```

### Get Asset Metadata
```http
GET /api/assets/{asset_id}
```

### Delete Image Asset
```http
DELETE /api/assets/{asset_id}?hard_delete=false

Query Parameters:
- hard_delete: boolean (default: false)
  - false: Soft delete (sets deleted_at timestamp)
  - true: Hard delete (removes from DB and S3)
```

### Health Check
```http
GET /api/health
```

## Database Schema

### ImageAsset Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| created_at | DateTime | Creation timestamp |
| deleted_at | DateTime | Soft delete timestamp (nullable) |
| angle_1 | String | First angle tag (indexed) |
| angle_2 | String | Second angle tag (indexed) |
| action_1 | String | First action tag (indexed) |
| action_2 | String | Second action tag (indexed) |
| action_3 | String | Third action tag (indexed) |
| s3_url | String | S3 URL of the image |
| original_filename | String | Original filename |

## Project Structure

```
nsfw_db_manager/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── database.py      # Database configuration
│   │   └── s3_utils.py      # S3 upload utilities
│   └── run_server.py        # Server startup script
├── README.md
└── .env                     # Environment variables
```

## Development

### Initialize Database

The database is automatically initialized on server startup. To manually reset:

```python
from src.database import reset_db
reset_db()
```

### Running in Production

For production, use a production-ready server:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or with gunicorn:

```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Examples

### Complete Upload Workflow

```python
import requests

# 1. Upload an image
with open('nsfw_image.png', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f},
        data={
            'angle_1': 'front',
            'angle_2': 'top',
            'action_1': 'standing',
            'action_2': 'arms_crossed'
        }
    )

upload_result = response.json()
asset_id = upload_result['asset']['id']
print(f"Uploaded asset ID: {asset_id}")

# 2. Search for similar images
search_response = requests.get(
    'http://localhost:8000/api/search',
    params={
        'angle_1': 'front',
        'action_1': 'standing',
        'limit': 10
    }
)

results = search_response.json()
print(f"Found {results['total']} matching assets")

# 3. Download an image
download_response = requests.get(
    f'http://localhost:8000/api/download/{asset_id}',
    allow_redirects=True
)

with open('downloaded.png', 'wb') as f:
    f.write(download_response.content)
```

## License

Private project - All rights reserved
