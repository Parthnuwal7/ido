"""
ZIP file processing service
Handles scanning and extracting files from YouTube Takeout ZIP archives
"""

import zipfile
import io
from typing import Optional

from services.history_locator import find_history




def read_zip_for_files(zip_content: bytes) -> dict:
    """
    Recursively search a ZIP file for target files.
    
    Args:
        zip_content: Raw bytes of the ZIP file
        
    Returns:
        Dictionary with found_files, missing_files, and total_files_in_zip
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            all_files = zf.namelist()
            total_files = len(all_files)

            located = find_history(all_files)

            # Keys stay canonical because the frontend maps over them and posts them
            # back to /extract. The value may point at a .html member -- `formats` is
            # what says which export format was actually found.
            found_files: dict[str, Optional[str]] = {
                "watch-history.json": located.watch.member if located.watch else None,
                "search-history.json": located.search.member if located.search else None,
                "subscriptions.csv": located.subscriptions,
            }
            formats: dict[str, Optional[str]] = {
                "watch-history.json": located.watch.format if located.watch else None,
                "search-history.json": located.search.format if located.search else None,
                "subscriptions.csv": "csv" if located.subscriptions else None,
            }

            missing_files = [
                filename for filename, path in found_files.items()
                if path is None
            ]

            return {
                "found_files": found_files,
                "formats": formats,
                "missing_files": missing_files,
                "total_files_in_zip": total_files
            }

    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file")
    except Exception as e:
        raise ValueError(f"Error processing ZIP file: {str(e)}")


def _content_type_for(path: str, filename: str) -> str:
    """Content type of the bytes actually extracted.

    The canonical keys are always *.json / *.csv, but the member behind
    "watch-history.json" may really be watch-history.html. Deriving the type from the
    key made preprocess run json.loads() on HTML and silently yield zero events.
    """
    member = (path or filename).lower()
    if member.endswith('.html') or member.endswith('.htm'):
        return 'html'
    if member.endswith('.csv'):
        return 'csv'
    return 'json'


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
                    
                    # Tag by the ACTUAL member extension, not the canonical key the
                    # caller asked under: an HTML export arrives under
                    # "watch-history.json" and must still be recognised as HTML.
                    content_type = _content_type_for(path, filename)

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
                        content_type = _content_type_for(path, filename)
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
