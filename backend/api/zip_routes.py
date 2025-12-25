"""
ZIP processing API routes
Endpoints for scanning and extracting files from YouTube Takeout ZIPs
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from models.schemas import ScanResult, ExtractResult, ExtractedFile
from services.zip_service import read_zip_for_files, extract_files_by_paths
from services.timezone_service import validate_timezone

router = APIRouter()


@router.post("/read", response_model=ScanResult)
async def read_zip(file: UploadFile = File(...)):
    """
    Scan a ZIP file for target YouTube Takeout files.
    
    Returns paths to found files and list of missing files.
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    try:
        content = await file.read()
        result = read_zip_for_files(content)
        
        return ScanResult(
            found_files=result["found_files"],
            missing_files=result["missing_files"],
            total_files_in_zip=result["total_files_in_zip"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ZIP: {str(e)}")


@router.post("/extract", response_model=ExtractResult)
async def extract_zip(
    file: UploadFile = File(...),
    paths: str = Form(""),  # JSON string of paths dict
    timezone: str = Form("UTC")
):
    """
    Extract specific files from a ZIP using provided paths.
    
    Args:
        file: The ZIP file
        paths: JSON string mapping filename to path in ZIP
        timezone: User's timezone for timestamp conversion
    """
    import json
    
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    if not validate_timezone(timezone):
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone}")
    
    try:
        paths_dict = json.loads(paths) if paths else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid paths JSON")
    
    if not paths_dict:
        raise HTTPException(status_code=400, detail="No paths provided for extraction")
    
    try:
        content = await file.read()
        extracted_files, missing_files = extract_files_by_paths(content, paths_dict)
        
        return ExtractResult(
            files=[ExtractedFile(**f) for f in extracted_files],
            timezone=timezone,
            missing_files=missing_files
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting files: {str(e)}")
