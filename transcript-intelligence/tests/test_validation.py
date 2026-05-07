"""Tests for src/validation.py — LLM output schema and consistency checks."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.validation import (
    validate_record,
    validate_enriched,
    ValidationReport,
    VALID_SENTIMENTS,
    VALID_URGENCIES,
    VALID_CALL_TYPES,
    VALID_CHURN,
)


# ── validate_record ───────────────────────────────────────────────────────────

class TestValidateRecord:
    def test_valid_record_produces_no_errors(self, single_record):
        errors, warnings = validate_record(single_record, 0)
        assert errors == []

    def test_missing_required_field(self, single_record):
        bad = {**single_record, "sentiment": None}
        errors, _ = validate_record(bad, 0)
        assert any("sentiment" in e for e in errors)

    def test_missing_title(self, single_record):
        bad = {**single_record, "title": ""}
        errors, _ = validate_record(bad, 0)
        assert any("title" in e for e in errors)

    @pytest.mark.parametrize("bad_val", ["unknown", "POSITIVE", "happy", ""])
    def test_invalid_sentiment_values(self, single_record, bad_val):
        bad = {**single_record, "sentiment": bad_val}
        errors, _ = validate_record(bad, 0)
        assert any("sentiment" in e for e in errors)

    @pytest.mark.parametrize("good_val", VALID_SENTIMENTS)
    def test_all_valid_sentiments_pass(self, single_record, good_val):
        rec = {**single_record, "sentiment": good_val}
        errors, _ = validate_record(rec, 0)
        sentiment_errors = [e for e in errors if "Invalid sentiment" in e]
        assert sentiment_errors == []

    @pytest.mark.parametrize("bad_val", ["urgent", "CRITICAL", "extreme"])
    def test_invalid_urgency_values(self, single_record, bad_val):
        bad = {**single_record, "urgency": bad_val}
        errors, _ = validate_record(bad, 0)
        assert any("urgency" in e for e in errors)

    @pytest.mark.parametrize("bad_val", ["sales", "SUPPORT", "external_call"])
    def test_invalid_call_type(self, single_record, bad_val):
        bad = {**single_record, "call_type": bad_val}
        errors, _ = validate_record(bad, 0)
        assert any("call_type" in e for e in errors)

    @pytest.mark.parametrize("bad_val", ["very_high", "none_detected"])
    def test_invalid_churn_risk(self, single_record, bad_val):
        bad = {**single_record, "churn_risk": bad_val}
        errors, _ = validate_record(bad, 0)
        assert any("churn_risk" in e for e in errors)

    def test_sentiment_score_out_of_range_low(self, single_record):
        bad = {**single_record, "sentiment_score": 0}
        errors, _ = validate_record(bad, 0)
        assert any("sentiment_score" in e for e in errors)

    def test_sentiment_score_out_of_range_high(self, single_record):
        bad = {**single_record, "sentiment_score": 6}
        errors, _ = validate_record(bad, 0)
        assert any("sentiment_score" in e for e in errors)

    @pytest.mark.parametrize("score", [1, 1.5, 3, 4.9, 5])
    def test_valid_sentiment_scores(self, single_record, score):
        rec = {**single_record, "sentiment_score": score}
        errors, _ = validate_record(rec, 0)
        score_errors = [e for e in errors if "sentiment_score" in e]
        assert score_errors == []

    def test_non_numeric_sentiment_score(self, single_record):
        bad = {**single_record, "sentiment_score": "high"}
        errors, _ = validate_record(bad, 0)
        assert any("sentiment_score" in e for e in errors)

    def test_key_entities_must_be_list(self, single_record):
        bad = {**single_record, "key_entities": "Apex Corp"}
        errors, _ = validate_record(bad, 0)
        assert any("key_entities" in e for e in errors)

    def test_action_items_must_be_list(self, single_record):
        bad = {**single_record, "action_items": "Fix billing"}
        errors, _ = validate_record(bad, 0)
        assert any("action_items" in e for e in errors)


class TestCrossFieldConsistency:
    def test_high_churn_positive_sentiment_is_warning(self, single_record):
        suspicious = {**single_record, "churn_risk": "high", "sentiment": "positive"}
        _, warnings = validate_record(suspicious, 0)
        assert any("churn_risk=high" in w and "positive" in w for w in warnings)

    def test_critical_urgency_positive_sentiment_is_warning(self, single_record):
        suspicious = {**single_record, "urgency": "critical", "sentiment": "positive"}
        _, warnings = validate_record(suspicious, 0)
        assert any("urgency=critical" in w for w in warnings)

    def test_positive_sentiment_low_score_is_warning(self, single_record):
        suspicious = {**single_record, "sentiment": "positive", "sentiment_score": 1.5}
        _, warnings = validate_record(suspicious, 0)
        assert any("positive" in w and "score=" in w for w in warnings)

    def test_negative_sentiment_high_score_is_warning(self, single_record):
        suspicious = {**single_record, "sentiment": "negative", "sentiment_score": 4.5}
        _, warnings = validate_record(suspicious, 0)
        assert any("negative" in w and "score=" in w for w in warnings)

    def test_consistent_record_has_no_cross_field_warnings(self):
        rec = {
            "id": "x1", "title": "T", "call_type": "support",
            "sentiment": "negative", "urgency": "high",
            "topic": "billing", "summary": "Issue",
            "churn_risk": "high", "sentiment_score": 2.0,
            "emotion": "frustrated", "intent": "complaint",
            "key_entities": [], "action_items": [],
        }
        errors, warnings = validate_record(rec, 0)
        consistency_warnings = [w for w in warnings if "Inconsistency" in w or "Suspicious" in w]
        assert consistency_warnings == []


# ── validate_enriched ─────────────────────────────────────────────────────────

class TestValidateEnriched:
    def test_all_valid_records(self, sample_enriched):
        report = validate_enriched(sample_enriched)
        assert report.total == 3
        assert report.valid == 3
        assert report.error_count == 0

    def test_report_counts_invalid_records(self, sample_enriched):
        broken = sample_enriched + [
            {"id": "bad1", "title": "", "call_type": "unknown",
             "sentiment": "extreme", "urgency": "super", "topic": None, "summary": "x"}
        ]
        report = validate_enriched(broken)
        assert report.total == 4
        assert report.valid == 3
        assert report.error_count > 0

    def test_valid_pct_calculation(self, sample_enriched):
        report = validate_enriched(sample_enriched)
        assert report.valid_pct == 100.0

    def test_empty_input(self):
        report = validate_enriched([])
        assert report.total == 0
        assert report.valid == 0
        assert report.valid_pct == 0.0

    def test_to_dict_has_expected_keys(self, sample_enriched):
        report = validate_enriched(sample_enriched)
        d = report.to_dict()
        for key in ["total", "valid", "valid_pct", "error_count", "warning_count", "errors", "warnings"]:
            assert key in d
