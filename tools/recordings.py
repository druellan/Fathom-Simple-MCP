from fastmcp import Context
from typing import Optional
from fathom_client import client, FathomAPIError
import asyncio
import strip_markdown


async def get_meeting_details(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve comprehensive meeting details including summary and metadata (without transcript).

    Meeting metadata is best-effort. The Fathom REST API has no GET /recordings/{id}
    endpoint, so `client.get_meeting` falls back to scanning the first page of
    /meetings. The metadata lookup will miss for recordings older than that first
    page, and also for recordings the authenticated user did not personally record
    (those are not surfaced on /meetings under the user's API key). When the
    metadata lookup misses, the summary is still returned with empty metadata
    fields. Programming errors (non-FathomAPIError exceptions) on the metadata
    lookup are not swallowed — they propagate.

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording

    Returns:
        dict: Unified meeting object with metadata and summary (no transcript)
    """
    try:
        await ctx.info(f"Fetching meeting details for recording {recording_id}")

        # Fetch meeting metadata (best-effort) and summary concurrently.
        # The summary endpoint is direct (/recordings/{id}/summary) and works for
        # any recording_id; the meeting lookup may 404 for older recordings or
        # for recordings the user did not personally record.
        results = await asyncio.gather(
            client.get_meeting(recording_id),
            client.get_summary(recording_id),
            return_exceptions=True,
        )
        meeting_result, summary_result = results

        # Summary is the primary payload; fail if it errored.
        if isinstance(summary_result, Exception):
            raise summary_result
        summary = summary_result

        # Meeting metadata is optional. Only API errors are treated as "not
        # available"; other exception types are likely programming bugs and
        # should propagate.
        if isinstance(meeting_result, FathomAPIError):
            status = getattr(meeting_result, "status_code", "?")
            await ctx.info(
                f"Meeting metadata not available for {recording_id} "
                f"(FathomAPIError status={status}); "
                f"returning summary with empty metadata fields."
            )
            meeting = {}
        elif isinstance(meeting_result, Exception):
            raise meeting_result
        else:
            meeting = meeting_result

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
        return result

    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error fetching meeting details: {str(e)}")
        raise


async def get_meeting_transcript(
    ctx: Context,
    recording_id: int
) -> dict:
    """Retrieve meeting transcript with essential metadata.

    Meeting metadata is best-effort. The Fathom REST API has no GET /recordings/{id}
    endpoint, so `client.get_meeting` falls back to scanning the first page of
    /meetings. The metadata lookup will miss for recordings older than that first
    page, and also for recordings the authenticated user did not personally record
    (those are not surfaced on /meetings under the user's API key). When the
    metadata lookup misses, the transcript is still returned with empty metadata
    fields. Programming errors (non-FathomAPIError exceptions) on the metadata
    lookup are not swallowed — they propagate.

    Args:
        ctx: MCP context for logging
        recording_id: Numeric ID of the recording

    Returns:
        dict: Transcript with minimal metadata (id, title, participants, dates)
    """
    try:
        await ctx.info(f"Fetching transcript for recording {recording_id}")

        # Fetch meeting metadata (best-effort) and transcript concurrently.
        # The transcript endpoint is direct (/recordings/{id}/transcript) and works
        # for any recording_id; the meeting lookup may 404 for older recordings or
        # for recordings the user did not personally record.
        results = await asyncio.gather(
            client.get_meeting(recording_id),
            client.get_transcript(recording_id),
            return_exceptions=True,
        )
        meeting_result, transcript_result = results

        # Transcript is the primary payload; fail if it errored.
        if isinstance(transcript_result, Exception):
            raise transcript_result
        transcript = transcript_result

        # Meeting metadata is optional. Only API errors are treated as "not
        # available"; other exception types are likely programming bugs and
        # should propagate.
        if isinstance(meeting_result, FathomAPIError):
            status = getattr(meeting_result, "status_code", "?")
            await ctx.info(
                f"Meeting metadata not available for {recording_id} "
                f"(FathomAPIError status={status}); "
                f"returning transcript with empty metadata fields."
            )
            meeting = {}
        elif isinstance(meeting_result, Exception):
            raise meeting_result
        else:
            meeting = meeting_result

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
        return result

    except FathomAPIError as e:
        await ctx.error(f"Fathom API error: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error fetching meeting transcript: {str(e)}")
        raise