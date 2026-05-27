"""Unit tests for tools/recordings.py.

These tests cover the resilience behavior introduced for `get_meeting_transcript`
and `get_meeting_details`: when `client.get_meeting` raises (the Fathom REST API
has no `GET /recordings/{id}` endpoint, so older recordings 404 against the
first-page scan), the transcript/summary calls still succeed and metadata fields
come back empty.

Run with:
    uv run python -m unittest tests.test_recordings
"""
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Set a dummy API key before importing the module under test so config validation
# doesn't fail at import time.
os.environ.setdefault("FATHOM_API_KEY", "test-key")

# Make the package root importable when running from a checkout.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fathom_client import FathomAPIError  # noqa: E402
from tools import recordings  # noqa: E402


class MockContext:
    """Minimal stand-in for fastmcp.Context — only info/error are called."""

    def __init__(self):
        self.info_messages = []
        self.error_messages = []

    async def info(self, msg):
        self.info_messages.append(msg)

    async def error(self, msg):
        self.error_messages.append(msg)


SAMPLE_MEETING = {
    "title": "1-1 alice - bob",
    "url": "https://fathom.video/calls/12345",
    "share_url": "https://fathom.video/share/abcdef",
    "created_at": "2026-05-27T14:30:00Z",
    "scheduled_start_time": "2026-05-27T14:30:00Z",
    "scheduled_end_time": "2026-05-27T15:00:00Z",
    "recording_start_time": "2026-05-27T14:30:30Z",
    "recording_end_time": "2026-05-27T15:00:45Z",
    "transcript_language": "en",
    "participants": [{"name": "Alice"}, {"name": "Bob"}],
    "recorded_by": {"name": "Alice", "email": "alice@example.com"},
    "teams": ["Engineering"],
    "topics": ["1-1"],
    "sentiment": "neutral",
    "crm_matches": [],
}

SAMPLE_TRANSCRIPT = {
    "transcript": [
        {"speaker": {"display_name": "Alice"}, "text": "Hi Bob.", "timestamp": "00:00:01"},
        {"speaker": {"display_name": "Bob"}, "text": "Hey Alice.", "timestamp": "00:00:03"},
    ]
}

SAMPLE_SUMMARY = {
    "summary": {
        "markdown_formatted": "## Recap\n\nAlice and Bob caught up.",
    }
}


class GetMeetingTranscriptTests(unittest.IsolatedAsyncioTestCase):
    """Behavior of get_meeting_transcript across meeting-lookup outcomes."""

    async def test_returns_transcript_with_full_metadata_when_meeting_lookup_succeeds(self):
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(return_value=SAMPLE_MEETING)), \
             patch.object(recordings.client, "get_transcript", new=AsyncMock(return_value=SAMPLE_TRANSCRIPT)):
            result = await recordings.get_meeting_transcript(MockContext(), recording_id=12345)

        self.assertEqual(result["recording_id"], 12345)
        self.assertEqual(result["title"], "1-1 alice - bob")
        self.assertEqual(len(result["participants"]), 2)
        self.assertEqual(result["created_at"], "2026-05-27T14:30:00Z")
        self.assertEqual(len(result["transcript"]), 2)

    async def test_returns_transcript_with_empty_metadata_when_meeting_lookup_404s(self):
        """The fix: a 404 from get_meeting must not fail the whole call."""
        meeting_404 = FathomAPIError("Meeting with recording_id 99999 not found", 404)
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(side_effect=meeting_404)), \
             patch.object(recordings.client, "get_transcript", new=AsyncMock(return_value=SAMPLE_TRANSCRIPT)):
            ctx = MockContext()
            result = await recordings.get_meeting_transcript(ctx, recording_id=99999)

        # Transcript still comes through.
        self.assertEqual(result["recording_id"], 99999)
        self.assertEqual(len(result["transcript"]), 2)
        # Metadata fields come back empty (not raised).
        self.assertIsNone(result["title"])
        self.assertEqual(result["participants"], [])
        self.assertIsNone(result["created_at"])
        self.assertIsNone(result["scheduled_start_time"])
        self.assertIsNone(result["scheduled_end_time"])
        # Best-effort log includes exception type + status so operators can
        # distinguish 401 (scope change / bad key) from 404 (old recording).
        self.assertTrue(any("Meeting metadata not available" in m for m in ctx.info_messages))
        self.assertTrue(any("FathomAPIError status=404" in m for m in ctx.info_messages))

    async def test_propagates_when_meeting_lookup_raises_non_fathom_exception(self):
        """Non-FathomAPIError exceptions on the meeting lookup are NOT swallowed.

        A KeyError/AttributeError/etc. from a programming bug must propagate so
        it can be diagnosed, not get silently hidden as "metadata unavailable."
        """
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             patch.object(recordings.client, "get_transcript", new=AsyncMock(return_value=SAMPLE_TRANSCRIPT)):
            with self.assertRaises(RuntimeError):
                await recordings.get_meeting_transcript(MockContext(), recording_id=12345)

    async def test_raises_when_transcript_fetch_fails(self):
        """Transcript is the primary payload; its failure must propagate."""
        transcript_err = FathomAPIError("Resource not found", 404)
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(return_value=SAMPLE_MEETING)), \
             patch.object(recordings.client, "get_transcript", new=AsyncMock(side_effect=transcript_err)):
            with self.assertRaises(FathomAPIError):
                await recordings.get_meeting_transcript(MockContext(), recording_id=12345)

    async def test_raises_when_transcript_fetch_fails_even_if_meeting_also_fails(self):
        """If both fail, the transcript error is what propagates (the primary payload)."""
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(side_effect=FathomAPIError("meet-404", 404))), \
             patch.object(recordings.client, "get_transcript", new=AsyncMock(side_effect=FathomAPIError("transcript-404", 404))):
            with self.assertRaises(FathomAPIError) as cm:
                await recordings.get_meeting_transcript(MockContext(), recording_id=12345)
        self.assertEqual(cm.exception.message, "transcript-404")


