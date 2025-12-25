"""
Content preview API routes
Endpoints for displaying file contents
"""

import json
import csv
import io
from fastapi import APIRouter, HTTPException
from models.schemas import PreviewRequest, PreviewResult

router = APIRouter()


def _parse_json_content(content: str, max_items: int = 50) -> dict:
    """Parse JSON content and return summary with sample items."""
    try:
        data = json.loads(content)
        
        if isinstance(data, list):
            return {
                "total_items": len(data),
                "sample_items": data[:max_items],
                "has_more": len(data) > max_items
            }
        elif isinstance(data, dict):
            return {
                "total_items": 1,
                "data": data,
                "has_more": False
            }
        else:
            return {"data": data}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}


def _parse_csv_content(content: str, max_items: int = 50) -> dict:
    """Parse CSV content and return summary with sample items."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        return {
            "total_items": len(rows),
            "headers": reader.fieldnames or [],
            "sample_items": rows[:max_items],
            "has_more": len(rows) > max_items
        }
    except Exception as e:
        return {"error": f"Invalid CSV: {str(e)}"}


@router.post("/preview", response_model=PreviewResult)
async def preview_content(request: PreviewRequest):
    """
    Parse and return file contents for display.
    
    Returns structured preview of watch history, search history, and subscriptions.
    """
    result = PreviewResult(timezone=request.timezone)
    
    for file in request.files:
        if file.filename == "watch-history.json":
            result.watch_history = _parse_json_content(file.content)
        elif file.filename == "search-history.json":
            result.search_history = _parse_json_content(file.content)
        elif file.filename == "subscriptions.csv":
            result.subscriptions = _parse_csv_content(file.content)
    
    return result


@router.get("/timezones")
async def get_timezones():
    """Get list of available timezones."""
    from services.timezone_service import get_common_timezones
    
    return {
        "timezones": get_common_timezones()
    }
