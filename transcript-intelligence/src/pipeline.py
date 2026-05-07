"""
LLM enrichment pipeline — processes each transcript and extracts structured BI.

Why LLM-based over clustering/rule-based:
  - The dataset is small (100 transcripts), making statistical clustering noisy
  - Topic labels need to be business-meaningful, not just co-occurrence clusters
  - The summary.json already gives us sentence-level sentiment; LLM adds intent/urgency layers
  - gpt-4o-mini is fast and cheap enough to process 100 transcripts in < 2 minutes

We use the pre-existing summary as context in the prompt to ground the extraction —
this avoids hallucination and keeps costs low (summary is ~5x shorter than full transcript).
"""

import json
import os

from src.llm import call_llm

ENRICHED_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "enriched.json")

SYSTEM_PROMPT = """You are a business intelligence analyst specializing in B2B SaaS.
You extract structured insights from call transcript summaries.
Always return valid JSON matching the exact schema requested.
Be precise, business-focused, and concise."""

EXTRACTION_PROMPT = """Analyze this call transcript and return a JSON object with exactly these fields:

{{
  "topic": "<primary business topic in 2-4 words, e.g. 'Pricing Negotiation', 'Outage Response', 'Feature Request'>",
  "sub_topic": "<more specific sub-topic, e.g. 'Annual Renewal Pricing', 'Pipeline Failure Root Cause'>",
  "sentiment": "<one of: positive / neutral / mixed / negative>",
  "emotion": "<dominant emotion: frustrated / concerned / satisfied / anxious / neutral / optimistic / angry>",
  "urgency": "<one of: low / medium / high / critical>",
  "intent": "<caller's primary intent: reporting_issue / seeking_renewal / requesting_feature / escalating / planning / reviewing / onboarding / compliance_check>",
  "key_entities": ["list", "of", "key", "product_names", "company_names", "technical_terms"],
  "churn_risk": "<one of: none / low / medium / high>",
  "summary": "<2-sentence executive summary of what happened and what matters>"
}}

Call Type: {call_type}
Title: {title}
Duration: {duration} minutes
Existing Sentiment Score (1-5): {sentiment_score}
Existing Topics: {existing_topics}

Summary:
{summary}

Key Moments:
{key_moments}"""


def format_key_moments(moments: list) -> str:
    if not moments:
        return "None"
    lines = []
    for m in moments:
        lines.append(f"- [{m.get('type', '')}] {m.get('text', '')}")
    return "\n".join(lines)


def enrich_transcript(transcript: dict) -> dict:
    user_prompt = EXTRACTION_PROMPT.format(
        call_type=transcript["call_type"],
        title=transcript["title"],
        duration=transcript["duration_minutes"],
        sentiment_score=transcript.get("sentiment_score", "N/A"),
        existing_topics=", ".join(transcript.get("existing_topics", [])),
        summary=transcript["summary"],
        key_moments=format_key_moments(transcript.get("key_moments", [])),
    )
    extraction = call_llm(SYSTEM_PROMPT, user_prompt)
    return {**transcript, **extraction}


def run_pipeline(transcripts: list[dict], verbose: bool = True) -> list[dict]:
    enriched = []
    total = len(transcripts)
    for i, t in enumerate(transcripts):
        if verbose:
            print(f"[{i+1}/{total}] Enriching: {t['title'][:60]}")
        try:
            result = enrich_transcript(t)
            enriched.append(result)
        except Exception as e:
            print(f"  ERROR: {e} — skipping")
            enriched.append({**t, "topic": "Unknown", "sentiment": "neutral",
                             "urgency": "low", "emotion": "neutral",
                             "intent": "unknown", "key_entities": [],
                             "churn_risk": "none", "sub_topic": "Unknown",
                             "summary": t.get("summary", "")})
    return enriched


def save_enriched(enriched: list[dict], path: str = ENRICHED_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"Saved {len(enriched)} enriched transcripts to {path}")


def load_enriched(path: str = ENRICHED_PATH) -> list[dict]:
    with open(path) as f:
        return json.load(f)
