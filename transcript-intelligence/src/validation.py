"""
LLM output validation.

Validates enriched transcripts against expected schemas, enum values,
numeric ranges, and cross-field consistency rules.
Run standalone:  python -m src.validation
"""

from __future__ import annotations
from dataclasses import dataclass, field

VALID_SENTIMENTS = {"positive", "neutral", "mixed", "negative"}
VALID_URGENCIES  = {"low", "medium", "high", "critical"}
VALID_CALL_TYPES = {"support", "external", "internal"}
VALID_CHURN      = {"none", "low", "medium", "high"}
VALID_EMOTIONS   = {
    "frustrated", "satisfied", "neutral", "anxious",
    "confused", "happy", "disappointed", "concerned", "angry", "excited",
}

REQUIRED_FIELDS = ["id", "title", "call_type", "sentiment", "urgency", "topic", "summary"]
ENRICHED_FIELDS = ["topic", "sentiment", "urgency", "churn_risk", "emotion", "intent",
                   "key_entities", "sentiment_score", "summary"]


@dataclass
class ValidationReport:
    total:  int = 0
    valid:  int = 0
    errors: dict[str, list[str]] = field(default_factory=dict)
    warnings: dict[str, list[str]] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(len(v) for v in self.errors.values())

    @property
    def warning_count(self) -> int:
        return sum(len(v) for v in self.warnings.values())

    @property
    def valid_pct(self) -> float:
        return round(self.valid / max(self.total, 1) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "total":         self.total,
            "valid":         self.valid,
            "valid_pct":     self.valid_pct,
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "errors":        self.errors,
            "warnings":      self.warnings,
        }


def validate_record(t: dict, idx: int) -> tuple[list[str], list[str]]:
    """
    Returns (errors, warnings) for a single transcript.
    Errors = definite data quality problems.
    Warnings = suspicious but not necessarily wrong.
    """
    errors: list[str] = []
    warnings: list[str] = []
    label = f"[{idx}:{t.get('id', '?')}]"

    # ── Required fields present ───────────────────────────────────────────────
    for f in REQUIRED_FIELDS:
        if not t.get(f):
            errors.append(f"{label} Missing required field: '{f}'")

    # ── Enum validation ───────────────────────────────────────────────────────
    checks = [
        ("sentiment",  VALID_SENTIMENTS),
        ("urgency",    VALID_URGENCIES),
        ("call_type",  VALID_CALL_TYPES),
        ("churn_risk", VALID_CHURN),
    ]
    for field_name, valid_set in checks:
        val = t.get(field_name)
        if val and val not in valid_set:
            errors.append(
                f"{label} Invalid {field_name}='{val}'. "
                f"Expected one of: {sorted(valid_set)}"
            )

    if t.get("emotion") and t["emotion"] not in VALID_EMOTIONS:
        warnings.append(
            f"{label} Unrecognised emotion='{t['emotion']}'. "
            f"Known values: {sorted(VALID_EMOTIONS)}"
        )

    # ── Numeric ranges ────────────────────────────────────────────────────────
    score = t.get("sentiment_score")
    if score is not None:
        if not isinstance(score, (int, float)):
            errors.append(f"{label} sentiment_score must be numeric, got {type(score).__name__}")
        elif not (1 <= score <= 5):
            errors.append(f"{label} sentiment_score={score} out of expected range [1, 5]")

    # ── Type checks ───────────────────────────────────────────────────────────
    if "key_entities" in t and not isinstance(t["key_entities"], list):
        errors.append(f"{label} key_entities must be a list")
    if "action_items" in t and not isinstance(t["action_items"], list):
        errors.append(f"{label} action_items must be a list")

    # ── Cross-field consistency ───────────────────────────────────────────────
    sentiment = t.get("sentiment")
    churn     = t.get("churn_risk")
    urgency   = t.get("urgency")
    score_val = t.get("sentiment_score")

    if churn == "high" and sentiment == "positive":
        warnings.append(
            f"{label} Suspicious: churn_risk=high but sentiment=positive"
        )
    if urgency == "critical" and sentiment == "positive":
        warnings.append(
            f"{label} Suspicious: urgency=critical but sentiment=positive"
        )
    if score_val is not None and isinstance(score_val, (int, float)):
        if sentiment == "positive" and score_val < 3:
            warnings.append(
                f"{label} Inconsistency: sentiment=positive but score={score_val} (below neutral)"
            )
        if sentiment == "negative" and score_val > 3:
            warnings.append(
                f"{label} Inconsistency: sentiment=negative but score={score_val} (above neutral)"
            )

    # ── Enrichment completeness ───────────────────────────────────────────────
    missing_enriched = [f for f in ENRICHED_FIELDS if t.get(f) is None]
    if missing_enriched:
        warnings.append(
            f"{label} Missing enriched fields: {missing_enriched}"
        )

    return errors, warnings


def validate_enriched(enriched: list[dict]) -> ValidationReport:
    """Validate all records and return an aggregate ValidationReport."""
    report = ValidationReport(total=len(enriched))

    for i, t in enumerate(enriched):
        errs, warns = validate_record(t, i)
        rec_id = t.get("id", f"record_{i}")
        if errs:
            report.errors[rec_id] = errs
        else:
            report.valid += 1
        if warns:
            report.warnings[rec_id] = warns

    return report


def print_report(report: ValidationReport) -> None:
    print("\n" + "=" * 55)
    print("  Validation Report")
    print("=" * 55)
    print(f"  Total records : {report.total}")
    print(f"  Valid         : {report.valid}  ({report.valid_pct}%)")
    print(f"  With errors   : {len(report.errors)}")
    print(f"  With warnings : {len(report.warnings)}")

    if report.errors:
        print(f"\n  Errors (first 5 records):")
        for rec_id, errs in list(report.errors.items())[:5]:
            for e in errs:
                print(f"    ✗ {e}")

    if report.warnings:
        print(f"\n  Warnings (first 5 records):")
        for rec_id, warns in list(report.warnings.items())[:5]:
            for w in warns:
                print(f"    ⚠  {w}")
    print("=" * 55)


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json as _json
    path = sys.argv[1] if len(sys.argv) > 1 else "outputs/enriched.json"
    with open(path) as f:
        data = _json.load(f)
    report = validate_enriched(data)
    print_report(report)
