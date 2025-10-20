from typing import Any, Dict
from datetime import datetime

def remove_null_and_empty(obj: Any) -> Any:
    """Recursively remove null, empty dicts/lists, and empty strings from a dict/list."""
    if isinstance(obj, dict):
        result = {}
        
        for key, value in obj.items():
            # Skip fields that are not useful for LLMs
            if key in ["links"]:
                continue
                
            cleaned_value = remove_null_and_empty(value)
            
            # Skip empty values
            if cleaned_value in (None, "", {}, []):
                continue
            
            result[key] = cleaned_value
        
        return result
    
    elif isinstance(obj, list):
        result = []
        for item in obj:
            cleaned_item = remove_null_and_empty(item)
            if cleaned_item not in (None, "", {}, []):
                result.append(cleaned_item)
        return result
    
    else:
        return obj


def filter_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Filter Fathom API response: remove sensitive fields and clean empty values."""
    return remove_null_and_empty(response)


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.utcnow().isoformat() + "Z"

