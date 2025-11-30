from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError

async def list_team_members(
    ctx: Context,
    cursor: Optional[str] = None,
    team: Optional[str] = None
) -> dict:
    """Retrieve paginated list of team members with optional team filtering.
    
    Returns team member records that can be used to identify meeting participants
    and recording metadata.
    
    Args:
        ctx: MCP context for logging
        cursor: Pagination cursor from previous response for next page
        team: Filter members by specific team name (case-sensitive)
    
    Returns:
        dict: {
            "items": [Team member objects with name, email, and team associations],
            "limit": int (default 10),
            "cursor": str (for pagination, null if no more results)
        }
    """
    try:
        await ctx.info("Fetching team members from Fathom API")
        
        # Build parameters
        params = {}
        if cursor:
            params["cursor"] = cursor
        if team:
            params["team"] = team
        
        result = await client.get_team_members(params=params if params else None)
        await ctx.info("Successfully retrieved team members")

        return result
        
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching team members: {str(e)}")
        raise e