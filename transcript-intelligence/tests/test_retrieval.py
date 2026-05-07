"""
Tests for src/embeddings.py — FAISS index build and semantic search.

Both sentence-transformers and faiss are fully mocked at the sys.modules
level so no native C extensions run during tests.
"""
import os
import sys
import json
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import src.embeddings as emb_module


# ── Mock helpers ──────────────────────────────────────────────────────────────

DIM = 16  # embedding dimension used across all mocks


def _make_mock_model():
    """Deterministic fake encoder: same seed → same vectors."""
    mock = MagicMock()

    def encode(texts, show_progress_bar=False, normalize_embeddings=False):
        rng = np.random.default_rng(seed=0)
        vecs = rng.random((len(texts), DIM)).astype("float32")
        if normalize_embeddings:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs /= np.clip(norms, 1e-10, None)
        return vecs

    mock.encode.side_effect = encode
    return mock


def _make_mock_faiss(n_vectors: int = 0):
    """
    Minimal FAISS mock that stores added vectors and supports search.
    Returns (mock_faiss_module, mock_index).
    """
    stored = {"vecs": None}

    mock_index = MagicMock()

    def add(vecs):
        stored["vecs"] = vecs

    def search(qvec, k):
        actual_n = len(stored["vecs"]) if stored["vecs"] is not None else n_vectors
        k = min(k, actual_n)
        scores  = np.ones((1, k), dtype="float32") * 0.8
        indices = np.arange(k, dtype="int64").reshape(1, -1)
        return scores, indices

    mock_index.add.side_effect = add
    mock_index.search.side_effect = search

    mock_faiss = MagicMock()
    mock_faiss.IndexFlatIP.return_value = mock_index
    mock_faiss.write_index = MagicMock()
    mock_faiss.read_index.return_value = mock_index

    return mock_faiss, mock_index


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_module_cache():
    """Reset in-memory singletons and remove any faiss import from sys.modules."""
    emb_module._model = None
    emb_module._index = None
    emb_module._meta  = []
    yield
    emb_module._model = None
    emb_module._index = None
    emb_module._meta  = []


@pytest.fixture
def tmp_index(tmp_path):
    return str(tmp_path / "test.index"), str(tmp_path / "test_meta.json")


# ── build_index ───────────────────────────────────────────────────────────────

class TestBuildIndex:
    def _run_build(self, enriched, index_path, meta_path):
        mock_model = _make_mock_model()
        mock_faiss, _ = _make_mock_faiss(len(enriched))
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            emb_module.build_index(enriched, index_path, meta_path)

    def test_creates_meta_file(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        self._run_build(sample_enriched, index_path, meta_path)
        assert os.path.exists(meta_path)

    def test_meta_record_count_matches_input(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        self._run_build(sample_enriched, index_path, meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert len(meta) == len(sample_enriched)

    def test_meta_contains_required_fields(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        self._run_build(sample_enriched, index_path, meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        for record in meta:
            for field in ["id", "title", "summary", "topic", "sentiment", "urgency", "call_type"]:
                assert field in record, f"Field '{field}' missing from meta record"

    def test_meta_ids_match_input(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        self._run_build(sample_enriched, index_path, meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert {r["id"] for r in meta} == {t["id"] for t in sample_enriched}

    def test_faiss_write_index_called(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model = _make_mock_model()
        mock_faiss, _ = _make_mock_faiss(len(sample_enriched))
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            emb_module.build_index(sample_enriched, index_path, meta_path)
        mock_faiss.write_index.assert_called_once()

    def test_model_encode_called_with_all_texts(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model = _make_mock_model()
        mock_faiss, _ = _make_mock_faiss(len(sample_enriched))
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            emb_module.build_index(sample_enriched, index_path, meta_path)
        call_args = mock_model.encode.call_args
        texts_encoded = call_args[0][0]
        assert len(texts_encoded) == len(sample_enriched)

    def test_in_memory_cache_cleared_after_build(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        # Pre-set stale cache
        emb_module._index = MagicMock()
        emb_module._meta  = [{"id": "stale"}]
        mock_model = _make_mock_model()
        mock_faiss, _ = _make_mock_faiss(len(sample_enriched))
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            emb_module.build_index(sample_enriched, index_path, meta_path)
        assert emb_module._index is None
        assert emb_module._meta  == []


# ── search ────────────────────────────────────────────────────────────────────

class TestSearch:
    def _setup(self, enriched, index_path, meta_path):
        """Build meta file then directly inject mock index into module state.

        faiss.write_index is mocked so no file is written for the index —
        we bypass load_index and inject the mock directly so search() works.
        """
        mock_model = _make_mock_model()
        mock_faiss, mock_index = _make_mock_faiss(len(enriched))

        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            emb_module.build_index(enriched, index_path, meta_path)

        # meta_path was written (json.dump is not mocked); index path was not
        # (faiss.write_index is mocked). Inject state directly.
        with open(meta_path) as f:
            emb_module._meta  = json.load(f)
        emb_module._index = mock_index

        return mock_model, mock_faiss, mock_index

    def test_returns_correct_count(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model, mock_faiss, _ = self._setup(sample_enriched, index_path, meta_path)
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            results = emb_module.search("billing", top_k=2,
                                        index_path=index_path, meta_path=meta_path)
        assert len(results) == 2

    def test_top_k_capped_at_index_size(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model, mock_faiss, _ = self._setup(sample_enriched, index_path, meta_path)
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            results = emb_module.search("query", top_k=999,
                                        index_path=index_path, meta_path=meta_path)
        assert len(results) <= len(sample_enriched)

    def test_each_result_has_score(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model, mock_faiss, _ = self._setup(sample_enriched, index_path, meta_path)
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            results = emb_module.search("billing", top_k=2,
                                        index_path=index_path, meta_path=meta_path)
        for r in results:
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_each_result_has_metadata_fields(self, sample_enriched, tmp_index):
        index_path, meta_path = tmp_index
        mock_model, mock_faiss, _ = self._setup(sample_enriched, index_path, meta_path)
        with patch.object(emb_module, "_get_model", return_value=mock_model), \
             patch.dict(sys.modules, {"faiss": mock_faiss}):
            results = emb_module.search("billing", top_k=1,
                                        index_path=index_path, meta_path=meta_path)
        assert len(results) == 1
        for field in ["id", "title", "topic", "sentiment", "urgency"]:
            assert field in results[0], f"'{field}' missing from search result"

    def test_empty_when_index_not_built(self, tmp_index):
        index_path, meta_path = tmp_index
        # No index file → graceful empty return
        results = emb_module.search("anything", index_path=index_path, meta_path=meta_path)
        assert results == []
