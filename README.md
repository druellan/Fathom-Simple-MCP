# Fathom MCP Server

A Model Context Protocol (MCP) server for accessing Fathom AI API endpoints (meetings, recordings, transcripts, summaries, teams, team members) via GET operations. Built with [FastMCP](https://gofastmcp.com/).

This implementation provides streamlined access to Fathom meeting data while minimizing API consumption. It is optimized for efficiency and simplicity, using the toon output format for less token usage and better LLM processing.

## Features

- **List Meetings**: Retrieve meetings with optional filtering and inclusion of transcripts/summaries
- **Get Summary**: Retrieve markdown summary for a specific recording
- **Get Transcript**: Retrieve transcript for a specific recording
- **List Teams**: Retrieve all teams
- **List Team Members**: Retrieve team members with optional team filtering

## Requirements

- Python 3.10+
- Fathom API key
- FastMCP 2.0+

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
      "run",
      "server.py"
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
- `calendar_invitees_domains_type` (str, optional): Domain filter type (all, only_internal, one_or_more_external)
- `created_after` (str, optional): ISO timestamp filter
- `created_before` (str, optional): ISO timestamp filter
- `cursor` (str, optional): Pagination cursor
- `include_action_items` (bool, optional): Include action items
- `include_crm_matches` (bool, optional): Include CRM matches
- `include_summary` (bool, optional): Include summary
- `include_transcript` (bool, optional): Include transcript
- `recorded_by` (list[str], optional): Filter by recorder emails
- `teams` (list[str], optional): Filter by team names

### `get_summary`
Retrieve markdown summary for a recording.

**Properties:**
- `recording_id` (int): The recording identifier
- `destination_url` (str, optional): Async callback URL

### `get_transcript`
Retrieve transcript for a recording.

**Properties:**
- `recording_id` (int): The recording identifier
- `destination_url` (str, optional): Async callback URL

### `list_teams`
Retrieve teams with optional pagination.

**Properties:**
- `cursor` (str, optional): Pagination cursor

### `list_team_members`
Retrieve team members with optional filtering and pagination.

**Properties:**
- `cursor` (str, optional): Pagination cursor
- `team` (str, optional): Filter by team name

## Output Format

All tools return data in filtered JSON format for improved readability and LLM processing.
The output is filtered to remove empty, null or redundant information.

Example JSON output for meetings:
```json
{
  "items": [
    {
      "title": "Quarterly Business Review",
      "recording_id": 123456789,
      "created_at": "2025-03-01T17:01:30Z"
    }
  ]
}
```

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