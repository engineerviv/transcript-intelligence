"""
Entry point for the full pipeline.

Run: python run_pipeline.py

Steps:
  1. Load raw dataset           -> data/transcripts.json
  2. LLM enrichment             -> outputs/enriched.json  (cached, safe to re-run)
  3. Validate LLM outputs       -> prints ValidationReport
  4. Aggregation + LLM insights -> outputs/aggregated.json
  5. Build FAISS index          -> outputs/faiss.index + faiss_meta.json
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.data_gen import load_all_transcripts, save_transcripts
from src.pipeline import run_pipeline, save_enriched, load_enriched
from src.analysis import aggregate, save_aggregated
from src.validation import validate_enriched, print_report
from src.embeddings import build_index
from src.utils import load_json

DATASET_DIR      = os.path.join(os.path.dirname(__file__), "..", "dataset")
TRANSCRIPTS_PATH = os.path.join(os.path.dirname(__file__), "data", "transcripts.json")
ENRICHED_PATH    = os.path.join(os.path.dirname(__file__), "outputs", "enriched.json")
AGGREGATED_PATH  = os.path.join(os.path.dirname(__file__), "outputs", "aggregated.json")


def main():
    print("=" * 60)
    print("Transcript Intelligence Platform — Pipeline")
    print("=" * 60)

    # Step 1: Load and normalise dataset (skip if already done)
    print("\n[Step 1] Loading dataset…")
    if os.path.exists(TRANSCRIPTS_PATH):
        print(f"  transcripts.json already exists — loading from cache")
        transcripts = load_json(TRANSCRIPTS_PATH)
    else:
        transcripts = load_all_transcripts(DATASET_DIR)
        save_transcripts(transcripts, TRANSCRIPTS_PATH)
    call_types: dict = {}
    for t in transcripts:
        ct = t["call_type"]
        call_types[ct] = call_types.get(ct, 0) + 1
    print(f"  Loaded {len(transcripts)} transcripts: {call_types}")

    # Step 2: LLM enrichment (cached per-transcript)
    print("\n[Step 2] Running LLM enrichment pipeline…")
    print("  (Results cached — repeated runs skip API calls)")
    enriched = run_pipeline(transcripts, verbose=True)
    save_enriched(enriched, ENRICHED_PATH)

    # Step 3: Validate LLM outputs
    print("\n[Step 3] Validating LLM outputs…")
    report = validate_enriched(enriched)
    print_report(report)
    if report.error_count > 0:
        print(f"  ⚠  {report.error_count} validation error(s) found — review above.")
    else:
        print("  ✓  All records passed validation.")

    # Step 4: Aggregation + executive insights
    print("\n[Step 4] Aggregating insights…")
    if os.path.exists(AGGREGATED_PATH):
        import shutil
        prior_path = os.path.join(os.path.dirname(AGGREGATED_PATH), "prior_aggregated.json")
        shutil.copy2(AGGREGATED_PATH, prior_path)
        print("  Saved prior aggregated stats for delta tracking")
    stats = aggregate(enriched)
    save_aggregated(stats, AGGREGATED_PATH)

    # Step 5: Build FAISS semantic index
    print("\n[Step 5] Building FAISS semantic index…")
    build_index(enriched)

    print("\n" + "=" * 60)
    print("Pipeline complete. Start the API with:")
    print("  uvicorn api.main:app --reload --port 8000")
    print("=" * 60)


if __name__ == "__main__":
    main()
