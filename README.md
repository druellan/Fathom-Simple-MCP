# Fathom MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![](https://badge.mcpx.dev?type=server&features=tools 'MCP server with features')

A Model Context Protocol (MCP) server for accessing Fathom.video meeting recordings, transcripts, summaries, teams, and team members.

This implementation provides streamlined access to Fathom meeting data while minimizing API consumption. It is optimized for efficiency and simplicity, using the **Toon** output format for less token usage and better LLM processing.

## Features

- **List Meetings**: Retrieve meetings with optional filtering and inclusion of summaries
- **Get Meeting Details**: Retrieve comprehensive meeting data including AI-generated summaries and transcripts
- **Search Meetings**: Search meetings by keyword across titles, attendees, teams, topics, and summaries
- **List Teams**: Retrieve all teams
- **List Team Members**: Retrieve team members with optional team filtering

## Requirements

- Python 3.10+
- Fathom API key

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
or
```bash
uv venv && uv sync
```

## Configuration

The server uses environment variables for configuration:

- `FATHOM_API_KEY`: Your Fathom API key (required)
- `FATHOM_TIMEOUT`: Request timeout in seconds (default: 30)
- `OUTPUT_FORMAT`: Output format for tool responses ("toon" or "json", default: "toon")
- `DEFAULT_PER_PAGE`: Number of results per page (default: 50)

## Usage

### Direct Python Execution (Recommended)
```json
{
  "fathom": {
    "command": "python",
    "args": [
      "server.py"
    ],
    "env": {
      "FATHOM_API_KEY": "<api-key>"
    }
  }
}
```

### Using UV
```json
{
  "fathom": {
    "command": "uv",
    "args": [
      "--directory",
      "/mcp_path/fathom-mcp",
      "run",
      "fathom-mcp"
    ],
    "env": {
      "FATHOM_API_KEY": "<api-key>"
    }
  }
}
```

## Available Tools

### `list_meetings`
Retrieve meetings with optional filtering and pagination.

**Properties:**
- `calendar_invitees` (list[str], optional): Filter by invitee emails
- `calendar_invitees_domains` (list[str], optional): Filter by domains
- `created_after` (str, optional): ISO timestamp filter
- `created_before` (str, optional): ISO timestamp filter
- `cursor` (str, optional): Pagination cursor
- `include_action_items` (bool, optional): Include action items
- `include_crm_matches` (bool, optional): Include CRM matches
- `per_page` (int, optional): Number of results per page (default: 50, configurable via DEFAULT_PER_PAGE env var)
- `recorded_by` (list[str], optional): Filter by recorder emails
- `teams` (list[str], optional): Filter by team names

### `search_meetings`
Search meetings by keyword across titles, participants, teams, topics, summaries, and optionally transcripts.

**Properties:**
- `query` (str, required): Search query to match against meeting metadata and optionally transcript content
- `include_transcript` (bool, optional): If True, search within transcripts and include them in results (default: False). Warning: This is slower and more resource-intensive.

**Returns:**
A search results object containing:
- `items`: List of matching meetings with full meeting details (and transcripts if requested)
- `query`: The search query used
- `total_matches`: Number of meetings that matched the search
- `searched_transcripts`: Boolean indicating whether transcripts were searched

**Examples:**
- `search_meetings("McDonalds")` - Search metadata only (fast)
- `search_meetings("budget discussion", include_transcript=True)` - Search including full transcripts (slower)
- `search_meetings("engineering")` - Find meetings related to engineering topics

### `get_meeting_details`
Retrieve comprehensive meeting details including summary and metadata (without transcript).

**Properties:**
- `recording_id` (int): The recording identifier

**Returns:**
A unified meeting object containing:
- `recording_id`: Unique identifier for the recording
- `title`: Meeting title
- `meeting_url`: URL to the meeting recording
- `share_url`: Shareable URL for the meeting
- `created_at`: When the meeting was created
- `scheduled_start_time`: Original scheduled start time
- `scheduled_end_time`: Original scheduled end time
- `recording_start_time`: When recording actually started
- `recording_end_time`: When recording actually ended
- `transcript_language`: Language of the transcript
- `participants`: List of meeting participants with names, emails, and external/internal status
- `recorded_by`: Information about who recorded the meeting (name, email, team)
- `teams`: Teams associated with the meeting
- `topics`: AI-detected topics discussed
- `sentiment`: Overall sentiment analysis
- `crm_matches`: CRM contact matches
- `summary`: AI-generated meeting summary (converted to plain text from markdown)

### `get_meeting_transcript`
Retrieve meeting transcript with essential metadata (id, title, participants, dates).

**Properties:**
- `recording_id` (int): The recording identifier

**Returns:**
A transcript object containing:
- `recording_id`: Unique identifier for the recording
- `title`: Meeting title
- `participants`: List of meeting participants
- `created_at`: When the meeting was created
- `scheduled_start_time`: Original scheduled start time
- `scheduled_end_time`: Original scheduled end time
- `transcript`: Full meeting transcript with timestamps

### `list_teams`
Retrieve teams with optional pagination.

**Properties:**
- `cursor` (str, optional): Pagination cursor
- `per_page` (int, optional): Number of results per page (default: 50, configurable via DEFAULT_PER_PAGE env var)

### `list_team_members`
Retrieve team members with optional filtering and pagination.

**Properties:**
- `cursor` (str, optional): Pagination cursor
- `per_page` (int, optional): Number of results per page (default: 50, configurable via DEFAULT_PER_PAGE env var)
- `team` (str, optional): Filter by team name

## MCP Configuration Examples

### Claude Code

```json
{
  "mcpServers": {
    "fathom": {
      "command": "python",
      "args": ["path/to/fathom-mcp/server.py"],
      "env": {
        "FATHOM_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### GitHub Copilot (VS Code)

```json
{
  "servers": {
    "fathom": {
      "command": "python",
      "args": ["path/to/fathom-mcp/server.py"],
      "env": {
        "FATHOM_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Roo Code

```json
{
  "mcp": {
    "servers": {
      "fathom": {
        "command": "uv",
        "args": [
          "--directory",
          "/mcp_path/fathom-mcp",
          "run",
          "fathom-mcp"
        ],
        "env": {
          "FATHOM_API_KEY": "your-api-key-here"
        }
      }
    }
  }
}
```

## Output Format

The server supports two output formats configured via the `OUTPUT_FORMAT` environment variable:
- **TOON** (default): Token-Optimized Object Notation - optimized for LLM processing with reduced token usage
- **JSON**: Standard JSON format with indentation for human readability

All output is filtered to remove empty, null, or redundant information for improved efficiency.

## Error Handling

The server provides comprehensive error handling:

- **401 Unauthorized**: Invalid API key
- **404 Not Found**: Resource not found
- **429 Rate Limited**: Too many requests
- **500 Server Error**: Fathom API issues

All errors are logged via MCP context with appropriate severity levels.

## Security

- API keys are loaded from environment variables
- No sensitive data is logged
- HTTPS is used for all API requests
- Error messages don't expose internal details

## License

MIT License.
