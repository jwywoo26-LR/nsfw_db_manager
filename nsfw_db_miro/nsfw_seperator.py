import os
import pandas as pd
from pathlib import Path
import shutil


def organize_images_by_action(csv_file_path, resource_dir, base_output_dir='output', image_column='image_name'):
    """
    Create directories based on 'action_direction_1' column and move images from resource folder.

    Args:
        csv_file_path (str): Path to the CSV file
        resource_dir (str): Path to the folder containing images
        base_output_dir (str): Base directory where subdirectories will be created
        image_column (str): Name of the column containing image filenames

    Returns:
        dict: Statistics about the operation
    """
    # Read the CSV file
    df = pd.read_csv(csv_file_path)

    # Check if required columns exist
    if 'action_direction_1' not in df.columns:
        raise ValueError(f"Column 'action_direction_1' not found in CSV. Available columns: {df.columns.tolist()}")

    if image_column not in df.columns:
        raise ValueError(f"Column '{image_column}' not found in CSV. Available columns: {df.columns.tolist()}")

    # Create base output directory if it doesn't exist
    base_path = Path(base_output_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    resource_path = Path(resource_dir)
    if not resource_path.exists():
        raise ValueError(f"Resource directory not found: {resource_dir}")

    # Get unique values from the action_direction_1 column (excluding NaN values)
    unique_actions = df['action_direction_1'].dropna().unique()

    # Create directories for each unique action
    created_dirs = {}
    for action in unique_actions:
        # Clean the action name to make it a valid directory name
        dir_name = str(action).strip().replace('/', '_').replace('\\', '_')
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        created_dirs[action] = dir_path
        print(f"Created directory: {dir_path}")

    print(f"\nTotal directories created: {len(created_dirs)}")

    # Move images to their respective directories
    stats = {
        'moved': 0,
        'skipped_no_action': 0,
        'skipped_not_found': 0,
        'errors': 0
    }

    print("\nMoving images...")
    for _, row in df.iterrows():
        action = row['action_direction_1']
        image_name = row[image_column]

        # Skip if action is NaN
        if pd.isna(action):
            stats['skipped_no_action'] += 1
            continue

        # Skip if image name is NaN
        if pd.isna(image_name):
            stats['skipped_not_found'] += 1
            continue

        # Find the source image
        # If image_name is already a path (contains / or \), use it directly
        # Otherwise, combine with resource_path
        image_name_str = str(image_name)
        if '/' in image_name_str or '\\' in image_name_str:
            # Image name contains path, use it as-is (relative to current directory)
            source_image = Path(image_name_str)
            # Extract just the filename for destination
            filename_only = Path(image_name_str).name
        else:
            # Just a filename, combine with resource_path
            source_image = resource_path / image_name_str
            filename_only = image_name_str

        if not source_image.exists():
            print(f"Warning: Image not found: {source_image}")
            stats['skipped_not_found'] += 1
            continue

        # Get destination directory
        dir_name = str(action).strip().replace('/', '_').replace('\\', '_')
        dest_dir = base_path / dir_name
        dest_image = dest_dir / filename_only

        # Move the image
        try:
            shutil.move(str(source_image), str(dest_image))
            stats['moved'] += 1
            if stats['moved'] % 100 == 0:
                print(f"Moved {stats['moved']} images...")
        except Exception as e:
            print(f"Error moving {image_name}: {e}")
            stats['errors'] += 1

    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Images moved: {stats['moved']}")
    print(f"  Skipped (no action): {stats['skipped_no_action']}")
    print(f"  Skipped (not found): {stats['skipped_not_found']}")
    print(f"  Errors: {stats['errors']}")
    print(f"{'='*50}")

    return stats


def main():
    """
    Main function to organize images by action_direction_1.
    Set your paths here.
    """
    # SET YOUR PATHS HERE
    csv_file_path = '../resources/csvs/nsfw_data_v3.csv'
    resource_directory = '../resources/nsfw_data'
    output_directory = '../resources/nsfw_data_by_action'
    image_column_name = 'reference_image_path'  # Change this to match your CSV column name

    try:
        stats = organize_images_by_action(
            csv_file_path,
            resource_directory,
            output_directory,
            image_column_name
        )
        print(f"\nSuccess! Organized images into '{output_directory}'")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
