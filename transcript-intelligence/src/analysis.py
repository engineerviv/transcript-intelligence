"""
Aggregation and insight engine.
Takes enriched transcripts and produces:
  - statistical summaries (topic freq, sentiment dist, urgency dist)
  - cross-cuts (sentiment by call type, topic x sentiment)
  - LLM-generated executive insights grounded in the actual data
"""

import json
import os
from collections import Counter

from src.llm import call_llm

AGGREGATED_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "aggregated.json")


# ── Statistical aggregations ──────────────────────────────────────────────────

def compute_topic_frequency(enriched: list[dict]) -> list[dict]:
    counts = Counter(t.get("topic", "Unknown") for t in enriched)
    return [{"topic": k, "count": v} for k, v in counts.most_common(15)]


def compute_sentiment_distribution(enriched: list[dict]) -> dict:
    counts = Counter(t.get("sentiment", "neutral") for t in enriched)
    total = len(enriched)
    return {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in counts.items()}


def compute_sentiment_by_call_type(enriched: list[dict]) -> dict:
    result = {}
    for t in enriched:
        ct = t.get("call_type", "unknown")
        sent = t.get("sentiment", "neutral")
        result.setdefault(ct, Counter())[sent] += 1
    return {ct: dict(counter) for ct, counter in result.items()}


def compute_urgency_distribution(enriched: list[dict]) -> dict:
    counts = Counter(t.get("urgency", "low") for t in enriched)
    total = len(enriched)
    return {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in counts.items()}


def compute_churn_risk_distribution(enriched: list[dict]) -> dict:
    counts = Counter(t.get("churn_risk", "none") for t in enriched)
    return dict(counts)


def compute_top_negative_topics(enriched: list[dict], top_n: int = 8) -> list[dict]:
    negative_topics = [
        t.get("topic", "Unknown")
        for t in enriched
        if t.get("sentiment") in ("negative", "mixed")
    ]
    counts = Counter(negative_topics)
    return [{"topic": k, "count": v} for k, v in counts.most_common(top_n)]


def compute_high_urgency_topics(enriched: list[dict]) -> list[dict]:
    urgent = [
        t.get("topic", "Unknown")
        for t in enriched
        if t.get("urgency") in ("high", "critical")
    ]
    counts = Counter(urgent)
    return [{"topic": k, "count": v} for k, v in counts.most_common(10)]


def compute_intent_distribution(enriched: list[dict]) -> dict:
    counts = Counter(t.get("intent", "unknown") for t in enriched)
    return dict(counts)


def compute_emotion_distribution(enriched: list[dict]) -> dict:
    counts = Counter(t.get("emotion", "neutral") for t in enriched)
    return dict(counts)


def compute_churn_risk_accounts(enriched: list[dict]) -> list[dict]:
    """External calls flagged high churn risk — actionable for account managers."""
    at_risk = [
        {
            "title": t["title"],
            "account": _extract_account_name(t["title"]),
            "churn_risk": t.get("churn_risk", "none"),
            "sentiment": t.get("sentiment", "neutral"),
            "urgency": t.get("urgency", "low"),
            "summary": t.get("summary", ""),
        }
        for t in enriched
        if t.get("call_type") == "external" and t.get("churn_risk") in ("medium", "high")
    ]
    risk_order = {"high": 0, "medium": 1}
    return sorted(at_risk, key=lambda x: risk_order.get(x["churn_risk"], 2))


def _extract_account_name(title: str) -> str:
    """'Aegis / Summit Trust - Platform Concerns' -> 'Summit Trust'"""
    import re
    m = re.match(r"Aegis\s*/\s*(.+?)\s*[-–]", title, re.IGNORECASE)
    return m.group(1).strip() if m else title


def compute_avg_sentiment_score_by_type(enriched: list[dict]) -> dict:
    scores: dict[str, list] = {}
    for t in enriched:
        ct = t.get("call_type", "unknown")
        score = t.get("sentiment_score")
        if score is not None:
            scores.setdefault(ct, []).append(score)
    return {ct: round(sum(v) / len(v), 2) for ct, v in scores.items()}