class GetMeetingDetailsTests(unittest.IsolatedAsyncioTestCase):
    """Behavior of get_meeting_details across meeting-lookup outcomes."""

    async def test_returns_summary_with_full_metadata_when_meeting_lookup_succeeds(self):
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(return_value=SAMPLE_MEETING)), \
             patch.object(recordings.client, "get_summary", new=AsyncMock(return_value=SAMPLE_SUMMARY)):
            result = await recordings.get_meeting_details(MockContext(), recording_id=12345)

        self.assertEqual(result["recording_id"], 12345)
        self.assertEqual(result["title"], "1-1 alice - bob")
        self.assertIn("Alice and Bob caught up", result["summary"])

    async def test_returns_summary_with_empty_metadata_when_meeting_lookup_404s(self):
        """The fix: a 404 from get_meeting must not fail the whole call."""
        meeting_404 = FathomAPIError("Meeting with recording_id 99999 not found", 404)
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(side_effect=meeting_404)), \
             patch.object(recordings.client, "get_summary", new=AsyncMock(return_value=SAMPLE_SUMMARY)):
            ctx = MockContext()
            result = await recordings.get_meeting_details(ctx, recording_id=99999)

        self.assertEqual(result["recording_id"], 99999)
        self.assertIn("Alice and Bob caught up", result["summary"])
        # Scalar metadata fields come back None.
        self.assertIsNone(result["title"])
        self.assertIsNone(result["meeting_url"])
        self.assertIsNone(result["recorded_by"])
        # List-typed metadata fields come back as empty lists, not None, so
        # downstream callers can iterate without a None check.
        self.assertEqual(result["participants"], [])
        self.assertEqual(result["teams"], [])
        self.assertEqual(result["topics"], [])
        self.assertEqual(result["crm_matches"], [])
        # Best-effort log includes exception type + status for operator triage.
        self.assertTrue(any("Meeting metadata not available" in m for m in ctx.info_messages))
        self.assertTrue(any("FathomAPIError status=404" in m for m in ctx.info_messages))

    async def test_propagates_when_meeting_lookup_raises_non_fathom_exception(self):
        """Non-FathomAPIError exceptions on the meeting lookup are NOT swallowed."""
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             patch.object(recordings.client, "get_summary", new=AsyncMock(return_value=SAMPLE_SUMMARY)):
            with self.assertRaises(RuntimeError):
                await recordings.get_meeting_details(MockContext(), recording_id=12345)

    async def test_raises_when_summary_fetch_fails(self):
        """Summary is the primary payload for get_meeting_details; its failure must propagate."""
        with patch.object(recordings.client, "get_meeting", new=AsyncMock(return_value=SAMPLE_MEETING)), \
             patch.object(recordings.client, "get_summary", new=AsyncMock(side_effect=FathomAPIError("nope", 404))):
            with self.assertRaises(FathomAPIError):
                await recordings.get_meeting_details(MockContext(), recording_id=12345)


if __name__ == "__main__":
    unittest.main()
