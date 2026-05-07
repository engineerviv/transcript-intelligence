"""Shared helpers used across the app and pipeline."""

import json
import os


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sentiment_color(sentiment: str) -> str:
    return {
        "positive": "#22c55e",
        "neutral": "#94a3b8",
        "mixed": "#f59e0b",
        "negative": "#ef4444",
    }.get(sentiment, "#94a3b8")


def urgency_color(urgency: str) -> str:
    return {
        "low": "#22c55e",
        "medium": "#f59e0b",
        "high": "#f97316",
        "critical": "#dc2626",
    }.get(urgency, "#94a3b8")


def churn_color(risk: str) -> str:
    return {
        "none": "#22c55e",
        "low": "#84cc16",
        "medium": "#f59e0b",
        "high": "#ef4444",
    }.get(risk, "#94a3b8")


def badge_html(label: str, value: str, color: str) -> str:
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'padding:3px 10px;border-radius:999px;font-size:0.8rem;font-weight:600;">'
        f'{label}: {value}</span>'
    )


def outputs_ready() -> bool:
    base = os.path.join(os.path.dirname(__file__), "..", "outputs")
    return (
        os.path.exists(os.path.join(base, "enriched.json"))
        and os.path.exists(os.path.join(base, "aggregated.json"))
    )
