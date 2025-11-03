# 🚀 Quick Start Guide

Get the NSFW Image Asset Manager running in 3 steps!

## Step 1: Setup Environment

```bash
cd nsfw_db_manager

# Copy example env file
cp .env.example .env

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt
```

## Step 2: Start the Backend

```bash
cd nsfw_db_manager/backend
python run_server.py
```

You should see:
```
🚀 Starting NSFW Image Asset Manager API...
📖 API Documentation: http://localhost:8001/docs
```

✅ Backend is running at **http://localhost:8001**

## Step 3: Start the Frontend (New Terminal)

Open a **new terminal** and run:

```bash
cd nsfw_db_manager/frontend
python gradio_app.py
```

You should see:
```
🚀 Starting Gradio Frontend...
Running on local URL:  http://127.0.0.1:7860
```

✅ Frontend is running at **http://localhost:7860**

## Usage

### Upload an Image
1. Go to the **Upload** tab
2. Select an image file
3. Add metadata tags (angle_1, action_1, etc.)
4. Click "Upload Image"

### Search Images
1. Go to the **Search** tab
2. Enter filter criteria (leave empty to show all)
3. Click "Search"
4. Browse results in the gallery

### View Asset Details
1. Go to the **Asset Details** tab
2. Enter an asset ID
3. Click "Get Details"

## Configuration

By default, images are stored locally in `backend/uploads/images/`.

To change storage location, edit `.env`:
```env
USE_LOCAL_STORAGE=true
LOCAL_UPLOAD_DIR=uploads/images
```

## Troubleshooting

**Backend won't start:**
- Check if port 8001 is already in use
- Make sure you're in the `backend` directory
- Check `.env` file exists

**Frontend can't connect to backend:**
- Make sure backend is running first
- Check backend is on http://localhost:8001
- Look for error messages in backend terminal

**Images not displaying:**
- Make sure `USE_LOCAL_STORAGE=true` in `.env`
- Check files exist in `backend/uploads/images/`
- Verify file permissions

## Next Steps

- Check out the full [README.md](README.md) for API documentation
- View the Swagger docs at http://localhost:8001/docs
- Explore the API endpoints
