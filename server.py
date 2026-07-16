import json

from fastmcp import FastMCP, Context
from fastmcp.server.middleware import Middleware, MiddlewareContext
from typing import Any, Dict, Annotated
from pydantic import Field
from config import config
from fathom_client import client
from contextlib import asynccontextmanager
from toon import encode as toon_encode

# Import tools
import tools.meetings
import tools.recordings
import tools.teams
import tools.team_members
import tools.search


@asynccontextmanager
async def lifespan(server):
    """Server lifespan context manager"""
    try:
        config.validate()
    except ValueError as e:
        raise ValueError(f"Configuration error: {str(e)}")

    yield

    await client.close()


class OutputSerializationMiddleware(Middleware):
    """Serialize tool output based on OUTPUT_FORMAT configuration.

    Intercepts tool results and serializes them to TOON or JSON format.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)

        if result and hasattr(result, "content"):
            for item in result.content:
                if hasattr(item, "text"):
                    text = item.text
                    if text and isinstance(text, str):
                        try:
                            parsed = json.loads(text)
                            if config.output_format in ("toon", "hybrid"):
                                try:
                                    item.text = toon_encode(parsed)
                                    if config.output_format == "toon":
                                        result.structured_content = {"toon": item.text}
                                except Exception:
                                    pass
                        except (json.JSONDecodeError, TypeError, ValueError):
                            pass

        return result


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
    version="0.1.0",
    lifespan=lifespan,
    on_duplicate="warn",
)

mcp.add_middleware(OutputSerializationMiddleware())


# --- Tools ---

@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def search_meetings(
    ctx: Context,
    query: Annotated[
        str,
        Field(
            description="Search query to match against meeting metadata (titles, participants, teams, topics, summaries, and optionally transcripts)"
        ),
    ],
    include_transcript: Annotated[
        bool,
        Field(
            description="If True, search within transcripts and include them in results."
        ),
    ] = False,
) -> Dict[str, Any]:
    """Search meetings by keyword across metadata fields and optionally transcripts.

    This tool searches meeting metadata (titles, attendees, teams, topics, summaries) and optionally
    full transcript content. Uses fuzzy matching to handle partial matches, plurals, and case-insensitive search.

    By default, transcripts are NOT searched or included to optimize performance. Set include_transcript=True
    to search within and return transcript data.

    Fetches all meetings (with pagination) and returns those matching the search query.

    Examples:
        search_meetings("McDonalds")  # Search metadata only
        search_meetings("budget discussion", include_transcript=True)  # Search including transcripts
        search_meetings("engineering")  # Find meetings related to engineering
    """
    return await tools.search.search_meetings(ctx, query, include_transcript)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def list_meetings(
    ctx: Context,
    calendar_invitees: Annotated[
        list[str], Field(description="Filter by invitee emails")
    ] = None,
    calendar_invitees_domains: Annotated[
        list[str], Field(description="Filter by domains")
    ] = None,
    created_after: Annotated[
        str, Field(description="ISO timestamp filter")
    ] = None,
    created_before: Annotated[
        str, Field(description="ISO timestamp filter")
    ] = None,
    cursor: Annotated[
        str, Field(description="Pagination cursor")
    ] = None,
    include_action_items: Annotated[
        bool, Field(description="Include action items")
    ] = None,
    include_crm_matches: Annotated[
        bool, Field(description="Include CRM matches")
    ] = None,
    per_page: Annotated[
        int,
        Field(description=f"Number of results per page (default: {config.default_per_page})"),
    ] = config.default_per_page,
    recorded_by: Annotated[
        list[str], Field(description="Filter by recorder emails")
    ] = None,
    teams: Annotated[
        list[str], Field(description="Filter by team names")
    ] = None,
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


@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def get_meeting_details(
    ctx: Context,
    recording_id: Annotated[int, Field(description="The recording identifier")],
) -> Dict[str, Any]:
    """Retrieve comprehensive meeting details including summary and metadata (without transcript).

    Example:
        get_meeting_details([recording_id])
    """
    return await tools.recordings.get_meeting_details(ctx, recording_id)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def get_meeting_transcript(
    ctx: Context,
    recording_id: Annotated[int, Field(description="The recording identifier")],
) -> Dict[str, Any]:
    """Retrieve meeting transcript with essential metadata (id, title, participants, dates).

    Example:
        get_meeting_transcript([recording_id])
    """
    return await tools.recordings.get_meeting_transcript(ctx, recording_id)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def list_teams(
    ctx: Context,
    cursor: Annotated[
        str, Field(description="Pagination cursor")
    ] = None,
    per_page: Annotated[
        int, Field(description=f"Number of results per page (default: {config.default_per_page})")
    ] = None,
) -> Dict[str, Any]:
    """Retrieve paginated list of teams with organizational structure.

    Examples:
        list_teams_tool()  # Get first page of teams
        list_teams_tool(cursor="abc123")  # Get next page using cursor
    """
    return await tools.teams.list_teams(ctx, cursor, per_page)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
    },
)
async def list_team_members(
    ctx: Context,
    cursor: Annotated[
        str, Field(description="Pagination cursor")
    ] = None,
    per_page: Annotated[
        int, Field(description=f"Number of results per page (default: {config.default_per_page})")
    ] = None,
    team: Annotated[
        str, Field(description="Filter by team name")
    ] = None,
) -> Dict[str, Any]:
    """Retrieve paginated team members with optional team filtering.

    Examples:
        list_team_members_tool()  # Get all team members across all teams
        list_team_members_tool(team="Engineering")  # Filter members by team name
        list_team_members_tool(cursor="def456")  # Paginate through member list
    """
    return await tools.team_members.list_team_members(ctx, cursor, team, per_page)


def main():
    """Entry point for the fathom-mcp command"""
    mcp.run()


if __name__ == "__main__":
    main()