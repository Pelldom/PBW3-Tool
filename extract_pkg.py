import os
import zipfile

pkg_path = "build/PBW3 Tool_v1.02/PBW3 Tool.pkg"
extract_path = "build/PBW3 Tool_v1.02/extracted_pkg"

# Ensure the extraction directory exists
os.makedirs(extract_path, exist_ok=True)

# Attempt to extract the .pkg file assuming it's a zip archive
try:
    with zipfile.ZipFile(pkg_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extraction successful.")
except zipfile.BadZipFile:
    print("The file is not a zip archive or is corrupted.")
except Exception as e:
    print(f"An error occurred: {e}") 