from fastmcp import Context
from typing import List, Optional
from fathom_client import client, FathomAPIError
from config import config


def _build_meetings_params(
    calendar_invitees: Optional[List[str]] = None,
    calendar_invitees_domains: Optional[List[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    cursor: Optional[str] = None,
    include_action_items: Optional[bool] = None,
    include_crm_matches: Optional[bool] = None,
    include_summary: Optional[bool] = None,
    recorded_by: Optional[List[str]] = None,
    teams: Optional[List[str]] = None,
    per_page: Optional[int] = None
) -> dict:
    """Build API parameters dict from function arguments"""
    params = {}
    
    if calendar_invitees:
        params["calendar_invitees[]"] = calendar_invitees
    if calendar_invitees_domains:
        params["calendar_invitees_domains[]"] = calendar_invitees_domains
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if cursor:
        params["cursor"] = cursor
    if include_action_items is not None:
        params["include_action_items"] = include_action_items
    if include_crm_matches is not None:
        params["include_crm_matches"] = include_crm_matches
    if include_summary is not None:
        params["include_summary"] = include_summary
    if recorded_by:
        params["recorded_by[]"] = recorded_by
    if teams:
        params["teams[]"] = teams
    if per_page is not None:
        params["limit"] = per_page
    
    return params

async def list_meetings(
    ctx: Context,
    calendar_invitees: Optional[List[str]] = None,
    calendar_invitees_domains: Optional[List[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    cursor: Optional[str] = None,
    include_action_items: Optional[bool] = None,
    include_crm_matches: Optional[bool] = None,
    include_summary: Optional[bool] = None,
    recorded_by: Optional[List[str]] = None,
    teams: Optional[List[str]] = None,
    per_page: Optional[int] = None
) -> dict:
    """Retrieve paginated list of meetings with optional filtering and content inclusion.
    
    Returns meeting records with metadata, optionally including transcripts, summaries,
    action items, and CRM matches. Use recording_id from results to fetch individual
    recording content.
    
    Args:
        ctx: MCP context for logging
        calendar_invitees: List of email addresses to filter meetings by attendees
        calendar_invitees_domains: List of domains to filter meetings by attendee domains
        created_after: ISO 8601 timestamp (e.g., "2024-01-01T00:00:00Z") - meetings created after this time
        created_before: ISO 8601 timestamp (e.g., "2024-12-31T23:59:59Z") - meetings created before this time
        cursor: Pagination cursor from previous response for next page
        include_action_items: Set True to include action items in response
        include_crm_matches: Set True to include CRM match data in response
        include_summary: Set True to include meeting summaries in response
        recorded_by: List of email addresses to filter by meeting recorder
        teams: List of team names to filter meetings by associated teams
        per_page: Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)
    
    Returns:
        dict: {
            "items": [Meeting objects with fields like title, url, created_at, recording_id, etc.],
            "limit": int (default 20),
            "cursor": str (for pagination, null if no more results)
        }
    """
    try:
        await ctx.info("Fetching meetings from Fathom API")

        # Use config default if per_page not provided
        effective_per_page = per_page if per_page is not None else config.default_per_page

        # Build parameters
        params = _build_meetings_params(
            calendar_invitees=calendar_invitees,
            calendar_invitees_domains=calendar_invitees_domains,
            created_after=created_after,
            created_before=created_before,
            cursor=cursor,
            include_action_items=include_action_items,
            include_crm_matches=include_crm_matches,
            include_summary=include_summary,
            recorded_by=recorded_by,
            teams=teams,
            per_page=effective_per_page
        )

        result = await client.get_meetings(params=params if params else None)
        await ctx.info("Successfully retrieved meetings")

        return result

    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching meetings: {str(e)}")
        raise e