# ── LLM-generated executive insights ─────────────────────────────────────────

INSIGHT_SYSTEM = """You are a senior business analyst at a B2B SaaS company called AegisCloud.
You generate concise, executive-level insights from call transcript analytics.
Be direct, specific, and actionable. Return valid JSON."""

INSIGHT_PROMPT = """Based on the following aggregated analytics from {n} call transcripts,
generate executive insights.

Return a JSON object with:
{{
  "key_insights": [
    "insight 1 (specific, data-driven, 1-2 sentences)",
    "insight 2",
    "insight 3",
    "insight 4",
    "insight 5"
  ],
  "operational_risks": [
    "risk 1",
    "risk 2",
    "risk 3"
  ],
  "churn_indicators": [
    "indicator 1",
    "indicator 2",
    "indicator 3"
  ],
  "customer_pain_points": [
    "pain point 1",
    "pain point 2",
    "pain point 3",
    "pain point 4"
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2",
    "recommendation 3"
  ]
}}

Analytics data:
- Total transcripts: {n}
- Call type distribution: {call_type_dist}
- Top topics: {top_topics}
- Sentiment distribution: {sentiment_dist}
- Sentiment by call type: {sentiment_by_type}
- Urgency distribution: {urgency_dist}
- Top negative topics: {neg_topics}
- Churn risk distribution: {churn_dist}
- High urgency topics: {urgent_topics}
- Average sentiment score by call type (1=very negative, 5=very positive): {avg_scores}
- Emotion distribution: {emotion_dist}
"""


def generate_executive_insights(enriched: list[dict], stats: dict) -> dict:
    call_type_dist = Counter(t.get("call_type") for t in enriched)
    prompt = INSIGHT_PROMPT.format(
        n=len(enriched),
        call_type_dist=dict(call_type_dist),
        top_topics=[x["topic"] for x in stats["topic_frequency"][:10]],
        sentiment_dist={k: v["pct"] for k, v in stats["sentiment_distribution"].items()},
        sentiment_by_type=stats["sentiment_by_call_type"],
        urgency_dist={k: v["pct"] for k, v in stats["urgency_distribution"].items()},
        neg_topics=[x["topic"] for x in stats["top_negative_topics"]],
        churn_dist=stats["churn_risk_distribution"],
        urgent_topics=[x["topic"] for x in stats["high_urgency_topics"]],
        avg_scores=stats["avg_sentiment_score_by_type"],
        emotion_dist=stats["emotion_distribution"],
    )
    return call_llm(INSIGHT_SYSTEM, prompt)


# ── Main aggregation entry point ──────────────────────────────────────────────

def aggregate(enriched: list[dict]) -> dict:
    stats = {
        "total_transcripts": len(enriched),
        "topic_frequency": compute_topic_frequency(enriched),
        "sentiment_distribution": compute_sentiment_distribution(enriched),
        "sentiment_by_call_type": compute_sentiment_by_call_type(enriched),
        "urgency_distribution": compute_urgency_distribution(enriched),
        "churn_risk_distribution": compute_churn_risk_distribution(enriched),
        "top_negative_topics": compute_top_negative_topics(enriched),
        "high_urgency_topics": compute_high_urgency_topics(enriched),
        "intent_distribution": compute_intent_distribution(enriched),
        "emotion_distribution": compute_emotion_distribution(enriched),
        "churn_risk_accounts": compute_churn_risk_accounts(enriched),
        "avg_sentiment_score_by_type": compute_avg_sentiment_score_by_type(enriched),
    }
    print("Generating executive insights via LLM...")
    stats["executive_insights"] = generate_executive_insights(enriched, stats)
    return stats


def save_aggregated(stats: dict, path: str = AGGREGATED_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Saved aggregated insights to {path}")


def load_aggregated(path: str = AGGREGATED_PATH) -> dict:
    with open(path) as f:
        return json.load(f)
