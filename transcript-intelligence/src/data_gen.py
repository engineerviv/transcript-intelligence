"""
Loads the raw dataset from disk and normalizes it into data/transcripts.json.

Each folder contains: meeting-info.json, summary.json, transcript.json, speaker-meta.json.
We infer call_type from the meeting title because the dataset has no explicit type field:
  - "Support Case #..." -> support
  - "Aegis / <Company> ..." -> external
  - everything else (All Hands, Sprint Planning, Outage, etc.) -> internal
"""

import json
import os
import re

from src.utils import load_json

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dataset")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "transcripts.json")


def infer_call_type(title: str) -> str:
    t = title.lower()
    if t.startswith("support case"):
        return "support"
    if re.match(r"^aegis\s*/\s*", t):
        return "external"
    return "internal"


def build_full_transcript_text(transcript_data: dict) -> str:
    entries = transcript_data.get("data", [])
    lines = [f"{e['speaker_name']}: {e['sentence']}" for e in entries if e.get("sentence")]
    return "\n".join(lines)


def load_all_transcripts(dataset_dir: str = DATASET_DIR) -> list[dict]:
    transcripts = []
    folders = sorted(
        f for f in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, f))
    )
    for folder in folders:
        base = os.path.join(dataset_dir, folder)
        try:
            meeting = load_json(os.path.join(base, "meeting-info.json"))
            summary = load_json(os.path.join(base, "summary.json"))
            transcript_raw = load_json(os.path.join(base, "transcript.json"))
            speaker_meta = load_json(os.path.join(base, "speaker-meta.json"))
        except FileNotFoundError as e:
            print(f"Skipping {folder}: {e}")
            continue

        title = meeting.get("title", "")
        call_type = infer_call_type(title)
        full_text = build_full_transcript_text(transcript_raw)

        # Sentence-level sentiments for richer analysis
        sentences = transcript_raw.get("data", [])
        sentiment_counts = {}
        for s in sentences:
            st = s.get("sentimentType", "neutral")
            sentiment_counts[st] = sentiment_counts.get(st, 0) + 1

        record = {
            "id": folder,
            "title": title,
            "call_type": call_type,
            "organizer": meeting.get("organizerEmail", ""),
            "start_time": meeting.get("startTime", ""),
            "duration_minutes": round(meeting.get("duration", 0), 1),
            "participants": meeting.get("allEmails", []),
            "num_speakers": len(speaker_meta),
            # Pre-extracted by dataset provider — used as ground truth baseline
            "summary": summary.get("summary", ""),
            "action_items": summary.get("actionItems", []),
            "existing_topics": summary.get("topics", []),
            "overall_sentiment": summary.get("overallSentiment", ""),
            "sentiment_score": summary.get("sentimentScore", None),
            "key_moments": summary.get("keyMoments", []),
            "sentence_sentiment_counts": sentiment_counts,
            "full_transcript": full_text,
            "num_sentences": len(sentences),
        }
        transcripts.append(record)

    return transcripts


def save_transcripts(transcripts: list[dict], output_path: str = OUTPUT_PATH):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcripts, f, indent=2)
    print(f"Saved {len(transcripts)} transcripts to {output_path}")


if __name__ == "__main__":
    data = load_all_transcripts()
    save_transcripts(data)
    call_type_counts = {}
    for t in data:
        ct = t["call_type"]
        call_type_counts[ct] = call_type_counts.get(ct, 0) + 1
    print("Call type distribution:", call_type_counts)
