"""
Tests for api/main.py — FastAPI endpoints via TestClient.

The LLM agent and pipeline outputs are fully mocked, so these tests
run without OpenAI credentials or pipeline data.
"""
import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient


# ── App fixture ───────────────────────────────────────────────────────────────

MOCK_AGGREGATED = {
    "total_transcripts": 3,
    "topic_frequency": [{"topic": "billing", "count": 1}],
    "sentiment_distribution": {"negative": {"count": 1, "pct": 33.3}},
    "urgency_distribution": {"high": {"count": 1, "pct": 33.3}},
    "churn_risk_distribution": {"medium": 1, "none": 2},
    "top_negative_topics": [{"topic": "billing", "count": 1}],
    "high_urgency_topics": [{"topic": "billing", "count": 1}],
    "intent_distribution": {"complaint": 1},
    "emotion_distribution": {"frustrated": 1},
    "churn_risk_accounts": [],
    "avg_sentiment_score_by_type": {"support": 2.0},
    "sentiment_by_call_type": {"support": {"negative": 1}},
    "executive_insights": {
        "key_insights": ["Billing issues dominate support calls."],
        "operational_risks": [],
        "churn_indicators": [],
        "customer_pain_points": [],
        "recommendations": [],
    },
}


@pytest.fixture
def client(sample_enriched):
    """Create a TestClient with mocked pipeline data.

    We prevent the startup event from loading real files by patching
    outputs_ready(), then inject test data after startup completes.
    """
    from api.main import app
    import api.main as main_module

    with patch("api.main.outputs_ready", return_value=False):
        with TestClient(app) as c:
            # Startup ran but skipped file loading; inject now
            main_module._enriched   = list(sample_enriched)
            main_module._aggregated = MOCK_AGGREGATED
            yield c

    # Cleanup module state between tests
    main_module._enriched   = []
    main_module._aggregated = {}


# ── /api/health ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/api/health").json()
        assert "status" in data
        assert "transcript_count" in data
        assert "pipeline_ready" in data

    def test_transcript_count_matches_loaded_data(self, client, sample_enriched):
        data = client.get("/api/health").json()
        assert data["transcript_count"] == len(sample_enriched)


# ── /api/transcripts ──────────────────────────────────────────────────────────

class TestGetTranscripts:
    def test_returns_all_records(self, client, sample_enriched):
        data = client.get("/api/transcripts").json()
        assert data["total"] == len(sample_enriched)
        assert len(data["transcripts"]) == len(sample_enriched)

    def test_response_has_transcripts_and_total_keys(self, client):
        data = client.get("/api/transcripts").json()
        assert "transcripts" in data
        assert "total" in data

    def test_full_transcript_stripped_from_list(self, client, sample_enriched):
        # Inject a record with full_transcript
        import api.main as m
        m._enriched = [{**sample_enriched[0], "full_transcript": "FULL TEXT"}]
        resp = client.get("/api/transcripts").json()
        for t in resp["transcripts"]:
            assert "full_transcript" not in t

    def test_filter_by_call_type(self, client):
        data = client.get("/api/transcripts?call_type=support").json()
        for t in data["transcripts"]:
            assert t["call_type"] == "support"

    def test_filter_by_sentiment(self, client):
        data = client.get("/api/transcripts?sentiment=positive").json()
        for t in data["transcripts"]:
            assert t["sentiment"] == "positive"

    def test_filter_by_urgency(self, client):
        data = client.get("/api/transcripts?urgency=high").json()
        for t in data["transcripts"]:
            assert t["urgency"] == "high"

    def test_filter_multiple_call_types(self, client):
        data = client.get("/api/transcripts?call_type=support,external").json()
        for t in data["transcripts"]:
            assert t["call_type"] in ("support", "external")

    def test_search_filters_by_title(self, client):
        data = client.get("/api/transcripts?search=billing").json()
        assert data["total"] >= 1
        for t in data["transcripts"]:
            text = (t.get("title","") + t.get("summary","") + t.get("topic","")).lower()
            assert "billing" in text

    def test_pagination_limit(self, client):
        data = client.get("/api/transcripts?limit=1").json()
        assert len(data["transcripts"]) == 1

    def test_pagination_offset(self, client, sample_enriched):
        first  = client.get("/api/transcripts?limit=1&offset=0").json()
        second = client.get("/api/transcripts?limit=1&offset=1").json()
        if len(sample_enriched) > 1:
            assert first["transcripts"][0]["id"] != second["transcripts"][0]["id"]

    def test_no_filter_returns_200(self, client):
        assert client.get("/api/transcripts").status_code == 200


# ── /api/transcripts/{id} ─────────────────────────────────────────────────────

class TestGetTranscript:
    def test_returns_known_id(self, client, sample_enriched):
        tid = sample_enriched[0]["id"]
        resp = client.get(f"/api/transcripts/{tid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == tid

    def test_returns_404_for_unknown_id(self, client):
        resp = client.get("/api/transcripts/does_not_exist")
        assert resp.status_code == 404

    def test_full_transcript_included_in_detail(self, client, sample_enriched):
        import api.main as m
        m._enriched = [{**sample_enriched[0], "full_transcript": "FULL TEXT HERE"}]
        tid = sample_enriched[0]["id"]
        resp = client.get(f"/api/transcripts/{tid}").json()
        assert resp.get("full_transcript") == "FULL TEXT HERE"


# ── /api/aggregated ───────────────────────────────────────────────────────────

class TestGetAggregated:
    def test_returns_200(self, client):
        assert client.get("/api/aggregated").status_code == 200

    def test_has_expected_top_level_keys(self, client):
        data = client.get("/api/aggregated").json()
        for key in ["total_transcripts", "topic_frequency", "sentiment_distribution",
                    "urgency_distribution", "executive_insights"]:
            assert key in data, f"Missing key: {key}"


# ── /api/validation ───────────────────────────────────────────────────────────

class TestValidationEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/validation").status_code == 200

    def test_response_has_validation_keys(self, client):
        data = client.get("/api/validation").json()
        for key in ["total", "valid", "valid_pct", "error_count", "warning_count"]:
            assert key in data

    def test_total_matches_loaded_records(self, client, sample_enriched):
        data = client.get("/api/validation").json()
        assert data["total"] == len(sample_enriched)

    def test_valid_records_count(self, client, sample_enriched):
        data = client.get("/api/validation").json()
        # All sample records are valid
        assert data["valid"] == len(sample_enriched)
        assert data["error_count"] == 0


# ── /api/chat/stream ──────────────────────────────────────────────────────────

class TestChatStream:
    def test_returns_200_with_mocked_agent(self, client):
        def mock_stream(*args, **kwargs):
            yield "Hello "
            yield "world"

        with patch("api.main.stream_agent_response", side_effect=mock_stream):
            resp = client.post(
                "/api/chat/stream",
                json={"question": "What are the top issues?", "history": []},
            )
        assert resp.status_code == 200

    def test_response_is_event_stream(self, client):
        def mock_stream(*args, **kwargs):
            yield "test"

        with patch("api.main.stream_agent_response", side_effect=mock_stream):
            resp = client.post(
                "/api/chat/stream",
                json={"question": "hello", "history": []},
            )
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_sse_format_in_response_body(self, client):
        def mock_stream(*args, **kwargs):
            yield "chunk"

        with patch("api.main.stream_agent_response", side_effect=mock_stream):
            resp = client.post(
                "/api/chat/stream",
                json={"question": "hello", "history": []},
            )
        body = resp.text
        assert "data:" in body
        assert "[DONE]" in body
