"""Tests for src/analysis.py — aggregation and distribution functions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.analysis import (
    compute_topic_frequency,
    compute_sentiment_distribution,
    compute_urgency_distribution,
    compute_churn_risk_distribution,
    compute_sentiment_by_call_type,
    compute_top_negative_topics,
    compute_high_urgency_topics,
    compute_intent_distribution,
    compute_emotion_distribution,
    compute_avg_sentiment_score_by_type,
    compute_churn_risk_accounts,
)


class TestTopicFrequency:
    def test_counts_topics_correctly(self, sample_enriched):
        result = compute_topic_frequency(sample_enriched)
        topics = {r["topic"]: r["count"] for r in result}
        assert topics["billing"] == 1
        assert topics["onboarding"] == 1

    def test_sorted_descending(self, sample_enriched):
        enriched = sample_enriched + [
            {**sample_enriched[0], "id": "x", "topic": "billing"}
        ]
        result = compute_topic_frequency(enriched)
        assert result[0]["topic"] == "billing"
        assert result[0]["count"] == 2

    def test_returns_list_of_dicts_with_topic_and_count(self, sample_enriched):
        result = compute_topic_frequency(sample_enriched)
        for item in result:
            assert "topic" in item and "count" in item

    def test_empty_input(self):
        assert compute_topic_frequency([]) == []


class TestSentimentDistribution:
    def test_returns_all_present_sentiments(self, sample_enriched):
        result = compute_sentiment_distribution(sample_enriched)
        assert "negative" in result
        assert "positive" in result
        assert "neutral" in result

    def test_counts_sum_to_total(self, sample_enriched):
        result = compute_sentiment_distribution(sample_enriched)
        total = sum(v["count"] for v in result.values())
        assert total == len(sample_enriched)

    def test_percentages_sum_near_100(self, sample_enriched):
        result = compute_sentiment_distribution(sample_enriched)
        total_pct = sum(v["pct"] for v in result.values())
        assert abs(total_pct - 100.0) < 1.0  # Allow small rounding

    def test_pct_field_present(self, sample_enriched):
        result = compute_sentiment_distribution(sample_enriched)
        for val in result.values():
            assert "pct" in val and "count" in val


class TestUrgencyDistribution:
    def test_keys_match_input_urgencies(self, sample_enriched):
        result = compute_urgency_distribution(sample_enriched)
        assert "high" in result
        assert "low" in result
        assert "medium" in result

    def test_counts_correct(self, sample_enriched):
        result = compute_urgency_distribution(sample_enriched)
        assert result["high"]["count"] == 1
        assert result["low"]["count"] == 1
        assert result["medium"]["count"] == 1


class TestChurnRiskDistribution:
    def test_counts_each_risk_level(self, sample_enriched):
        result = compute_churn_risk_distribution(sample_enriched)
        assert result["none"] == 2
        assert result["medium"] == 1

    def test_empty_input(self):
        assert compute_churn_risk_distribution([]) == {}


class TestSentimentByCallType:
    def test_keys_are_call_types(self, sample_enriched):
        result = compute_sentiment_by_call_type(sample_enriched)
        assert "support" in result
        assert "external" in result
        assert "internal" in result

    def test_nested_values_are_ints(self, sample_enriched):
        result = compute_sentiment_by_call_type(sample_enriched)
        for ct, sentiments in result.items():
            for s, count in sentiments.items():
                assert isinstance(count, int), f"{ct}/{s} should be int"

    def test_support_negative_count(self, sample_enriched):
        result = compute_sentiment_by_call_type(sample_enriched)
        assert result["support"]["negative"] == 1


class TestNegativeTopics:
    def test_only_includes_negative_and_mixed(self, sample_enriched):
        result = compute_top_negative_topics(sample_enriched)
        # Only t001 is negative; t002=positive, t003=neutral → excluded
        topics = [r["topic"] for r in result]
        assert "billing" in topics
        assert "onboarding" not in topics

    def test_empty_when_no_negative_records(self):
        all_positive = [
            {"id": f"t{i}", "sentiment": "positive", "topic": f"topic{i}"}
            for i in range(3)
        ]
        result = compute_top_negative_topics(all_positive)
        assert result == []


class TestHighUrgencyTopics:
    def test_includes_high_urgency_only(self, sample_enriched):
        result = compute_high_urgency_topics(sample_enriched)
        topics = [r["topic"] for r in result]
        assert "billing" in topics        # t001 is high urgency
        assert "onboarding" not in topics # t002 is low urgency
        assert "technical_issue" not in topics  # t003 is medium

    def test_empty_when_no_high_urgency(self):
        low_only = [{"id": "x", "urgency": "low", "topic": "misc"}]
        result = compute_high_urgency_topics(low_only)
        assert result == []


class TestIntentDistribution:
    def test_counts_intents(self, sample_enriched):
        result = compute_intent_distribution(sample_enriched)
        assert result.get("complaint") == 1
        assert result.get("information_request") == 1

    def test_returns_dict(self, sample_enriched):
        assert isinstance(compute_intent_distribution(sample_enriched), dict)


class TestEmotionDistribution:
    def test_counts_emotions(self, sample_enriched):
        result = compute_emotion_distribution(sample_enriched)
        assert result.get("frustrated") == 1
        assert result.get("satisfied") == 1


class TestAvgSentimentScoreByType:
    def test_averages_per_call_type(self, sample_enriched):
        result = compute_avg_sentiment_score_by_type(sample_enriched)
        assert result["support"] == 2.0
        assert result["external"] == 4.5
        assert result["internal"] == 3.0

    def test_ignores_records_without_score(self):
        records = [
            {"call_type": "support", "sentiment_score": 4.0},
            {"call_type": "support", "sentiment_score": None},
        ]
        result = compute_avg_sentiment_score_by_type(records)
        assert result["support"] == 4.0


class TestChurnRiskAccounts:
    def test_only_external_medium_high_churn(self, sample_enriched):
        result = compute_churn_risk_accounts(sample_enriched)
        # t001 is support (not external) → excluded
        # t002 is external + churn_risk=none → excluded
        assert result == []

    def test_includes_external_high_churn(self, sample_enriched):
        at_risk = {
            **sample_enriched[1],  # external call_type
            "id": "t_risk",
            "churn_risk": "high",
            "sentiment": "negative",
        }
        result = compute_churn_risk_accounts(sample_enriched + [at_risk])
        ids = [r.get("title") for r in result]
        assert at_risk["title"] in ids

    def test_sorted_high_before_medium(self):
        records = [
            {"id": "a", "title": "A", "call_type": "external", "churn_risk": "medium",
             "sentiment": "mixed", "urgency": "medium", "summary": "s"},
            {"id": "b", "title": "B", "call_type": "external", "churn_risk": "high",
             "sentiment": "negative", "urgency": "high", "summary": "s"},
        ]
        result = compute_churn_risk_accounts(records)
        assert result[0]["churn_risk"] == "high"
        assert result[1]["churn_risk"] == "medium"
