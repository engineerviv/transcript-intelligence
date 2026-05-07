"""
FastAPI backend for Transcript Intelligence Platform.

Run:  uvicorn api.main:app --reload --port 8000
      (from the transcript-intelligence/ directory)
"""

import json
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.agent import stream_agent_response
from src.validation import validate_enriched
from src.utils import load_json, outputs_ready

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Transcript Intelligence API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data loading ──────────────────────────────────────────────────────────────

BASE_DIR        = os.path.dirname(os.path.dirname(__file__))
ENRICHED_PATH   = os.path.join(BASE_DIR, "outputs", "enriched.json")
AGGREGATED_PATH = os.path.join(BASE_DIR, "outputs", "aggregated.json")

_enriched:   list[dict] = []
_aggregated: dict = {}


@app.on_event("startup")
def load_data():
    global _enriched, _aggregated
    if outputs_ready():
        _enriched   = load_json(ENRICHED_PATH)
        _aggregated = load_json(AGGREGATED_PATH)
        print(f"Loaded {len(_enriched)} enriched transcripts.")
    else:
        print("WARNING: Pipeline outputs not found. Run python run_pipeline.py first.")


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "pipeline_ready": outputs_ready(),
        "transcript_count": len(_enriched),
    }


@app.get("/api/transcripts")
def get_transcripts(
    call_type:  Optional[str] = Query(None),
    sentiment:  Optional[str] = Query(None),
    urgency:    Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    limit:      int = Query(100, le=500),
    offset:     int = Query(0),
):
    if not _enriched:
        raise HTTPException(503, "Pipeline outputs not ready. Run run_pipeline.py first.")

    results = _enriched

    if call_type:
        types = call_type.split(",")
        results = [t for t in results if t.get("call_type") in types]
    if sentiment:
        sents = sentiment.split(",")
        results = [t for t in results if t.get("sentiment") in sents]
    if urgency:
        urgs = urgency.split(",")
        results = [t for t in results if t.get("urgency") in urgs]
    if date_from:
        results = [t for t in results if t.get("start_time", "") >= date_from]
    if date_to:
        results = [t for t in results if t.get("start_time", "") <= date_to + "Z"]
    if search:
        q = search.lower()
        results = [
            t for t in results
            if q in t.get("title", "").lower()
            or q in t.get("summary", "").lower()
            or q in t.get("topic", "").lower()
        ]

    total = len(results)
    page  = results[offset: offset + limit]

    # Strip full_transcript from list view for performance
    slim = [{k: v for k, v in t.items() if k != "full_transcript"} for t in page]
    return {"transcripts": slim, "total": total}


@app.get("/api/transcripts/{transcript_id}")
def get_transcript(transcript_id: str):
    if not _enriched:
        raise HTTPException(503, "Pipeline outputs not ready.")
    match = next((t for t in _enriched if t.get("id") == transcript_id), None)
    if not match:
        raise HTTPException(404, f"Transcript '{transcript_id}' not found.")
    return match


@app.get("/api/aggregated")
def get_aggregated():
    if not _aggregated:
        raise HTTPException(503, "Pipeline outputs not ready. Run run_pipeline.py first.")
    return _aggregated


@app.get("/api/validation")
def get_validation():
    """Run validation on the current enriched data and return the report."""
    if not _enriched:
        raise HTTPException(503, "Pipeline outputs not ready.")
    report = validate_enriched(_enriched)
    return report.to_dict()


@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest):
    if not _enriched or not _aggregated:
        raise HTTPException(503, "Pipeline outputs not ready.")

    history = [{"role": m.role, "content": m.content} for m in body.history] or None

    def generate():
        try:
            for chunk in stream_agent_response(
                body.question, _enriched, _aggregated, history=history
            ):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
