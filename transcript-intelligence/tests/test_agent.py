"""
Tests for src/agent.py — tools and streaming response.

The LangGraph agent and OpenAI client are fully mocked so no API
credentials are needed. Tool functions are called via .invoke() which
is the standard LangChain interface for StructuredTool objects.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import src.agent as agent_module
from src.agent import init, search_transcripts, get_statistics, get_account_details, stream_agent_response


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_agent_state():
    """Reset module-level data store before and after each test."""
    agent_module._enriched   = []
    agent_module._aggregated = {}
    yield
    agent_module._enriched   = []
    agent_module._aggregated = {}


MOCK_AGGREGATED = {
    "sentiment_distribution":  {"negative": {"count": 1, "pct": 33.3}},
    "urgency_distribution":    {"high": {"count": 1, "pct": 33.3}},
    "churn_risk_distribution": {"medium": 1, "none": 2},
    "churn_risk_accounts":     [{"account": "Apex Corp", "risk": "medium"}],
    "topic_frequency":         [{"topic": "billing", "count": 5}],
    "top_negative_topics":     [{"topic": "billing", "count": 3}],
    "executive_insights": {
        "key_insights":       ["Billing dominates support calls."],
        "operational_risks":  [],
        "churn_indicators":   [],
        "customer_pain_points": [],
        "recommendations":    [],
    },
}


def _make_mock_agent(chunks: list[tuple[str, str]]):
    """
    Return a mock LangGraph agent whose .stream() yields (chunk, metadata) pairs.
    chunks: list of (text_content, langgraph_node) tuples.
    """
    mock_agent = MagicMock()

    def _stream(input_dict, stream_mode):
        for text, node in chunks:
            mock_chunk = MagicMock()
            mock_chunk.content = text
            yield mock_chunk, {"langgraph_node": node}

    mock_agent.stream.side_effect = _stream
    return mock_agent


# ── init ──────────────────────────────────────────────────────────────────────

class TestInit:
    def test_sets_enriched(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        assert agent_module._enriched is sample_enriched

    def test_sets_aggregated(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        assert agent_module._aggregated is MOCK_AGGREGATED

    def test_overwrites_previous_state(self, sample_enriched):
        agent_module._enriched   = [{"id": "stale"}]
        agent_module._aggregated = {"old": True}
        init(sample_enriched, MOCK_AGGREGATED)
        assert agent_module._enriched is sample_enriched
        assert agent_module._aggregated is MOCK_AGGREGATED


# ── search_transcripts tool ───────────────────────────────────────────────────

class TestSearchTranscripts:
    def test_returns_results_when_matches_found(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[{"id": "t001", "score": 0.92}]):
            result = search_transcripts.invoke({"query": "billing"})
        assert "Billing Issue" in result

    def test_no_results_returns_fallback_message(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[]):
            result = search_transcripts.invoke({"query": "xyz"})
        assert "No relevant transcripts found" in result

    def test_result_includes_similarity_score(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[{"id": "t001", "score": 0.85}]):
            result = search_transcripts.invoke({"query": "billing"})
        assert "0.85" in result

    def test_result_includes_sentiment_field(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[{"id": "t001", "score": 0.9}]):
            result = search_transcripts.invoke({"query": "billing"})
        assert "sentiment:" in result

    def test_result_includes_urgency_field(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[{"id": "t001", "score": 0.9}]):
            result = search_transcripts.invoke({"query": "billing"})
        assert "urgency:" in result

    def test_action_items_capped_at_three(self, sample_enriched):
        enriched = [{**sample_enriched[0], "action_items": ["A", "B", "C", "D", "E"]}]
        init(enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[{"id": "t001", "score": 0.9}]):
            result = search_transcripts.invoke({"query": "billing"})
        # 3 items joined by "; " = at most 2 semicolons
        action_line = [l for l in result.splitlines() if "Action items:" in l][0]
        assert action_line.count(";") <= 2

    def test_top_k_forwarded_to_semantic_search(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        with patch("src.agent.semantic_search", return_value=[]) as mock_search:
            search_transcripts.invoke({"query": "billing", "top_k": 3})
        mock_search.assert_called_once_with("billing", top_k=3)

    def test_multiple_results_separated_by_blank_line(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        mock_hits = [{"id": "t001", "score": 0.9}, {"id": "t002", "score": 0.8}]
        with patch("src.agent.semantic_search", return_value=mock_hits):
            result = search_transcripts.invoke({"query": "call"})
        assert "\n\n" in result


# ── get_statistics tool ───────────────────────────────────────────────────────

class TestGetStatistics:
    def test_not_available_when_aggregated_empty(self):
        result = get_statistics.invoke({"category": "all"})
        assert "not available" in result.lower()

    def test_sentiment_category_returns_distribution(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "sentiment"})
        assert "negative" in result
        assert "33.3" in result

    def test_urgency_category_returns_distribution(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "urgency"})
        assert "high" in result

    def test_churn_category_includes_at_risk_accounts(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "churn"})
        assert "Apex Corp" in result

    def test_topics_category_includes_top_topics(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "topics"})
        assert "billing" in result

    def test_insights_category_includes_key_insights(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "insights"})
        assert "Billing dominates" in result

    def test_all_category_contains_every_section(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "all"})
        for section in ("sentiment", "urgency", "churn", "topics", "insights"):
            assert section in result

    def test_unknown_category_falls_back_to_all(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_statistics.invoke({"category": "nonexistent"})
        assert "sentiment" in result


# ── get_account_details tool ──────────────────────────────────────────────────

class TestGetAccountDetails:
    def test_match_found_in_title(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Apex Corp"})
        assert "Found" in result
        assert "Apex Corp" in result

    def test_match_found_in_summary(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        # "billing discrepancy" is in the summary of t001
        result = get_account_details.invoke({"account_name": "billing discrepancy"})
        assert "Found" in result

    def test_match_found_in_key_entities(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Summit Trust"})
        assert "Summit Trust" in result

    def test_search_is_case_insensitive(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "apex corp"})
        assert "Found" in result

    def test_no_match_returns_not_found_message(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Totally Unknown XYZ"})
        assert "No records found" in result

    def test_result_includes_sentiment_and_urgency(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Apex Corp"})
        assert "negative" in result
        assert "high" in result

    def test_caps_results_at_six(self, sample_enriched):
        many = [
            {**sample_enriched[0], "id": f"t{i:03d}", "title": f"Omega Corp Call {i}",
             "key_entities": [], "summary": ""}
            for i in range(8)
        ]
        init(many, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Omega Corp"})
        assert "Found 8" in result
        assert result.count("• [") == 6

    def test_record_count_in_header(self, sample_enriched):
        init(sample_enriched, MOCK_AGGREGATED)
        result = get_account_details.invoke({"account_name": "Apex Corp"})
        assert "1 record(s)" in result


# ── stream_agent_response ─────────────────────────────────────────────────────

class TestStreamAgentResponse:
    def test_yields_text_chunks_from_agent_node(self, sample_enriched):
        mock_agent = _make_mock_agent([("Hello ", "agent"), ("world", "agent")])
        with patch("src.agent._build_agent", return_value=mock_agent):
            chunks = list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert chunks == ["Hello ", "world"]

    def test_filters_out_tool_node_chunks(self, sample_enriched):
        mock_agent = _make_mock_agent([("tool output", "tools"), ("answer", "agent")])
        with patch("src.agent._build_agent", return_value=mock_agent):
            chunks = list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert chunks == ["answer"]

    def test_filters_empty_string_chunks(self, sample_enriched):
        mock_agent = _make_mock_agent([("", "agent"), ("real content", "agent")])
        with patch("src.agent._build_agent", return_value=mock_agent):
            chunks = list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert chunks == ["real content"]

    def test_non_string_content_is_skipped(self, sample_enriched):
        mock_agent = MagicMock()

        def _stream(input_dict, stream_mode):
            # Simulate a tool-call chunk where content is a list
            tool_chunk = MagicMock()
            tool_chunk.content = [{"type": "tool_use", "id": "x"}]
            yield tool_chunk, {"langgraph_node": "agent"}
            text_chunk = MagicMock()
            text_chunk.content = "final answer"
            yield text_chunk, {"langgraph_node": "agent"}

        mock_agent.stream.side_effect = _stream
        with patch("src.agent._build_agent", return_value=mock_agent):
            chunks = list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert chunks == ["final answer"]

    def test_calls_init_before_streaming(self, sample_enriched):
        mock_agent = _make_mock_agent([])
        with patch("src.agent._build_agent", return_value=mock_agent):
            list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert agent_module._enriched   is sample_enriched
        assert agent_module._aggregated is MOCK_AGGREGATED

    def test_includes_history_in_messages(self, sample_enriched):
        mock_agent = _make_mock_agent([("ok", "agent")])
        history = [
            {"role": "user",      "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
        ]
        with patch("src.agent._build_agent", return_value=mock_agent):
            list(stream_agent_response("follow up", sample_enriched, MOCK_AGGREGATED, history=history))

        messages = mock_agent.stream.call_args[0][0]["messages"]
        assert len(messages) == 3  # 2 history + 1 current question

    def test_no_history_sends_only_current_question(self, sample_enriched):
        mock_agent = _make_mock_agent([("answer", "agent")])
        with patch("src.agent._build_agent", return_value=mock_agent):
            list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED, history=None))

        messages = mock_agent.stream.call_args[0][0]["messages"]
        assert len(messages) == 1

    def test_build_agent_receives_transcript_count(self, sample_enriched):
        mock_agent = _make_mock_agent([])
        with patch("src.agent._build_agent", return_value=mock_agent) as mock_build:
            list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        mock_build.assert_called_once_with(len(sample_enriched))

    def test_yields_nothing_when_no_agent_chunks(self, sample_enriched):
        mock_agent = _make_mock_agent([("only tools", "tools")])
        with patch("src.agent._build_agent", return_value=mock_agent):
            chunks = list(stream_agent_response("question", sample_enriched, MOCK_AGGREGATED))
        assert chunks == []
