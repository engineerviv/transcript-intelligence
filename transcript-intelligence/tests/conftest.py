"""Shared pytest fixtures."""
import pytest


SAMPLE_ENRICHED = [
    {
        "id": "t001",
        "title": "Aegis / Apex Corp - Billing Issue",
        "call_type": "support",
        "organizer": "support@aegis.com",
        "start_time": "2024-03-01T10:00:00Z",
        "duration_minutes": 25,
        "num_speakers": 2,
        "summary": "Customer raised a billing discrepancy. Invoice shows double charge for March.",
        "action_items": ["Refund double charge", "Review billing system"],
        "key_moments": [],
        "sentiment_score": 2.0,
        "num_sentences": 40,
        "topic": "billing",
        "sub_topic": "overcharge",
        "sentiment": "negative",
        "emotion": "frustrated",
        "urgency": "high",
        "intent": "complaint",
        "key_entities": ["Apex Corp", "billing"],
        "churn_risk": "medium",
        "existing_topics": ["billing"],
        "overall_sentiment": "negative",
    },
    {
        "id": "t002",
        "title": "Aegis / Summit Trust - Onboarding",
        "call_type": "external",
        "organizer": "sales@aegis.com",
        "start_time": "2024-03-02T14:00:00Z",
        "duration_minutes": 45,
        "num_speakers": 3,
        "summary": "Smooth onboarding session. Customer happy with platform capabilities.",
        "action_items": ["Send API docs", "Schedule follow-up"],
        "key_moments": [],
        "sentiment_score": 4.5,
        "num_sentences": 80,
        "topic": "onboarding",
        "sub_topic": "platform_setup",
        "sentiment": "positive",
        "emotion": "satisfied",
        "urgency": "low",
        "intent": "information_request",
        "key_entities": ["Summit Trust", "API"],
        "churn_risk": "none",
        "existing_topics": ["onboarding"],
        "overall_sentiment": "positive",
    },
    {
        "id": "t003",
        "title": "Aegis / Internal - Engineering Sync",
        "call_type": "internal",
        "organizer": "eng@aegis.com",
        "start_time": "2024-03-03T09:00:00Z",
        "duration_minutes": 30,
        "num_speakers": 4,
        "summary": "Sprint planning for Q2. Team discussed API performance regression.",
        "action_items": ["Fix latency regression", "Update runbook"],
        "key_moments": [],
        "sentiment_score": 3.0,
        "num_sentences": 55,
        "topic": "technical_issue",
        "sub_topic": "performance",
        "sentiment": "neutral",
        "emotion": "neutral",
        "urgency": "medium",
        "intent": "problem_solving",
        "key_entities": ["API", "Q2"],
        "churn_risk": "none",
        "existing_topics": ["technical"],
        "overall_sentiment": "neutral",
    },
]


@pytest.fixture
def sample_enriched():
    return SAMPLE_ENRICHED


@pytest.fixture
def single_record():
    return SAMPLE_ENRICHED[0]
