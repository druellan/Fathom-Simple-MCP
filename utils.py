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
    # First, apply the key filtering
    filtered = filter_sensitive_keys(response)
    # Then, remove null and empty values
    return remove_null_and_empty(filtered)


def filter_sensitive_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter specific keys from the response data to reduce output size.
    Removes meeting_title, calendar_invitees_domains_type from items,
    and email_domain from calendar_invitees and recorded_by.
    """
    if not isinstance(data, dict):
        return data

    # Make a copy to avoid modifying the original
    filtered = data.copy()

    if "items" in filtered and isinstance(filtered["items"], list):
        for item in filtered["items"]:
            if isinstance(item, dict):
                # Remove top-level keys
                item.pop("meeting_title", None)
                item.pop("calendar_invitees_domains_type", None)

                # Filter calendar_invitees
                if "calendar_invitees" in item and isinstance(item["calendar_invitees"], list):
                    for invitee in item["calendar_invitees"]:
                        if isinstance(invitee, dict):
                            invitee.pop("email_domain", None)

                # Filter recorded_by
                if "recorded_by" in item and isinstance(item["recorded_by"], dict):
                    item["recorded_by"].pop("email_domain", None)

    return filtered


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.utcnow().isoformat() + "Z"

