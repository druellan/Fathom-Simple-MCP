from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError

async def get_summary(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve AI-generated markdown summary for a specific meeting recording.

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording (from meeting.recording_id)

    Returns:
        dict: {
            "summary": {
                "markdown_formatted": "Full markdown summary text"
            }
        }
    """
    try:
        await ctx.info(f"Fetching summary for recording {recording_id}")
        result = await client.get_summary(recording_id)
        await ctx.info("Successfully retrieved summary")
        return result
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching summary: {str(e)}")
        raise e

async def get_transcript(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve timestamped transcript entries for a specific meeting recording.

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording (from meeting.recording_id)

    Returns:
        dict: {
            "transcript": [
                {
                    "speaker": "Speaker name",
                    "timestamp": "00:01:23",
                    "text": "Spoken content..."
                }
            ]
        }
    """
    try:
        await ctx.info(f"Fetching transcript for recording {recording_id}")
        result = await client.get_transcript(recording_id)
        await ctx.info("Successfully retrieved transcript")
        return result
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching transcript: {str(e)}")
        raise e