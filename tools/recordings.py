from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError
from utils import filter_response
import asyncio
import strip_markdown


async def get_meeting_details(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve comprehensive meeting details including summary and metadata (without transcript).

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording

    Returns:
        dict: Unified meeting object with metadata and summary (no transcript)
    """
    try:
        await ctx.info(f"Fetching meeting details for recording {recording_id}")

        # Fetch meeting metadata and summary concurrently
        meeting_task = client.get_meeting(recording_id)
        summary_task = client.get_summary(recording_id)

        meeting, summary = await asyncio.gather(
            meeting_task, summary_task, return_exceptions=True
        )

        # If summary (primary payload) failed, propagate the error
        if isinstance(summary, Exception):
            raise summary

        # Meeting metadata is best-effort: older recordings or those
        # recorded by others may not appear on the first page of /meetings.
        if isinstance(meeting, FathomAPIError):
            await ctx.info(
                f"Meeting metadata unavailable for recording {recording_id} "
                f"({type(meeting).__name__} status={meeting.status_code}); "
                f"returning summary without full metadata"
            )
            meeting = {}
        elif isinstance(meeting, Exception):
            raise meeting

        # Convert markdown summary to plain text
        markdown_summary = summary.get("summary", {}).get("markdown_formatted", "")
        plain_text_summary = strip_markdown.strip_markdown(markdown_summary) if markdown_summary else ""

        # Build unified meeting object without transcript
        result = {
            "recording_id": recording_id,
            "title": meeting.get("title"),
            "meeting_url": meeting.get("url"),
            "share_url": meeting.get("share_url"),
            "created_at": meeting.get("created_at"),
            "scheduled_start_time": meeting.get("scheduled_start_time"),
            "scheduled_end_time": meeting.get("scheduled_end_time"),
            "recording_start_time": meeting.get("recording_start_time"),
            "recording_end_time": meeting.get("recording_end_time"),
            "transcript_language": meeting.get("transcript_language"),
            "participants": meeting.get("participants", []),
            "recorded_by": meeting.get("recorded_by"),
            "teams": meeting.get("teams", []),
            "topics": meeting.get("topics", []),
            "sentiment": meeting.get("sentiment"),
            "crm_matches": meeting.get("crm_matches", []),
            "summary": plain_text_summary
        }

        await ctx.info("Successfully retrieved meeting details")
        return filter_response(result)

    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching meeting details: {str(e)}")
        raise e


async def get_meeting_transcript(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve meeting transcript with essential metadata.

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording

    Returns:
        dict: Transcript with minimal metadata (id, title, participants, dates)
    """
    try:
        await ctx.info(f"Fetching transcript for recording {recording_id}")

        # Fetch meeting metadata and transcript concurrently
        meeting_task = client.get_meeting(recording_id)
        transcript_task = client.get_transcript(recording_id)

        meeting, transcript = await asyncio.gather(
            meeting_task, transcript_task, return_exceptions=True
        )

        # If transcript (primary payload) failed, propagate the error
        if isinstance(transcript, Exception):
            raise transcript

        # Meeting metadata is best-effort: older recordings or those
        # recorded by others may not appear on the first page of /meetings.
        if isinstance(meeting, FathomAPIError):
            await ctx.info(
                f"Meeting metadata unavailable for recording {recording_id} "
                f"({type(meeting).__name__} status={meeting.status_code}); "
                f"returning transcript without full metadata"
            )
            meeting = {}
        elif isinstance(meeting, Exception):
            raise meeting
        
        # Build transcript object with essential metadata
        result = {
            "recording_id": recording_id,
            "title": meeting.get("title"),
            "participants": meeting.get("participants", []),
            "created_at": meeting.get("created_at"),
            "scheduled_start_time": meeting.get("scheduled_start_time"),
            "scheduled_end_time": meeting.get("scheduled_end_time"),
            "transcript": transcript.get("transcript", [])
        }

        await ctx.info("Successfully retrieved meeting transcript")
        return filter_response(result)

    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error fetching meeting transcript: {str(e)}")
        raise e