"""
Semantic retrieval layer: sentence-transformers embeddings + FAISS index.

First run builds the index from enriched.json (free, local, ~2s for 100 docs).
Subsequent runs load from disk in milliseconds.
Scales to ~1M vectors before needing a distributed store.
"""

from __future__ import annotations
import json
import os

BASE_DIR   = os.path.dirname(os.path.dirname(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "outputs", "faiss.index")
META_PATH  = os.path.join(BASE_DIR, "outputs", "faiss_meta.json")
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_index = None
_meta: list[dict] = []


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _transcript_text(t: dict) -> str:
    """Concatenate the most semantically rich fields for embedding."""
    return (
        f"{t.get('title', '')}. "
        f"{t.get('summary', '')} "
        f"Topic: {t.get('topic', '')}. "
        f"Emotion: {t.get('emotion', '')}. "
        f"Intent: {t.get('intent', '')}."
    )


def build_index(
    enriched: list[dict],
    index_path: str = INDEX_PATH,
    meta_path: str = META_PATH,
) -> None:
    """Embed all transcripts and persist a FAISS flat index to disk."""
    import faiss  # imported lazily so the rest of the app works without faiss

    model = _get_model()
    texts = [_transcript_text(t) for t in enriched]

    print(f"  Building embeddings for {len(texts)} transcripts ({MODEL_NAME})…")
    vecs = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    vecs = vecs.astype("float32")

    # IndexFlatIP on L2-normalised vectors == cosine similarity
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)

    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)

    meta = [
        {
            "id":        t.get("id", ""),
            "title":     t.get("title", ""),
            "summary":   t.get("summary", ""),
            "topic":     t.get("topic"),
            "sentiment": t.get("sentiment"),
            "urgency":   t.get("urgency"),
            "call_type": t.get("call_type"),
        }
        for t in enriched
    ]
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    # Invalidate in-memory cache so next search reloads from new files
    global _index, _meta
    _index, _meta = None, []

    print(f"  FAISS index saved → {index_path}  ({len(enriched)} vectors)")


def load_index(
    index_path: str = INDEX_PATH,
    meta_path: str = META_PATH,
) -> tuple:
    """Load index + metadata from disk. Returns (index, meta) or (None, [])."""
    global _index, _meta
    if _index is None:
        if not os.path.exists(index_path):
            return None, []
        import faiss
        _index = faiss.read_index(index_path)
        with open(meta_path) as f:
            _meta = json.load(f)
    return _index, _meta


def search(
    query: str,
    top_k: int = 8,
    index_path: str = INDEX_PATH,
    meta_path: str = META_PATH,
) -> list[dict]:
    """
    Return the top-k transcript metadata records most semantically similar to query.
    Each result includes a 'score' (cosine similarity, higher = more relevant).
    """
    index, meta = load_index(index_path, meta_path)
    if index is None or not meta:
        return []

    model = _get_model()
    qvec = model.encode([query], normalize_embeddings=True).astype("float32")
    scores, indices = index.search(qvec, min(top_k, len(meta)))

    return [
        {**meta[int(idx)], "score": float(score)}
        for score, idx in zip(scores[0], indices[0])
        if 0 <= int(idx) < len(meta)
    ]
