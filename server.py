from fastmcp import FastMCP, Context
from typing import Any, Dict
from pydantic import Field
from config import config
from fathom_client import client
from contextlib import asynccontextmanager
import json
from toon import encode as toon_encode
from utils import filter_response

# Import tools
import tools.meetings
import tools.recordings
import tools.teams
import tools.team_members
import tools.search


def output_serializer(data: Any) -> str:
    """Serialize tool output based on OUTPUT_FORMAT configuration.

    Args:
        data: The data to serialize

    Returns:
        Sanitized and formatted output as a the configured format (TOON or JSON)
    """
    if isinstance(data, str):
        # Don't serialize strings that are already formatted
        return data

    # Filter sensitive keys and sanitize output by removing null and empty values
    filtered_data = filter_response(data)

    if config.output_format == "toon":
        try:
            return toon_encode(filtered_data)
        except Exception:
            pass

    # Default to JSON
    return json.dumps(filtered_data, indent=2, ensure_ascii=False)


@asynccontextmanager
async def lifespan(server):
    """Server lifespan context manager"""
    # Startup
    if not config.validate():
        raise ValueError("Invalid configuration: FATHOM_API_KEY is required")
    
    yield
    
    # Shutdown
    await client.close()

mcp = FastMCP(
    name="Fathom MCP Server",
    instructions=(
        "Access Fathom.video meeting recordings, transcripts, summaries, teams, and team members."
        "Fathom.video automatically records, transcribes, and summarizes meetings."
        "Use search_meetings to find meetings by keywords in titles, summaries, participants, teams, and topics."
        "Use list_meetings to browse meetings with filtering by date, attendees, teams, and domains."
        "Use get_meeting_details for comprehensive meeting data including summaries."
        "Use list_teams and list_team_members for organizational data."
        "All endpoints support pagination and efficient data retrieval optimized for LLM processing."
    ),
    lifespan=lifespan,
    on_duplicate_tools="warn",
    on_duplicate_resources="warn",
    on_duplicate_prompts="warn",
    tool_serializer=output_serializer,
)

@mcp.tool
async def list_meetings(
    ctx: Context,
    calendar_invitees: list[str] = Field(
        default=None, description="Filter by invitee emails"
    ),
    calendar_invitees_domains: list[str] = Field(
        default=None, description="Filter by domains"
    ),
    created_after: str = Field(default=None, description="ISO timestamp filter"),
    created_before: str = Field(default=None, description="ISO timestamp filter"),
    cursor: str = Field(default=None, description="Pagination cursor"),
    include_action_items: bool = Field(
        default=None, description="Include action items"
    ),
    include_crm_matches: bool = Field(default=None, description="Include CRM matches"),
    per_page: int = Field(
        default=config.default_per_page,
        description=f"Number of results per page (default: {config.default_per_page})",
    ),
    recorded_by: list[str] = Field(
        default=None, description="Filter by recorder emails"
    ),
    teams: list[str] = Field(default=None, description="Filter by team names"),
) -> Dict[str, Any]:
    """Retrieve paginated meetings with filtering and optional content inclusion (action items, CRM matches).
    
    Examples:
        list_meetings()  # Get all meetings (paginated)
        list_meetings(created_after="2024-01-01T00:00:00Z")  # Meetings after specific date
        list_meetings(teams=["Sales", "Engineering"])  # Filter by specific teams
        list_meetings(calendar_invitees=["john.doe@company.com", "jane.smith@client.com"])  # Filter by specific attendees
        list_meetings(calendar_invitees_domains=["company.com", "client.com"])  # Filter by attendee domains
    """
    return await tools.meetings.list_meetings(
        ctx,
        calendar_invitees=calendar_invitees,
        calendar_invitees_domains=calendar_invitees_domains,
        created_after=created_after,
        created_before=created_before,
        cursor=cursor,
        include_action_items=include_action_items,
        include_crm_matches=include_crm_matches,
        per_page=per_page,
        recorded_by=recorded_by,
        teams=teams
    )


@mcp.tool
async def search_meetings(
    ctx: Context,
    query: str = Field(..., description="Search query to match against meeting metadata (titles, participants, teams)")
) -> Dict[str, Any]:
    """Search meetings by keyword across metadata fields (titles, participants, teams, topics).

    This tool searches meeting metadata only - not full transcript content. Uses fuzzy matching
    to handle partial matches, plurals, and case-insensitive search. For example, "McDonalds"
    will match meeting titles, attendee names/emails, team names, and discussion topics.

    Results include AI-generated summaries and CRM matches by default.

    Fetches all meetings (with pagination) and returns those matching the search query.

    Examples:
        search_meetings(\"McDonalds\")  # Find meetings with 'McDonalds' in title, participants, or teams
        search_meetings(\"acme\")  # Matches \"Acme Labs\", \"acme.com\" attendees, etc.
        search_meetings(\"lab\")  # Matches \"Labs\", \"Laboratory\", plural handling included
    """
    return await tools.search.search_meetings(ctx, query)


@mcp.tool
async def get_meeting_details(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier")
) -> Dict[str, Any]:
    """Retrieve comprehensive meeting details including summary and metadata (without transcript).

    Example:
        get_meeting_details([recording_id])
    """
    return await tools.recordings.get_meeting_details(ctx, recording_id)


@mcp.tool
async def get_meeting_transcript(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier")
) -> Dict[str, Any]:
    """Retrieve meeting transcript with essential metadata (id, title, participants, dates).

    Example:
        get_meeting_transcript([recording_id])
    """
    return await tools.recordings.get_meeting_transcript(ctx, recording_id)

@mcp.tool
async def list_teams(
    ctx: Context,
    cursor: str = Field(default=None, description="Pagination cursor"),
    per_page: int = Field(default=None, description=f"Number of results per page (default: {config.default_per_page})")
) -> Dict[str, Any]:
    """Retrieve paginated list of teams with organizational structure.
    
    Examples:
        list_teams_tool()  # Get first page of teams
        list_teams_tool(cursor="abc123")  # Get next page using cursor
    """
    return await tools.teams.list_teams(ctx, cursor, per_page)

@mcp.tool
async def list_team_members(
    ctx: Context,
    cursor: str = Field(default=None, description="Pagination cursor"),
    per_page: int = Field(default=None, description=f"Number of results per page (default: {config.default_per_page})"),
    team: str = Field(default=None, description="Filter by team name")
) -> Dict[str, Any]:
    """Retrieve paginated team members with optional team filtering.
    
    Examples:
        list_team_members_tool()  # Get all team members across all teams
        list_team_members_tool(team="Engineering")  # Filter members by team name
        list_team_members_tool(cursor="def456")  # Paginate through member list
    """
    return await tools.team_members.list_team_members(ctx, cursor, team, per_page)

if __name__ == "__main__":
    mcp.run()


def main():
    """Entry point for the fathom-mcp command"""
    mcp.run()