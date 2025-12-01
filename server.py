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
        "Access Fathom AI meeting recordings, transcripts, summaries, teams, and team members. "
        "Fathom automatically records, transcribes, and summarizes Zoom, Google Meet, and Microsoft Teams meetings. "
        "Use list_meetings to browse meetings with filtering by date, attendees, teams, or content inclusion. "
        "Use get_summary for AI-generated meeting summaries and get_transcript for timestamped speaker entries. "
        "Use list_teams and list_team_members for organizational data. "
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
    calendar_invitees: list[str] = Field(default=None, description="Filter by invitee emails"),
    calendar_invitees_domains: list[str] = Field(default=None, description="Filter by domains"),
    calendar_invitees_domains_type: str = Field(default=None, description="Domain filter type (all, only_internal, one_or_more_external)"),
    created_after: str = Field(default=None, description="ISO timestamp filter"),
    created_before: str = Field(default=None, description="ISO timestamp filter"),
    cursor: str = Field(default=None, description="Pagination cursor"),
    include_action_items: bool = Field(default=None, description="Include action items"),
    include_crm_matches: bool = Field(default=None, description="Include CRM matches"),
    include_summary: bool = Field(default=None, description="Include summary"),
    include_transcript: bool = Field(default=None, description="Include transcript"),
    per_page: int = Field(default=None, description="Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)"),
    recorded_by: list[str] = Field(default=None, description="Filter by recorder emails"),
    teams: list[str] = Field(default=None, description="Filter by team names")
) -> Dict[str, Any]:
    """Retrieve paginated meetings with filtering and optional content inclusion (transcripts, summaries, action items, CRM matches).
    
    Examples:
        list_meetings()  # Get all meetings (paginated)
        list_meetings(created_after="2024-01-01T00:00:00Z")  # Meetings after specific date
        list_meetings(include_summary=True, include_transcript=True)  # Include full content
        list_meetings(teams=["Sales", "Engineering"])  # Filter by specific teams
    """
    return await tools.meetings.list_meetings(
        ctx,
        calendar_invitees=calendar_invitees,
        calendar_invitees_domains=calendar_invitees_domains,
        calendar_invitees_domains_type=calendar_invitees_domains_type,
        created_after=created_after,
        created_before=created_before,
        cursor=cursor,
        include_action_items=include_action_items,
        include_crm_matches=include_crm_matches,
        include_summary=include_summary,
        include_transcript=include_transcript,
        per_page=per_page,
        recorded_by=recorded_by,
        teams=teams
    )

@mcp.tool
async def get_summary(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier")
) -> Dict[str, Any]:
    """Fetch AI-generated markdown summary for a recording.

    Example:
        get_summary_tool(recording_id=101470681)  # Get summary for specific recording
    """
    return await tools.recordings.get_summary(ctx, recording_id)

@mcp.tool
async def get_transcript(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier")
) -> Dict[str, Any]:
    """Retrieve timestamped speaker transcript for a recording.

    Example:
        get_transcript_tool(recording_id=101470681)  # Get transcript for specific recording
    """
    return await tools.recordings.get_transcript(ctx, recording_id)

@mcp.tool
async def list_teams(
    ctx: Context,
    cursor: str = Field(default=None, description="Pagination cursor"),
    per_page: int = Field(default=None, description="Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)")
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
    per_page: int = Field(default=None, description="Number of results per page (default: 20, configurable via DEFAULT_PER_PAGE env var)"),
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