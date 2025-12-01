from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError
from config import config

async def list_teams(
    ctx: Context,
    cursor: Optional[str] = None,
    per_page: Optional[int] = None
) -> dict:
    """Retrieve paginated list of teams in the organization.
    
    Returns team records that can be used for filtering meetings and team members.
    Team names from this endpoint can be used as values for the 'teams' parameter
    in list_meetings and 'team' parameter in list_team_members.
    
    Args:
        ctx: MCP context for logging
        cursor: Pagination cursor from previous response for next page
        per_page: Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)
    
    Returns:
        dict: {
            "items": [Team objects with name and metadata],
            "limit": int (default 20),
            "cursor": str (for pagination, null if no more results)
        }
    """
    try:
        await ctx.info("Fetching teams from Fathom API")
        
        # Use config default if per_page not provided
        effective_per_page = per_page if per_page is not None else config.default_per_page
        
        # Build parameters
        params = {}
        if cursor:
            params["cursor"] = cursor
        params["limit"] = effective_per_page
        
        result = await client.get_teams(params=params if params else None)
        await ctx.info("Successfully retrieved teams")

        return result
        
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching teams: {str(e)}")
        raise e