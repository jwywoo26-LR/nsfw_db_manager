# Bulk Upload Structure Guide

This guide explains how to prepare your zip file for bulk uploading images to the NSFW Image Asset Manager.

## Directory Structure

Your zip file should have the following structure:

```
your_archive.zip
├── data.csv                          # CSV file with metadata
└── resources/                        # Folder containing images
    └── nsfw_data/                    # Subfolder for images
        ├── image1.png
        ├── image2.png
        └── image3.png
```

## CSV File Format

### Required Columns

Your CSV file must include these columns:

| Column Name | Type | Required | Description | Example |
|-------------|------|----------|-------------|---------|
| `reference_image_name` | string | Yes | Unique identifier for the image | `standing_front_01` |
| `reference_image_path` | string | Yes | Relative path to the image file from CSV location | `../resources/nsfw_data/image.png` |
| `angle_direction_1` | string | Yes | First angle (vertical) | `above`, `below` |
| `angle_direction_2` | string | Yes | Second angle (horizontal) | `front`, `behind`, `side` |
| `action_direction_1` | string | Yes | Primary action/pose | `standing`, `sitting`, etc. |

### Optional Columns

| Column Name | Type | Required | Description | Example |
|-------------|------|----------|-------------|---------|
| `action_direction_2` | string | No | Secondary action modifier | `leg_lift`, `arm_raised` |
| `action_direction_3` | string | No | Tertiary action modifier | `looking_back` |
| `prompt` | string | No | Description or generation prompt | `a woman standing with one leg lifted` |

## Example CSV File

### data.csv

```csv
reference_image_name,reference_image_path,angle_direction_1,angle_direction_2,action_direction_1,action_direction_2,action_direction_3,prompt
standing_front_01,../resources/nsfw_data/standing_front_01.png,above,front,standing,,,a woman standing facing forward
standing_side_02,../resources/nsfw_data/standing_side_02.png,above,side,standing,leg_lift,,a woman standing with one leg lifted
sitting_behind_01,../resources/nsfw_data/sitting_behind_01.png,below,behind,sitting,,,a woman sitting viewed from behind
lying_front_01,../resources/nsfw_data/lying_front_01.png,above,front,lying,,,a woman lying down facing camera
standing_front_02,../resources/nsfw_data/standing_front_02.png,above,front,standing,arm_raised,looking_back,a woman standing with arm raised looking back
```

## Step-by-Step Instructions

### 1. Prepare Your Images

1. Collect all your images in a folder
2. Organize them in the structure: `resources/nsfw_data/`
3. Name your images descriptively (e.g., `standing_front_01.png`)

### 2. Create the CSV File

1. Open a spreadsheet application (Excel, Google Sheets, etc.)
2. Create columns with the exact names shown above
3. Fill in the metadata for each image
4. For `reference_image_path`, use relative paths: `../resources/nsfw_data/your_image.png`
5. Save as CSV format with filename `data.csv`

### 3. Create the Folder Structure

```bash
mkdir -p bulk_upload/resources/nsfw_data
```

Copy your images to:
```
bulk_upload/
└── resources/
    └── nsfw_data/
        └── (your images here)
```

Place your CSV file at:
```
bulk_upload/
└── data.csv
```

### 4. Create the Zip File

**On macOS/Linux:**
```bash
cd bulk_upload
zip -r ../my_bulk_upload.zip .
```

**On Windows:**
- Right-click the `bulk_upload` folder
- Select "Send to" → "Compressed (zipped) folder"

### 5. Upload via UI

1. Go to the **Bulk Upload** tab in the Gradio interface
2. Click "Browse" and select your zip file
3. Click "Process Bulk Upload"
4. Monitor the progress in the detailed log

## Example: Creating a Sample Upload

Here's a complete example you can follow:

### Create the structure:
```bash
mkdir -p example_upload/resources/nsfw_data
cd example_upload
```

### Create data.csv:
```csv
reference_image_name,reference_image_path,angle_direction_1,angle_direction_2,action_direction_1,prompt
test_01,../resources/nsfw_data/test_01.png,above,front,standing,test image 1
test_02,../resources/nsfw_data/test_02.png,below,side,sitting,test image 2
```

### Add your images:
```bash
# Copy your images to resources/nsfw_data/
cp /path/to/test_01.png resources/nsfw_data/
cp /path/to/test_02.png resources/nsfw_data/
```

### Create zip:
```bash
zip -r example_upload.zip .
```

### Upload:
Upload `example_upload.zip` via the Bulk Upload tab

## Common Issues & Solutions

### Issue: "Image not found"
- **Cause:** Incorrect path in CSV
- **Solution:** Ensure paths are relative from CSV location: `../resources/nsfw_data/image.png`

### Issue: "No CSV file found"
- **Cause:** CSV file is in a subdirectory or has wrong name
- **Solution:** Place CSV file at the root level of your zip

### Issue: "Column not found"
- **Cause:** Missing required columns in CSV
- **Solution:** Ensure all required columns are present with exact names

### Issue: Empty values uploaded
- **Cause:** Blank cells in optional columns
- **Solution:** This is normal - optional fields can be empty

## Path Format Examples

✅ **Correct:**
```csv
reference_image_path
../resources/nsfw_data/image1.png
../resources/nsfw_data/subfolder/image2.png
resources/nsfw_data/image3.png
```

❌ **Incorrect:**
```csv
reference_image_path
/absolute/path/to/image.png
C:\Windows\path\to\image.png
image.png (if not in same folder as CSV)
```

## Tips

1. **Use consistent naming:** Name your images descriptively
2. **Test with a small batch first:** Upload 2-3 images to verify the structure works
3. **Keep CSV simple:** Start with only required columns, add optional ones later
4. **Check file extensions:** Ensure image paths match actual file extensions (.png, .jpg, etc.)
5. **Validate CSV:** Open in a text editor to ensure no formatting issues

## Download Sample Template

A sample template structure is available at:
- [Download sample_bulk_upload.zip](#) (create this file following the structure above)
