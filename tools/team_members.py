from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError
from config import config

async def list_team_members(
    ctx: Context,
    cursor: Optional[str] = None,
    team: Optional[str] = None,
    per_page: Optional[int] = None
) -> dict:
    """Retrieve paginated list of team members with optional team filtering.
    
    Returns team member records that can be used to identify meeting participants
    and recording metadata.
    
    Args:
        ctx: MCP context for logging
        cursor: Pagination cursor from previous response for next page
        team: Filter members by specific team name (case-sensitive)
        per_page: Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)
    
    Returns:
        dict: {
            "items": [Team member objects with name, email, and team associations],
            "limit": int (default 20),
            "cursor": str (for pagination, null if no more results)
        }
    """
    try:
        await ctx.info("Fetching team members from Fathom API")
        
        # Use config default if per_page not provided
        effective_per_page = per_page if per_page is not None else config.default_per_page
        
        # Build parameters
        params = {}
        if cursor:
            params["cursor"] = cursor
        if team:
            params["team"] = team
        params["limit"] = effective_per_page
        
        result = await client.get_team_members(params=params if params else None)
        await ctx.info("Successfully retrieved team members")

        return result
        
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching team members: {str(e)}")
        raise e