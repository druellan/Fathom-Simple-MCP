from fastmcp import FastMCP, Context
from typing import Any, Dict
from pydantic import Field
from config import config
from fathom_client import client
from contextlib import asynccontextmanager
import json
from toon import encode as toon_encode
from utils import remove_null_and_empty

# Import tools
from tools.meetings import list_meetings
from tools.recordings import get_summary, get_transcript
from tools.teams import list_teams
from tools.team_members import list_team_members


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

    # Sanitize output by removing null and empty values
    sanitized_data = remove_null_and_empty(data)

    if config.output_format == "toon":
        try:
            return toon_encode(sanitized_data)
        except Exception:
            pass

    # Default to JSON
    return json.dumps(sanitized_data, indent=2, ensure_ascii=False)


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
    instructions="Use this tool to access Fathom meeting recordings, transcripts, summaries, teams, and team members. Focus on providing accurate and concise information based on the data available in Fathom.",
    lifespan=lifespan,
    on_duplicate_tools="warn",
    on_duplicate_resources="warn",
    on_duplicate_prompts="warn",
    tool_serializer=output_serializer,
)

@mcp.tool
async def list_meetings_tool(
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
    recorded_by: list[str] = Field(default=None, description="Filter by recorder emails"),
    teams: list[str] = Field(default=None, description="Filter by team names")
) -> Dict[str, Any]:
    """Retrieve a paginated list of meetings accessible to the API key. Supports filtering and optional inclusion of transcripts, summaries, action items, and CRM matches (where available)."""
    return await list_meetings(
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
        recorded_by=recorded_by,
        teams=teams
    )

@mcp.tool
async def get_summary_tool(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier"),
    destination_url: str = Field(default=None, description="Optional async callback URL")
) -> Dict[str, Any]:
    """Fetch the markdown summary for a specific recording. Supports synchronous return or asynchronous POST when destination_url is provided."""
    return await get_summary(ctx, recording_id, destination_url)

@mcp.tool
async def get_transcript_tool(
    ctx: Context,
    recording_id: int = Field(..., description="The recording identifier"),
    destination_url: str = Field(default=None, description="Optional async callback URL")
) -> Dict[str, Any]:
    """Retrieve the transcript for a recording as an array of timestamped speaker entries. Supports synchronous response or asynchronous POST to destination_url."""
    return await get_transcript(ctx, recording_id, destination_url)

@mcp.tool
async def list_teams_tool(
    ctx: Context,
    cursor: str = Field(default=None, description="Pagination cursor")
) -> Dict[str, Any]:
    """Return a paginated list of teams associated with the account."""
    return await list_teams(ctx, cursor)

@mcp.tool
async def list_team_members_tool(
    ctx: Context,
    cursor: str = Field(default=None, description="Pagination cursor"),
    team: str = Field(default=None, description="Filter by team name")
) -> Dict[str, Any]:
    """Return a paginated list of team members; supports optional filtering by team name."""
    return await list_team_members(ctx, cursor, team)

if __name__ == "__main__":
    mcp.run()


def main():
    """Entry point for the fathom-mcp command"""
    mcp.run()