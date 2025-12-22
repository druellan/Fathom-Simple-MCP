"""Fathom API client for MCP server"""
__version__ = "0.1.0"

import httpx
from typing import Dict, Any, Optional
from config import config
import asyncio

class FathomAPIError(Exception):
    """Custom exception for Fathom API errors"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class FathomClient:
    """Async HTTP client for Fathom API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers=config.headers
        )

    async def _request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Fathom API"""
        url = f"{config.base_url}{endpoint}"
        
        try:
            response = await self.client.request(method, url, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                # Extract rate limit information
                limit = response.headers.get("RateLimit-Limit", "unknown")
                remaining = response.headers.get("RateLimit-Remaining", "unknown")
                reset = response.headers.get("RateLimit-Reset", "unknown")
                
                raise FathomAPIError(
                    f"Rate limit exceeded. Limit: {limit}, Remaining: {remaining}, Reset: {reset}",
                    429
                )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise FathomAPIError("Unauthorized: Invalid API key", 401)
            elif response.status_code == 404:
                raise FathomAPIError("Resource not found", 404)
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "Unknown error")
                    raise FathomAPIError(f"HTTP {response.status_code}: {error_message}", response.status_code)
                except Exception:
                    raise FathomAPIError(
                        f"HTTP {response.status_code}: {response.text}",
                        response.status_code
                    )
                    
        except httpx.RequestError as e:
            raise FathomAPIError(f"Request failed: {str(e)}")

    async def get_meetings(self, params: Optional[dict] = None) -> Dict[str, Any]:
        """Get meetings with optional parameters"""
        return await self._request("GET", "/meetings", params=params)

    async def get_meeting(self, recording_id: int) -> Dict[str, Any]:
        """Get a single meeting by recording ID - fetches from meetings list and filters"""
        # Get meetings list and filter by recording_id
        meetings_data = await self.get_meetings()
        
        # Search for the specific meeting by recording_id
        for meeting in meetings_data.get("items", []):
            if meeting.get("recording_id") == recording_id:
                return meeting
        
        # If not found, raise appropriate error
        raise FathomAPIError(f"Meeting with recording_id {recording_id} not found", 404)

    async def get_summary(self, recording_id: int, destination_url: Optional[str] = None) -> Dict[str, Any]:
        """Get summary for a recording"""
        params = {}
        if destination_url:
            params["destination_url"] = destination_url
        return await self._request("GET", f"/recordings/{recording_id}/summary", params=params)

    async def get_transcript(self, recording_id: int, destination_url: Optional[str] = None) -> Dict[str, Any]:
        """Get transcript for a recording"""
        params = {}
        if destination_url:
            params["destination_url"] = destination_url
        return await self._request("GET", f"/recordings/{recording_id}/transcript", params=params)

    async def get_teams(self, params: Optional[dict] = None) -> Dict[str, Any]:
        """Get teams with optional parameters"""
        return await self._request("GET", "/teams", params=params)

    async def get_team_members(self, params: Optional[dict] = None) -> Dict[str, Any]:
        """Get team members with optional parameters"""
        return await self._request("GET", "/team_members", params=params)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Global client instance
client = FathomClient()