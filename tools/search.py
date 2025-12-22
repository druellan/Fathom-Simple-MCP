from fastmcp import Context
from fathom_client import client, FathomAPIError
from typing import Optional


def _normalize_search(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, remove spaces/hyphens, strip trailing 's'."""
    normalized = text.lower().replace(" ", "").replace("-", "").replace("_", "")
    # Strip trailing 's' to handle simple plurals (labs -> lab, meetings -> meeting)
    if normalized.endswith("s") and len(normalized) > 2:
        normalized = normalized[:-1]
    return normalized


def _filter_meeting_fields(meeting: dict, found_in_transcript: bool = False) -> dict:
    """Filter and structure meeting fields for search results.
    
    Args:
        meeting: The meeting object from the API
        found_in_transcript: Whether the search match was found in the transcript
    
    Returns:
        dict: Filtered meeting fields with summary and optional found_in_transcript flag
    """
    summary = meeting.get("default_summary")
    summary_text = None
    if isinstance(summary, dict):
        summary_text = summary.get("markdown_formatted")
    elif isinstance(summary, str):
        summary_text = summary
    
    result = {
        "title": meeting.get("title"),
        "recording_id": meeting.get("recording_id"),
        "url": meeting.get("url"),
        "share_url": meeting.get("share_url"),
        "created_at": meeting.get("created_at"),
        "scheduled_start_time": meeting.get("scheduled_start_time"),
        "scheduled_end_time": meeting.get("scheduled_end_time"),
        "recording_start_time": meeting.get("recording_start_time"),
        "recording_end_time": meeting.get("recording_end_time"),
        "transcript_language": meeting.get("transcript_language"),
        "calendar_invitees": meeting.get("calendar_invitees"),
        "recorded_by": meeting.get("recorded_by"),
        "teams": meeting.get("teams"),
        "topics": meeting.get("topics"),
        "summary": summary_text
    }
    
    # Add flag indicating if match was found in transcript
    if found_in_transcript:
        result["found_in_transcript"] = True
    
    return result


def _meeting_matches_search(meeting: dict, search_normalized: str) -> tuple:
    """Check if a meeting matches the search term in title, attendees, or teams.
    
    Returns:
        tuple: (matches, found_in_transcript) - matches=True if found, found_in_transcript=False for metadata searches
    """
    
    # Check title
    title = _normalize_search(meeting.get("title") or "")
    if search_normalized in title:
        return True, False

    # Check meeting_title
    meeting_title = _normalize_search(meeting.get("meeting_title") or "")
    if search_normalized in meeting_title:
        return True, False

    # Check attendee names and emails
    for invitee in meeting.get("calendar_invitees") or []:
        name = _normalize_search(invitee.get("name") or "")
        email = (invitee.get("email") or "").lower()
        if search_normalized in name or search_normalized in email:
            return True, False

    # Check team names
    for team in meeting.get("teams") or []:
        team_name = _normalize_search(team.get("name") or "") if isinstance(team, dict) else _normalize_search(str(team))
        if search_normalized in team_name:
            return True, False

    # Check topics
    for topic in meeting.get("topics") or []:
        topic_text = _normalize_search(topic.get("name") or "") if isinstance(topic, dict) else _normalize_search(str(topic))
        if search_normalized in topic_text:
            return True, False

    # Check default_summary.markdown_formatted (summary)
    summary = meeting.get("default_summary")
    summary_text = None

    if isinstance(summary, dict):
        summary_text = summary.get("markdown_formatted")

    if summary_text:
        summary_text_norm = _normalize_search(str(summary_text))
        if search_normalized in summary_text_norm:
            return True, False

    return False, False


def _meeting_matches_search_with_transcript(meeting: dict, search_normalized: str) -> tuple:
    """Check if a meeting matches the search term including transcript text.
    
    Returns:
        tuple: (matches, found_in_transcript) - found_in_transcript=True if match is in transcript
    """
    # First check all metadata fields
    matches, _ = _meeting_matches_search(meeting, search_normalized)
    if matches:
        return True, False
    
    # Check transcript
    transcript = meeting.get("transcript")
    if transcript:
        if isinstance(transcript, list):
            for entry in transcript:
                if isinstance(entry, dict):
                    text = entry.get("text", "")
                    if search_normalized in _normalize_search(text):
                        return True, True
        elif isinstance(transcript, str):
            if search_normalized in _normalize_search(transcript):
                return True, True
    
    return False, False


async def search_meetings(
    ctx: Context,
    query: str,
    include_transcript: bool = False
) -> dict:
    """Search meetings by keyword across titles, participants, teams, topics, and optionally transcripts.
    
    This tool searches meeting metadata and optionally full transcript content, returning
    matching meetings with their recording_id, summary, and optionally transcripts. Uses fuzzy matching
    to handle partial matches, plurals, and case-insensitive search.
    
    Fetches up to 10 pages (500 meetings max) to provide comprehensive search results.
    
    Args:
        ctx: MCP context for logging
        query: Search query string to match against meeting metadata
        include_transcript: If True, search within transcripts and include them in results (default: False)
    
    Returns:
        dict: {
            "items": [Meeting objects matching the search query with summary and optionally transcripts],
            "query": str (the search query used),
            "total_matches": int (number of matches found),
            "searched_transcripts": bool (whether transcripts were searched)
        }
    """
    try:
        await ctx.info(f"Searching meetings with query: {query}")
        
        if not query or not query.strip():
            await ctx.error("Search query cannot be empty")
            return {
                "items": [],
                "query": query,
                "total_matches": 0
            }
        
        # Normalize the search query
        search_normalized = _normalize_search(query)
        
        # Fetch all meetings (with pagination, max 10 pages = 500 meetings)
        all_meetings = []
        cursor: Optional[str] = None
        page = 1
        max_pages = 10
        
        while page <= max_pages:
            await ctx.info(f"Fetching meetings page {page}/{max_pages}")
            
            params = {
                "include_summary": True  # Always include summaries in search results
            }
            if cursor:
                params["cursor"] = cursor
            
            response = await client.get_meetings(params=params)
            items = response.get("items", [])
            
            if not items:
                break
            
            all_meetings.extend(items)
            
            # Check for next page
            cursor = response.get("cursor")
            if not cursor:
                break
            
            page += 1
        
        await ctx.info(f"Total meetings fetched: {len(all_meetings)}")
        
        # If including transcripts, fetch them for meetings that don't have them
        if include_transcript:
            await ctx.info("Fetching transcripts for meetings...")
            for meeting in all_meetings:
                if not meeting.get("transcript"):
                    recording_id = meeting.get("recording_id")
                    if recording_id:
                        try:
                            transcript_data = await client.get_transcript(recording_id)
                            meeting["transcript"] = transcript_data.get("transcript")
                        except Exception as e:
                            await ctx.info(f"Could not fetch transcript for {recording_id}: {str(e)}")
        
        # Filter meetings by search query and track where matches are found
        matched_meetings = []
        
        if include_transcript:
            for m in all_meetings:
                matches, found_in_transcript = _meeting_matches_search_with_transcript(m, search_normalized)
                if matches:
                    matched_meetings.append((m, found_in_transcript))
        else:
            for m in all_meetings:
                matches, _ = _meeting_matches_search(m, search_normalized)
                if matches:
                    matched_meetings.append((m, False))
        
        # Apply field filtering
        filtered_meetings = [
            _filter_meeting_fields(m, found_in_transcript=found_in_transcript)
            for m, found_in_transcript in matched_meetings
        ]
        
        await ctx.info(
            f"Search completed: found {len(matched_meetings)} matches out of {len(all_meetings)} meetings"
        )
        
        return {
            "items": filtered_meetings,
            "query": query,
            "total_matches": len(matched_meetings),
            "searched_transcripts": include_transcript
        }
        
    except FathomAPIError as e:
        await ctx.error(f"Fathom API error during search: {e.message}")
        raise e
    except Exception as e:
        await ctx.error(f"Unexpected error during search: {str(e)}")
        raise e
