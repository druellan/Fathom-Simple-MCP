from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError

async def list_teams(
    ctx: Context,
    cursor: Optional[str] = None
) -> dict:
    """Retrieve paginated list of teams in the organization.
    
    Returns team records that can be used for filtering meetings and team members.
    Team names from this endpoint can be used as values for the 'teams' parameter
    in list_meetings and 'team' parameter in list_team_members.
    
    Args:
        ctx: MCP context for logging
        cursor: Pagination cursor from previous response for next page
    
    Returns:
        dict: {
            "items": [Team objects with name and metadata],
            "limit": int (default 10),
            "cursor": str (for pagination, null if no more results)
        }
    """
    try:
        await ctx.info("Fetching teams from Fathom API")
        
        # Build parameters
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        result = await client.get_teams(params=params if params else None)
        await ctx.info("Successfully retrieved teams")

        return result
        
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching teams: {str(e)}")
        raise e