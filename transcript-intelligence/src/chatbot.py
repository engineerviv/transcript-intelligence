"""
Lightweight chatbot that answers questions about the transcript dataset.

Approach: retrieval-augmented prompting without a vector DB.
  - We serialize the aggregated stats + a relevant sample of enriched transcripts as context
  - All 100 transcripts are included in every prompt (~8k tokens, well within the 128k limit)
  - Transcripts are sorted by query-keyword relevance so the most pertinent ones appear first
  - Multi-turn: prior chat turns are passed as message history so follow-ups work
  - A production version with thousands of transcripts would use embeddings + semantic search
"""

import json
import os
from src.llm import call_llm_text, call_llm_stream

SYSTEM_PROMPT = """You are an AI analyst for AegisCloud's Transcript Intelligence Platform.
You answer questions about call transcript data for business stakeholders.

Rules:
- Only use the provided data context to answer. Do not hallucinate.
- Be concise, specific, and executive-friendly.
- Cite specific numbers, topics, or accounts when relevant.
- If the context doesn't have enough information, say so honestly.
- Format responses with bullet points when listing multiple items."""

CONTEXT_TEMPLATE = """You have access to the following transcript intelligence data:

=== AGGREGATE STATS ===
{agg_summary}

=== ALL ENRICHED TRANSCRIPTS (sorted by relevance to your question) ===
{transcript_sample}

=== USER QUESTION ===
{question}

Answer the question based solely on the data above."""


def _build_agg_summary(agg: dict) -> str:
    insights = agg.get("executive_insights", {})
    lines = [
        f"Total transcripts: {agg['total_transcripts']}",
        f"Top topics: {[x['topic'] for x in agg['topic_frequency'][:8]]}",
        f"Sentiment distribution: {json.dumps({k: v['pct'] for k, v in agg['sentiment_distribution'].items()})}",
        f"Sentiment by call type: {json.dumps(agg['sentiment_by_call_type'])}",
        f"Urgency distribution: {json.dumps({k: v['pct'] for k, v in agg['urgency_distribution'].items()})}",
        f"Churn risk: {json.dumps(agg['churn_risk_distribution'])}",
        f"Top negative topics: {[x['topic'] for x in agg['top_negative_topics']]}",
        f"High urgency topics: {[x['topic'] for x in agg['high_urgency_topics']]}",
        f"Intent distribution: {json.dumps(agg.get('intent_distribution', {}))}",
        f"Emotion distribution: {json.dumps(agg.get('emotion_distribution', {}))}",
        f"Key insights: {insights.get('key_insights', [])}",
        f"Operational risks: {insights.get('operational_risks', [])}",
        f"Churn indicators: {insights.get('churn_indicators', [])}",
        f"Customer pain points: {insights.get('customer_pain_points', [])}",
        f"At-risk accounts: {[a['account'] for a in agg.get('churn_risk_accounts', [])]}",
    ]
    return "\n".join(lines)


def _score_transcript(t: dict, keywords: list[str]) -> int:
    """Return match count against question keywords for relevance ranking."""
    haystack = " ".join([
        t.get("title", ""),
        t.get("call_type", ""),
        t.get("topic", ""),
        t.get("sub_topic", ""),
        t.get("intent", ""),
        t.get("emotion", ""),
        t.get("summary", ""),
    ]).lower()
    return sum(1 for kw in keywords if kw in haystack)


def _build_transcript_sample(enriched: list[dict], question: str) -> str:
    keywords = [w.lower() for w in question.split() if len(w) > 3]

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sent_order = {"negative": 0, "mixed": 1, "neutral": 2, "positive": 3}

    scored = sorted(
        enriched,
        key=lambda x: (
            -_score_transcript(x, keywords),           # relevance first
            priority_order.get(x.get("urgency", "low"), 3),
            sent_order.get(x.get("sentiment", "neutral"), 3),
        ),
    )

    lines = []
    for t in scored:
        lines.append(
            f"[{t['call_type'].upper()}] {t['title']} | "
            f"Topic: {t.get('topic','?')} | Sentiment: {t.get('sentiment','?')} | "
            f"Urgency: {t.get('urgency','?')} | Churn Risk: {t.get('churn_risk','?')} | "
            f"Intent: {t.get('intent','?')} | Emotion: {t.get('emotion','?')}\n"
            f"  Summary: {t.get('summary','')}"
        )
    return "\n\n".join(lines)


def answer_question_stream(
    question: str,
    enriched: list[dict],
    agg: dict,
    history: list[dict] | None = None,
):
    """Generator — yields text chunks for st.write_stream."""
    agg_summary = _build_agg_summary(agg)
    transcript_sample = _build_transcript_sample(enriched, question)
    user_prompt = CONTEXT_TEMPLATE.format(
        agg_summary=agg_summary,
        transcript_sample=transcript_sample,
        question=question,
    )
    yield from call_llm_stream(SYSTEM_PROMPT, user_prompt, history=history)


def answer_question(
    question: str,
    enriched: list[dict],
    agg: dict,
    history: list[dict] | None = None,
) -> str:
    agg_summary = _build_agg_summary(agg)
    transcript_sample = _build_transcript_sample(enriched, question)
    user_prompt = CONTEXT_TEMPLATE.format(
        agg_summary=agg_summary,
        transcript_sample=transcript_sample,
        question=question,
    )
    return call_llm_text(SYSTEM_PROMPT, user_prompt, history=history)
