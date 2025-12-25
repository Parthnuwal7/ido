"""
ZIP file processing service
Handles scanning and extracting files from YouTube Takeout ZIP archives
"""

import zipfile
import io
from typing import Optional


# Target files to look for in the ZIP
TARGET_FILES = {
    "watch-history.json": None,
    "search-history.json": None,
    "subscriptions.csv": None
}


def read_zip_for_files(zip_content: bytes) -> dict:
    """
    Recursively search a ZIP file for target files.
    
    Args:
        zip_content: Raw bytes of the ZIP file
        
    Returns:
        Dictionary with found_files, missing_files, and total_files_in_zip
    """
    found_files: dict[str, Optional[str]] = {
        "watch-history.json": None,
        "search-history.json": None,
        "subscriptions.csv": None
    }
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            all_files = zf.namelist()
            total_files = len(all_files)
            
            for file_path in all_files:
                # Get just the filename from the path
                filename = file_path.split('/')[-1]
                
                # Check if this is one of our target files
                if filename in found_files and found_files[filename] is None:
                    found_files[filename] = file_path
            
            # Determine which files are missing
            missing_files = [
                filename for filename, path in found_files.items() 
                if path is None
            ]
            
            return {
                "found_files": found_files,
                "missing_files": missing_files,
                "total_files_in_zip": total_files
            }
            
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file")
    except Exception as e:
        raise ValueError(f"Error processing ZIP file: {str(e)}")


def extract_files_by_paths(zip_content: bytes, paths: dict[str, str]) -> list[dict]:
    """
    Extract specific files from a ZIP using provided paths.
    
    Args:
        zip_content: Raw bytes of the ZIP file
        paths: Dictionary mapping filename to path in ZIP
        
    Returns:
        List of extracted file dictionaries
    """
    extracted_files = []
    missing_files = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            for filename, path in paths.items():
                try:
                    content = zf.read(path)
                    content_str = content.decode('utf-8')
                    
                    # Determine content type
                    content_type = 'csv' if filename.endswith('.csv') else 'json'
                    
                    extracted_files.append({
                        "filename": filename,
                        "content_type": content_type,
                        "content": content_str,
                        "size_bytes": len(content)
                    })
                except KeyError:
                    missing_files.append(filename)
                except UnicodeDecodeError:
                    # Try with different encoding
                    try:
                        content_str = content.decode('latin-1')
                        content_type = 'csv' if filename.endswith('.csv') else 'json'
                        extracted_files.append({
                            "filename": filename,
                            "content_type": content_type,
                            "content": content_str,
                            "size_bytes": len(content)
                        })
                    except Exception:
                        missing_files.append(filename)
                        
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file")
    except Exception as e:
        raise ValueError(f"Error extracting from ZIP file: {str(e)}")
    
    return extracted_files, missing_files
