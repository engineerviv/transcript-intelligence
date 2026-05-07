# Transcript Intelligence Platform — Design Document

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [End-to-End Data Flow](#3-end-to-end-data-flow)
4. [Backend — Python Layer](#4-backend--python-layer)
   - 4.1 [Dataset Ingestion — `src/data_gen.py`](#41-dataset-ingestion--srcdatagенpy)
   - 4.2 [LLM Client — `src/llm.py`](#42-llm-client--srcllmpy)
   - 4.3 [Enrichment Pipeline — `src/pipeline.py`](#43-enrichment-pipeline--srcpipelinepy)
   - 4.4 [Aggregation Engine — `src/analysis.py`](#44-aggregation-engine--srcanalysispy)
   - 4.5 [Semantic Retrieval — `src/embeddings.py`](#45-semantic-retrieval--srcembeddingspy)
   - 4.6 [LLM Output Validation — `src/validation.py`](#46-llm-output-validation--srcvalidationpy)
   - 4.7 [LangGraph Agent — `src/agent.py`](#47-langgraph-agent--srcagentpy)
   - 4.8 [Shared Utilities — `src/utils.py`](#48-shared-utilities--srcutilspy)
   - 4.9 [Pipeline Runner — `run_pipeline.py`](#49-pipeline-runner--runpipelinepy)
   - 4.10 [FastAPI Server — `api/main.py`](#410-fastapi-server--apimainpy)
5. [Frontend — React/TypeScript Layer](#5-frontend--reacttypescript-layer)
   - 5.1 [Entry Points — `main.tsx` & `App.tsx`](#51-entry-points--maintsx--apptsx)
   - 5.2 [Type Definitions — `types/index.ts`](#52-type-definitions--typesindexts)
   - 5.3 [API Client — `lib/api.ts`](#53-api-client--libapits)
   - 5.4 [Utilities — `lib/utils.ts`](#54-utilities--libutilsts)
   - 5.5 [Global Filter State — `context/FilterContext.tsx`](#55-global-filter-state--contextfiltercontexttsx)
   - 5.6 [Data Hooks — `hooks/`](#56-data-hooks--hooks)
   - 5.7 [Layout Shell — `components/layout/`](#57-layout-shell--componentslayout)
   - 5.8 [UI Primitives — `components/ui/`](#58-ui-primitives--componentsui)
   - 5.9 [Dashboard Charts — `components/dashboard/`](#59-dashboard-charts--componentsdashboard)
   - 5.10 [Dashboard Page — `pages/Dashboard.tsx`](#510-dashboard-page--pagesdashboardtsx)
   - 5.11 [Explorer Page — `pages/Explorer.tsx`](#511-explorer-page--pagesexplorertsx)
   - 5.12 [Insights Page — `pages/Insights.tsx`](#512-insights-page--pagesinsightstsx)
   - 5.13 [Chat Widget — `components/chat/ChatWidget.tsx`](#513-chat-widget--componentschatchatwidgettsx)
6. [Test Suite](#6-test-suite)
7. [Configuration Files](#7-configuration-files)
8. [Key Design Decisions](#8-key-design-decisions)
9. [Scalability Considerations](#9-scalability-considerations)
10. [Running the Application](#10-running-the-application)

---

## 1. System Overview

Transcript Intelligence is a full-stack AI analytics platform that ingests 100 raw B2B SaaS call recordings, enriches them with structured metadata using a Large Language Model, and surfaces the results through an interactive dashboard with three views and a conversational AI assistant.

The system is split into two independently runnable services:

| Service | Technology | Port |
|---|---|---|
| Backend API | Python · FastAPI · LangGraph | 8000 |
| Frontend UI | React · TypeScript · Vite · Tailwind | 5173 |

The backend also exposes an offline pipeline (not a web service) that must be run once before the API starts.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          DATASET (raw)                          │
│  dataset/<uuid>/  meeting-info.json · summary.json              │
│                   transcript.json · speaker-meta.json           │
└────────────────────────────┬────────────────────────────────────┘
                             │  run_pipeline.py
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OFFLINE PIPELINE                            │
│                                                                 │
│  Step 1  data_gen.py       normalize 100 folders                │
│                            → data/transcripts.json             │
│                                                                 │
│  Step 2  pipeline.py       LLM enrichment (GPT-4o-mini)         │
│          llm.py            per-transcript, SHA-256 cache        │
│                            → outputs/enriched.json             │
│                                                                 │
│  Step 3  validation.py     schema + consistency checks          │
│                            → printed ValidationReport          │
│                                                                 │
│  Step 4  analysis.py       statistical aggregation              │
│                            + LLM executive insights             │
│                            → outputs/aggregated.json           │
│                                                                 │
│  Step 5  embeddings.py     sentence-transformers + FAISS        │
│                            → outputs/faiss.index               │
│                            → outputs/faiss_meta.json           │
└────────────────────────────┬────────────────────────────────────┘
                             │  loaded at startup
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│                                                                 │
│  GET  /api/health                                               │
│  GET  /api/transcripts      filter · search · paginate         │
│  GET  /api/transcripts/{id} full record including transcript    │
│  GET  /api/aggregated       all statistics + insights           │
│  GET  /api/validation       live validation report              │
│  POST /api/chat/stream      LangGraph agent SSE stream          │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP / SSE (proxied by Vite dev server)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                               │
│                                                                 │
│  Dashboard     KPIs · charts · at-risk accounts table          │
│  Explorer      searchable transcript list + detail panel        │
│  Insights      executive insight cards + heatmap               │
│  ChatWidget    floating SSE-streaming LangGraph chat            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Data Flow

Understanding how a piece of data moves from raw recording folder to a rendered chart is the clearest way to understand the system.

### 3.1 Offline pipeline (run once)

```
dataset/01KQ.../
  meeting-info.json   ─┐
  summary.json          ├─► data_gen.load_all_transcripts()
  transcript.json       │     infers call_type from title
  speaker-meta.json   ─┘     concatenates speaker turns into full_transcript
                       │
                       ▼  data/transcripts.json  (100 normalised records)
                       │
                       ▼  pipeline.run_pipeline()
                            for each transcript:
                              build prompt from summary + key_moments
                              call gpt-4o-mini with JSON mode
                              merge returned fields into record
                              cache result by SHA-256(prompt)
                       │
                       ▼  outputs/enriched.json  (100 records + AI fields)
                       │    topic, sub_topic, sentiment, emotion,
                       │    urgency, intent, key_entities, churn_risk,
                       │    summary (rewritten), sentiment_score preserved
                       │
                       ▼  validation.validate_enriched()
                            checks enums, ranges, cross-field rules
                       │
                       ▼  analysis.aggregate()
                            compute_topic_frequency()
                            compute_sentiment_distribution()
                            compute_urgency_distribution()
                            compute_churn_risk_distribution()
                            compute_sentiment_by_call_type()
                            compute_churn_risk_accounts()
                            compute_avg_sentiment_score_by_type()
                            compute_top_negative_topics()
                            compute_high_urgency_topics()
                            compute_intent_distribution()
                            compute_emotion_distribution()
                            generate_executive_insights() ← LLM call
                       │
                       ▼  outputs/aggregated.json  (all stats + insights)
                       │
                       ▼  embeddings.build_index()
                            SentenceTransformer('all-MiniLM-L6-v2')
                            encode title + summary + topic + emotion
                            normalize to unit vectors
                            faiss.IndexFlatIP (cosine similarity)
                       │
                       ▼  outputs/faiss.index + outputs/faiss_meta.json
```

### 3.2 API request (runtime)

```
Browser                     FastAPI                      Files / FAISS
  │                            │                              │
  │ GET /api/transcripts        │                              │
  │ ?call_type=support          │                              │
  │ &sentiment=negative         │──── filter _enriched list   │
  │ &search=billing             │──── text search (title,     │
  │                             │     summary, topic)         │
  │                             │──── strip full_transcript   │
  │◄── {transcripts, total} ───│                              │
  │                             │                              │
  │ GET /api/transcripts/{id}   │──── lookup by id            │
  │◄── full record ────────────│     (full_transcript included)│
  │                             │                              │
  │ POST /api/chat/stream       │                              │
  │ {question, history}         │                              │
  │                             │── agent.stream_agent_response│
  │                             │     LangGraph ReAct loop:   │
  │                             │     agent → pick tool →     │
  │                             │       search_transcripts    │
  │                             │         embeddings.search() │
  │                             │         → FAISS query ──────►
  │                             │◄── top-K metadata ─────────│
  │                             │       get_statistics        │
  │                             │         → _aggregated dict  │
  │                             │       get_account_details   │
  │                             │         → filter _enriched  │
  │                             │     agent → compose answer  │
  │◄── SSE: data: {"text":"…"} │     stream tokens           │
  │◄── SSE: data: [DONE]  ─────│                              │
```

### 3.3 Frontend data flow

```
App.tsx
  └─ QueryClientProvider (TanStack Query — 5 min stale time)
  └─ FilterProvider (global call_type / sentiment / urgency state)
  └─ BrowserRouter
       └─ Layout
            └─ FilterBar  ─► reads/writes FilterContext
            └─ Outlet
                 ├─ Dashboard
                 │    └─ useAggregated()  ─► GET /api/aggregated
                 │    └─ useTranscripts() ─► GET /api/transcripts (no filter)
                 │                           merges FilterContext
                 ├─ Explorer
                 │    └─ useTranscripts(local overrides)
                 │    └─ useTranscript(selectedId) ─► GET /api/transcripts/{id}
                 └─ Insights
                      └─ useAggregated()
       └─ ChatWidget  (always mounted, outside routes)
            └─ POST /api/chat/stream  ─► ReadableStream SSE consumer
```

---

## 4. Backend — Python Layer

### 4.1 Dataset Ingestion — `src/data_gen.py`

**Purpose:** Normalize the raw dataset (100 folders, each with 4–6 JSON files) into a single flat array of transcript records.

**Key functions:**

`infer_call_type(title)` — The dataset has no explicit call type field. This function uses title pattern matching:
- Titles starting with `"Support Case #..."` → `"support"`
- Titles matching `"Aegis / <Company Name>"` → `"external"` (customer-facing calls)
- Everything else (All Hands, Sprint Planning, Outage Response, etc.) → `"internal"`

`build_full_transcript_text(transcript_data)` — Concatenates all speaker turns from `transcript.json` into a single string in the format `"SpeakerName: sentence"`. This produces the `full_transcript` field that the Explorer page can display.

`load_all_transcripts(dataset_dir)` — Iterates every folder, loads all JSON files, and assembles one record per call. The resulting record preserves pre-extracted fields from the dataset provider (their own NLP: `summary`, `action_items`, `key_moments`, `sentiment_score`) and adds our structural fields. These provider-extracted fields serve as a grounding baseline for our LLM enrichment.

**Output:** `data/transcripts.json` — 100 records, each ~2KB.

**Why this approach:** Rather than re-doing what the dataset provider already computed (sentence-level sentiment, action items, key moments), we keep their output and layer our own AI analysis on top. This avoids duplication, reduces cost, and lets us validate our LLM outputs against their baseline.

---

### 4.2 LLM Client — `src/llm.py`

**Purpose:** Provide a single interface to GPT-4o-mini with prompt-level caching.

**Core mechanism — prompt cache:**

Every call to `call_llm()` computes `SHA-256(system_prompt + "||" + user_prompt + "||json")`, truncated to 16 hex characters. This hash is looked up in `outputs/cache.json` before making any API call. On a cache hit, the stored result is returned immediately. On a miss, the API is called, the result is stored, and the cache is saved to disk.

This means the 100-transcript enrichment pipeline is fully idempotent. Re-running the pipeline costs $0.00 in API fees if nothing changed. This is critical for development iteration.

**Cache bypass for conversations:** The `call_llm_text()` and `call_llm_stream()` functions accept a `history` parameter. When history is present, the cache is skipped — conversation responses are context-dependent and should not be cached.

**JSON mode:** Enrichment calls use `response_format={"type": "json_object"}` which forces GPT-4o-mini to emit valid JSON. This eliminates the need for regex post-processing or error recovery from malformed responses.

**Retry logic:** `_call()` retries up to 3 times with exponential backoff (1s, 2s) on any exception. This handles transient OpenAI API errors without failing the entire pipeline.

**Model choice rationale:** GPT-4o-mini costs approximately $0.15 per million input tokens. Processing 100 transcript summaries (avg ~500 tokens each) costs roughly $0.017 total — cheap enough to treat as disposable.

---

### 4.3 Enrichment Pipeline — `src/pipeline.py`

**Purpose:** Take the 100 normalised transcripts and extract 8 structured AI fields from each one using GPT-4o-mini.

**What gets extracted:**

| Field | Type | Example |
|---|---|---|
| `topic` | string | `"Pricing Negotiation"` |
| `sub_topic` | string | `"Annual Renewal Discount"` |
| `sentiment` | enum | `"negative"` |
| `emotion` | string | `"frustrated"` |
| `urgency` | enum | `"high"` |
| `intent` | string | `"escalating"` |
| `key_entities` | list | `["Summit Trust", "API v2"]` |
| `churn_risk` | enum | `"medium"` |

**Prompt design:** The prompt deliberately uses the pre-extracted `summary` and `key_moments` rather than the full transcript. Summaries are ~5× shorter than transcripts, reducing token usage while retaining the semantic content needed for classification. The `key_moments` field (churn signals, technical issues, positive pivots) provides particularly strong signal for urgency and churn risk prediction.

**Error handling:** If enrichment fails for a record (API error, malformed JSON), the transcript is kept with safe fallback values (`topic: "Unknown"`, `sentiment: "neutral"`, etc.) rather than crashing the pipeline. This ensures all 100 transcripts are always present in outputs.

**`enrich_transcript(transcript)`** merges the LLM-returned dict with the original transcript dict using `{**transcript, **extraction}`. This means LLM fields overlay any pre-existing fields of the same name (e.g., the LLM rewrites `summary` with a more executive-focused version), while all original fields are preserved.

---

### 4.4 Aggregation Engine — `src/analysis.py`

**Purpose:** Compute all statistical distributions from the enriched transcripts, and generate a single LLM-powered executive insights block.

**Statistical functions (all pure, no LLM):**

- `compute_topic_frequency()` — `Counter` over `topic` field, sorted descending, top 15
- `compute_sentiment_distribution()` — counts + percentage per sentiment value
- `compute_sentiment_by_call_type()` — nested dict: `{call_type: {sentiment: count}}`; feeds the stacked bar chart and the heatmap
- `compute_urgency_distribution()` — counts + percentage per urgency level
- `compute_churn_risk_distribution()` — raw counts per risk level
- `compute_top_negative_topics()` — topics appearing in negative or mixed sentiment calls
- `compute_high_urgency_topics()` — topics in high or critical urgency calls
- `compute_intent_distribution()` — counts per intent label
- `compute_emotion_distribution()` — counts per emotion label
- `compute_avg_sentiment_score_by_type()` — mean of numeric `sentiment_score` per call type
- `compute_churn_risk_accounts()` — filters external calls with medium or high churn risk, sorts high before medium; feeds the at-risk table

**`generate_executive_insights()`** — Makes a single LLM call with all statistical summaries as context to generate five structured lists: key insights, operational risks, churn indicators, customer pain points, and recommendations. These appear on the Insights page. The LLM is given the numerical data, not raw transcripts, so the output is grounded in aggregated truth rather than individual anecdotes.

**`_extract_account_name(title)`** — Parses titles like `"Aegis / Summit Trust - Platform Concerns"` using a regex to extract `"Summit Trust"`. This is what populates the "Account" column in the at-risk table.

**Output:** `outputs/aggregated.json` — ~10KB of pre-computed statistics that the API serves directly.

**Why pre-compute?** The aggregated endpoint is called on every Dashboard and Insights page load. Recomputing distributions over 100 records on every request would be fast but wasteful. Pre-computing at pipeline time also ensures the dashboard and the chatbot see exactly the same numbers.

---

### 4.5 Semantic Retrieval — `src/embeddings.py`

**Purpose:** Provide fast, semantically-aware transcript retrieval for the LangGraph agent.

**Why this replaces keyword matching:** The previous chatbot scored transcripts by counting how many query keywords appeared in title/summary/topic fields. This fails for synonyms ("invoice" vs "billing"), misses context ("everything is broken" maps to urgency, not a keyword), and has no notion of relevance ordering beyond raw match counts. Embedding-based retrieval finds transcripts that are semantically related to the question even when no exact words overlap.

**Model:** `all-MiniLM-L6-v2` from `sentence-transformers`. This model:
- Runs entirely locally — no API cost, no latency from network calls
- Produces 384-dimensional embeddings
- Is fine-tuned for semantic similarity tasks (not just next-token prediction)
- Downloads once (~90MB) and is cached by the library

**Index:** FAISS `IndexFlatIP` (Flat Inner Product). When vectors are L2-normalised before indexing (which `normalize_embeddings=True` does), inner product equals cosine similarity. `IndexFlatIP` does exact search — no approximation — which is appropriate for 100 vectors. At 10,000+ vectors you would switch to `IndexIVFFlat` or `IndexHNSWFlat` for approximate nearest-neighbour search.

**`_transcript_text(t)`** — The text fed to the encoder concatenates `title + summary + topic + emotion + intent`. This creates a richer semantic fingerprint than using summary alone, because topic and emotion act as strong discriminative signals.

**`build_index(enriched)`** — Called in Step 5 of the pipeline. Encodes all transcripts, adds to FAISS, writes index to `outputs/faiss.index`. Also writes a lightweight `outputs/faiss_meta.json` containing only the 7 fields needed at search time (id, title, summary, topic, sentiment, urgency, call_type) — not the full records. The agent then uses these IDs to look up full records from the in-memory `_enriched` list.

**`search(query, top_k)`** — Encodes the query string, performs a single FAISS search, returns top-k results with cosine similarity scores. The module-level `_index` and `_meta` are cached after the first call to avoid re-reading from disk on every query.

**Scalability:** At 1M vectors, `IndexFlatIP` would take ~400MB and each search would take ~50ms (vs ~0.1ms for 100 vectors). The natural upgrade path is `IndexIVFFlat` (clustering-based approximate search, <5ms at 1M) or a hosted vector store (Pinecone, Weaviate, Qdrant) for distributed deployments.

---

### 4.6 LLM Output Validation — `src/validation.py`

**Purpose:** Catch data quality problems in the LLM's enrichment output before those problems propagate to the dashboard and chatbot.

**Why this matters:** LLMs can produce outputs that look valid but aren't. Examples seen in practice:
- `sentiment: "POSITIVE"` (wrong case) — breaks all enum comparisons
- `urgency: "urgent"` (not in our schema) — the dashboard bucketing would silently drop it
- `sentiment_score: 0.8` (model confused 0–1 scale with our 1–5 scale)
- `churn_risk: "high"` with `sentiment: "positive"` — logically suspicious, worth flagging

**Errors vs Warnings:**
- **Errors** are definitive schema violations that would break downstream logic: missing required fields, values not in enum sets, non-numeric score fields, wrong collection types
- **Warnings** are logically suspicious but not necessarily wrong: unrecognised emotion labels (model invented a new one), cross-field inconsistencies (high churn + positive sentiment), missing optional enriched fields

**`validate_record(t, idx)`** returns `(errors, warnings)` for a single transcript. Pure function — no I/O, easy to test in isolation.

**`validate_enriched(enriched)`** runs all records, builds a `ValidationReport` dataclass with error and warning dicts keyed by record ID. Exposed as `GET /api/validation` so operators can check data quality without re-running the pipeline.

**`print_report(report)`** produces a human-readable summary with sample errors, called by `run_pipeline.py` so every pipeline run surfaces validation issues immediately.

---

### 4.7 LangGraph Agent — `src/agent.py`

**Purpose:** Replace the naive "dump all transcripts in one giant prompt" chatbot with a reasoning agent that selects and uses tools to retrieve exactly the information needed to answer each question.

**Agent architecture — ReAct loop:**

```
User question
      │
      ▼
┌─────────────────────────────────────────────┐
│               LangGraph ReAct Agent          │
│                                             │
│  Agent node (GPT-4o-mini)                   │
│    - reads question + conversation history  │
│    - decides: call a tool, or answer        │
│         │                                   │
│         ▼                                   │
│  Tool node                                  │
│    - executes chosen tool                   │
│    - returns result as ToolMessage          │
│         │                                   │
│         ▼                                   │
│  Agent node again                           │
│    - reads tool result                      │
│    - decides: call another tool, or answer  │
│         │                                   │
│  (loops until agent emits final answer)     │
└──────────────┬──────────────────────────────┘
               │ stream_mode="messages"
               ▼
      Text tokens (SSE)
```

**Three tools:**

`search_transcripts(query, top_k=6)` — Calls `embeddings.search()` to retrieve the top-K semantically similar transcripts. Enriches results with full records from the in-memory `_enriched` list (FAISS meta only stores 7 fields). Formats output as readable bullet points including title, call_type, sentiment, urgency, churn_risk, summary, and action items. Used for questions about specific issues, complaints, or accounts.

`get_statistics(category)` — Returns pre-computed aggregated stats from `_aggregated`. Accepts a category argument (`"sentiment"`, `"urgency"`, `"churn"`, `"topics"`, `"insights"`, `"all"`) so the agent can fetch only the relevant section rather than dumping the entire 10KB stats object into context. Used for trend questions, distribution questions, and executive summaries.

`get_account_details(account_name)` — Does a case-insensitive substring search across title, key_entities, and summary for any mention of the account name. Returns up to 6 matching calls. Handles questions like "What's happening with Summit Trust?"

**System prompt:** The agent is given a system prompt that explains its role (expert business analyst), what data it has access to (N transcripts from AegisCloud), and a routing heuristic for which tool to use for which type of question. This prevents the agent from guessing when it should search, and from doing redundant tool calls.

**Streaming:** `stream_agent_response()` calls `agent.stream()` with `stream_mode="messages"`. This yields `(chunk, metadata)` tuples where each chunk is a `BaseMessageChunk`. We filter to only yield chunks where `metadata["langgraph_node"] == "agent"` and `chunk.content` is a non-empty string. This filters out tool call parameter chunks (which have empty content) and tool result messages (which come from the "tools" node).

**State:** `_enriched` and `_aggregated` are module-level variables initialised by `init()`, which is called by `stream_agent_response()` on every invocation. The API calls `stream_agent_response()` with the full enriched and aggregated data on each chat request — there is no persistent agent state between conversations.

---

### 4.8 Shared Utilities — `src/utils.py`

**Purpose:** Thin shared helpers used across the backend.

- `load_json(path)` — UTF-8 JSON file reader used throughout the pipeline
- `outputs_ready()` — Checks whether both `enriched.json` and `aggregated.json` exist; used by the API startup handler and health endpoint to determine if the pipeline has been run
- Color helper functions (`sentiment_color`, `urgency_color`, `churn_color`) — hex color maps used by the legacy Streamlit app (not by the React frontend, which has its own)
- `badge_html()` — HTML badge renderer for Streamlit (legacy)

---

### 4.9 Pipeline Runner — `run_pipeline.py`

**Purpose:** Orchestrate all five pipeline steps in sequence from a single entry point.

**The five steps:**

```
Step 1  Load dataset         data_gen.load_all_transcripts()
        (skip if cached)     → data/transcripts.json

Step 2  LLM enrichment       pipeline.run_pipeline()
        (per-item cached)    → outputs/enriched.json

Step 3  Validate outputs     validation.validate_enriched()
        (always runs)        → prints ValidationReport to console

Step 4  Aggregate            analysis.aggregate()
        (always runs)        saves prior run for KPI delta tracking
                             → outputs/aggregated.json
                             → outputs/prior_aggregated.json

Step 5  Build FAISS index    embeddings.build_index()
        (always runs)        → outputs/faiss.index
                             → outputs/faiss_meta.json
```

**Idempotency:** Steps 1 and 2 are safe to re-run. Step 1 checks for `data/transcripts.json` existence before re-loading. Step 2 uses the prompt hash cache so already-enriched transcripts are returned from disk without an API call.

**KPI delta tracking:** Before overwriting `aggregated.json` in Step 4, the existing file is copied to `prior_aggregated.json`. The frontend's KPI cards can display deltas (e.g., `↑ 3 vs last run`) by comparing the current and prior aggregated files. This is used when the pipeline is re-run after new call data arrives.

---

### 4.10 FastAPI Server — `api/main.py`

**Purpose:** Expose the pipeline outputs as a REST API consumed by the React frontend.

**Startup:** The `@app.on_event("startup")` handler loads `enriched.json` and `aggregated.json` into module-level lists `_enriched` and `_aggregated` when the server starts. All requests read from these in-memory structures — no file I/O per request.

**CORS:** Configured to allow origins `http://localhost:5173` (Vite dev server) and `http://localhost:3000`. In production this would be replaced with the deployed frontend URL.

**Endpoints:**

`GET /api/health` — Returns `{"status": "ok", "pipeline_ready": bool, "transcript_count": int}`. The frontend can use this to show a "pipeline not ready" banner if outputs don't exist.

`GET /api/transcripts` — The most complex endpoint. Accepts query parameters:
- `call_type`, `sentiment`, `urgency` — comma-separated multi-value filters (e.g., `?call_type=support,external`)
- `date_from`, `date_to` — ISO date strings for time range filtering
- `search` — full-text substring search across title, summary, and topic
- `limit` / `offset` — pagination (default limit 100, max 500)

Crucially, `full_transcript` is stripped from every record in the list response. The full transcript field averages ~8KB per record. Returning it for 100 records would be ~800KB per list request — wasteful for a list view that never displays it.

`GET /api/transcripts/{id}` — Returns the full record including `full_transcript`. Only called when the user clicks a row in the Explorer.

`GET /api/aggregated` — Returns the entire `_aggregated` dict. This is the data source for all dashboard charts, KPI cards, and the Insights page.

`GET /api/validation` — Runs `validate_enriched(_enriched)` on demand and returns the report as JSON. Useful for operators to check data quality without re-running the pipeline.

`POST /api/chat/stream` — Accepts `{"question": str, "history": [{"role": str, "content": str}]}`. Calls `stream_agent_response()` and wraps the generator in a `StreamingResponse` with `media_type="text/event-stream"`. Each chunk is emitted as `data: {"text": "..."}\n\n`. The stream ends with `data: [DONE]\n\n`. The `X-Accel-Buffering: no` header disables nginx proxy buffering so tokens reach the browser immediately.

---

## 5. Frontend — React/TypeScript Layer

### 5.1 Entry Points — `main.tsx` & `App.tsx`

**`main.tsx`** — The Vite entry point. Mounts the React app into `<div id="root">` using React 19's `createRoot`. Wraps everything in `StrictMode` for development-time checks.

**`App.tsx`** — The application root. Sets up four nested providers and the router:

```tsx
<QueryClientProvider>      // TanStack Query — manages all server state
  <FilterProvider>          // Global filter state across pages
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>   // Persistent shell
          <Route index → Dashboard />
          <Route /explorer → Explorer />
          <Route /insights → Insights />
        </Route>
      </Routes>
      <ChatWidget />         // Outside Routes — always mounted
    </BrowserRouter>
  </FilterProvider>
</QueryClientProvider>
```

`ChatWidget` is rendered outside `<Routes>` so it persists and retains conversation history when the user navigates between pages.

**TanStack Query config:** `staleTime: 5 * 60 * 1000` (5 minutes). Data fetched from the API is considered fresh for 5 minutes — navigating between pages does not trigger redundant API calls. This matches the immutable nature of the pipeline outputs (they don't change unless the pipeline is re-run).

---

### 5.2 Type Definitions — `types/index.ts`

**Purpose:** Single source of truth for all data shapes used across the frontend.

All TypeScript types mirror the JSON structures returned by the API. Key types:

- `Transcript` — the full record shape including all enriched fields and the optional `full_transcript`
- `AggregatedStats` — the shape of `GET /api/aggregated`, including nested types for all distribution maps
- `ExecutiveInsights` — the five string arrays in `aggregated.executive_insights`
- `AtRiskAccount` — a row in the at-risk accounts table
- `ChatMessage` — `{role: 'user' | 'assistant', content: string}` used by the chat widget
- `Filters` — the global filter state shape: `callTypes[], sentiments[], urgencies[], dateFrom, dateTo, search`

Having all types in one file means type errors surface at compile time rather than runtime, and refactoring the API response shape produces compile errors everywhere the field is used.

---

### 5.3 API Client — `lib/api.ts`

**Purpose:** Typed wrapper around `fetch` so no component ever constructs a raw URL.

**`get<T>(path)`** — Generic typed fetch helper. Throws on non-2xx responses with the response body as the error message.

**`buildQuery(filters)`** — Converts a `TranscriptFilters` object to a URL query string. Handles multi-value arrays (`callTypes` → `call_type=support,external`), omits empty/undefined values.

**`api.chatStream(question, history)`** — Returns a `ReadableStream<string>`. This is the most complex function in the file. It:
1. Creates a `ReadableStream` and captures the controller
2. Fires a `fetch()` to `POST /api/chat/stream` asynchronously
3. Reads the response body as chunks via `res.body.getReader()`
4. Uses a line buffer to reassemble SSE `data: {...}\n\n` frames that may arrive split across chunks
5. Parses each `data:` line as JSON, extracts `text`
6. Enqueues text into the ReadableStream
7. Closes the stream on `[DONE]` sentinel or error

The consumer (ChatWidget) gets a `ReadableStream<string>` and calls `reader.read()` in a loop, appending each string to the displayed message. This produces the typewriter streaming effect.

---

### 5.4 Utilities — `lib/utils.ts`

**Purpose:** Shared constants and formatting functions.

- `cn(...classes)` — Merges Tailwind classes using `clsx` + `tailwind-merge`. Handles conditional classes and deduplication (important when combining base + variant classes)
- `SENTIMENT_COLORS`, `URGENCY_COLORS`, `CHURN_COLORS` — Hex color maps used by Recharts
- `SENTIMENT_BG`, `URGENCY_BG`, `CHURN_BG` — Tailwind ring-color classes used by Badge components
- `formatDuration(minutes)` — Converts `25.5` → `"25m"`
- `formatDate(isoString)` — Converts `"2024-03-01T10:00:00Z"` → `"Mar 1, 2024"`

---

### 5.5 Global Filter State — `context/FilterContext.tsx`

**Purpose:** Share filter state between the FilterBar (which modifies it) and every data-fetching hook (which reads it).

The context holds a `Filters` object with `callTypes`, `sentiments`, `urgencies`, `dateFrom`, `dateTo`, and `search`. The default state has all call types and all sentiments selected (i.e., no filtering).

`setFilters(partial)` merges a partial update — callers only specify what they're changing.

`resetFilters()` restores the default.

`isDefault` is derived by JSON-comparing current state to default — used by FilterBar to conditionally show the Reset button.

**Why global state for filters?** The Dashboard, Explorer, and Insights pages all respond to the same filter selection. Without a shared context, each page would independently manage filter state and they'd be out of sync. The FilterBar in the header modifies the context; the data hooks read from it.

---

### 5.6 Data Hooks — `hooks/`

**`useAggregated.ts`** — Wraps `api.aggregated()` in a TanStack Query `useQuery` with key `['aggregated']`. Because aggregated data never changes at runtime (only when the pipeline re-runs), the stale time could be infinity. It's set to 5 minutes for consistency.

**`useTranscripts.ts`** exports two hooks:

`useTranscripts(extra?)` — Reads filters from `FilterContext`, merges any `extra` overrides from the caller (Explorer uses this to add its own local search and filter controls on top of the global filters), then calls `api.transcripts(mergedFilters)`. The query key includes the serialised filters so TanStack Query re-fetches when any filter changes.

`useTranscript(id)` — Fetches a single full transcript. The `enabled: !!id` option means the query only fires when `id` is non-null — it's dormant until a row is clicked in the Explorer.

---

### 5.7 Layout Shell — `components/layout/`

**`Sidebar.tsx`** — Fixed left sidebar (224px wide, `w-56`). Contains the TI logo mark, three `NavLink` items using React Router's `NavLink` which automatically applies the active style when the current path matches. The sidebar is always visible; the main content is offset by `ml-56`.

**`FilterBar.tsx`** — Renders three `ToggleGroup` components for call type, sentiment, and urgency. Each toggle group shows colored pills; active filters have the pill background colored using inline styles with hex color + opacity suffix (`#22c55e33` = green at 20% opacity). The Reset button appears only when `!isDefault`.

`ToggleGroup` prevents de-selecting the last item in a group (the `if (next.length > 0) onChange(next)` guard) so filters never result in zero selected values.

**`Layout.tsx`** — The React Router layout route component. Renders the Sidebar, a sticky header with the current page title and FilterBar, and an `<Outlet>` for the active page. The `TITLES` map derives the page title from `useLocation().pathname`.

---

### 5.8 UI Primitives — `components/ui/`

**`Badge.tsx`** — A small rounded-full label with `ring-1 ring-inset` border. Accepts a `className` for color variants (e.g., `SENTIMENT_BG['positive']` which is `ring-green-500/30 bg-green-500/10 text-green-400`).

**`Spinner.tsx`** — Animated border-top spinner using Tailwind's `animate-spin` with a blue top border. Accepts `className` for size override.

---

### 5.9 Dashboard Charts — `components/dashboard/`

**`KpiCard.tsx`** — Displays a large numeric/string value, a label, an optional sub-label, and an optional delta indicator. The `higherIsBad` prop inverts the color logic: for "Negative Sentiment %" a positive delta (more negative) should be red, not green.

**`Charts.tsx`** — Contains seven Recharts chart components:

`TopicsChart` — Horizontal `BarChart` (layout="vertical"). The first bar is red (worst topic by frequency), all others are blue. Accepts an `onTopicClick` callback for potential cross-filtering to Explorer.

`SentimentPie` — Donut `PieChart` with center text showing total call count. Uses `paddingAngle={2}` for a small gap between segments. The `<text>` SVG elements inside `PieChart` render the center label — this is a direct SVG injection technique specific to Recharts.

`SentimentByTypeChart` — Stacked `BarChart` with four series (one per sentiment). Each series uses `stackId="a"` so bars stack. The `radius={[4,4,0,0]}` is applied only to the topmost series ("negative") so the top of each stacked bar is rounded.

`UrgencyChart` / `ChurnRiskChart` — Simple bar charts with per-bar colors via `<Cell>`. The `label={{ position: 'top' }}` adds count labels above each bar.

`NegativeTopicsChart` — Bar chart with angled x-axis labels (`angle={-25}`) to accommodate longer topic names without overlap.

`TimelineChart` — `ScatterChart` where x = call date, y = sentiment score (1–5), color = sentiment category. Four `<Scatter>` series, one per sentiment, render as separate colored point clouds. Size of each point is constant (the `size` field in data is computed but Recharts ScatterChart doesn't vary point size without `z`-axis configuration).

---

### 5.10 Dashboard Page — `pages/Dashboard.tsx`

**Purpose:** Operational overview of all 100 transcripts at a glance.

**Data sources:** `useAggregated()` for all chart data and the at-risk table. `useTranscripts()` for the timeline chart (which needs individual transcript points) and total count.

**KPI row:** Five KpiCard components:
1. Total transcripts (from `txData.total`, responds to global filters)
2. Top issue category (first entry in `topic_frequency`)
3. Negative sentiment % = `(negative.count + mixed.count) / total * 100`
4. High urgency calls = `urgency.high.count + urgency.critical.count`
5. At-risk accounts = count of `churn_risk_accounts` where `churn_risk === "high"`

**At-risk table:** An expandable table. Clicking a row toggles an expansion row directly below it (using a `selectedAccount` state and rendering two `<tr>` elements per account inside a `<>` Fragment). The expansion shows the full title and summary.

**Loading state:** Both `aggLoading` and `txLoading` must be false before rendering. A full-page spinner is shown while either is loading. This prevents partial renders with undefined data.

---

### 5.11 Explorer Page — `pages/Explorer.tsx`

**Purpose:** Browse, search, and filter individual transcripts; view full details of any call.

**Layout:** Two-panel, fixed-height (`h-[calc(100vh-130px)]`):
- Left panel (320px, fixed): transcript list with controls
- Right panel (flex-1): detail view or empty state

**`TranscriptRow`** — A button element rendering title, truncated summary, date, duration, and up to three badges. The `selected` state is indicated by `bg-blue-950/30 border-l-2 border-l-blue-500` — a blue left border.

**Local filters** — The Explorer has its own three `<select>` dropdowns (call type, sentiment, urgency) that act as *additional* filters on top of the global FilterBar filters. They're passed as `extra` overrides to `useTranscripts()`. This means the global filter constrains the universe; the local selects narrow within it.

**CSV export** — `exportCsv()` creates a Blob URL from a manually constructed CSV string, clicks a programmatically-created `<a>` element to trigger the download, then revokes the object URL. It exports the currently-filtered transcript set, not all 100.

**`DetailPanel`** — Appears when a row is clicked. Uses `useTranscript(id)` which fires a `GET /api/transcripts/{id}` request — this is the only place in the app that fetches `full_transcript`. The panel shows:
- Sticky header with title and badges
- Metadata grid (8 fields in 2 columns)
- Sentiment score progress bar: `(score - 1) / 4 * 100%` maps 1–5 to 0–100%
- Summary paragraph
- Key entities as blue chips
- Action items as bulleted list with `→` arrows
- Key moments with emoji icons per type
- Collapsible `<pre>` block for the full transcript text

---

### 5.12 Insights Page — `pages/Insights.tsx`

**Purpose:** Executive-level view of AI-generated insights and deeper analytical visualisations.

**Data source:** `useAggregated()` only. All content is derived from the pre-computed `aggregated.json`.

**Layout:**
- Row 1 (2 columns): Key Insights + Operational Risks
- Row 2 (3 columns): Churn Indicators + Pain Points + Recommendations
- Row 3 (5 columns): Heatmap (col-span-3) + Intent distribution + Emotion distribution (col-span-2)
- Row 4: High-urgency topic chips

**`InsightCard`** — Takes items from `executive_insights[key]` and renders them as a numbered list. The left border color (`accent`) and background tint (`bg`) are determined per card by `INSIGHT_CONFIG`. Includes a count badge in the top-right corner.

**`SentimentHeatmap`** — Custom HTML `<table>` (not a Recharts component). Each cell is a `div` with `backgroundColor` computed as `hex + opacity suffix`. The opacity is `intensity * 200 + 30` (mapped to hex), where intensity = `value / maxValue`. This produces a gradient from very light (low volume) to fully saturated (highest volume). Cells with zero value get a neutral dark background. The color hue per column is `SENTIMENT_COLORS[sentiment]`.

**`DistributionList`** — Renders a sorted list of distribution entries as label + progress bar + count. The bar width is `(value / max) * 100%`. An optional `colorFn` parameter lets emotion distributions use emotion-specific colors.

---

### 5.13 Chat Widget — `components/chat/ChatWidget.tsx`

**Purpose:** Floating AI assistant that is accessible from any page, preserves conversation history, and streams responses token-by-token.

**Open/closed state:** `open` boolean controls whether the panel or the floating button is shown. The button has a green dot indicator (always visible) and the panel slides in from the bottom-right corner.

**Message state:** `messages: Message[]` where `Message = {role, content, streaming?: boolean}`. The `streaming` flag on the last assistant message controls whether to show the cursor blink. During streaming, each new token is appended to the last message's content via a functional state update.

**Sending a message:**

```
sendMessage(text)
  │
  ├── add user message to state
  ├── add empty assistant message with streaming: true
  ├── call api.chatStream(text, history)
  │     → returns ReadableStream<string>
  │
  ├── reader = stream.getReader()
  ├── loop:
  │     { done, value } = await reader.read()
  │     append value to last message content
  │     update React state (triggers re-render → user sees new tokens)
  │
  └── set streaming: false on last message (removes cursor)
```

**Conversation history:** When `sendMessage` fires, `messages` is used to build the `history` array passed to `api.chatStream()`. This is the full prior conversation sent to the backend, which passes it to LangGraph as prior `HumanMessage`/`AIMessage` turns. The agent can therefore reference earlier turns ("as I mentioned above...").

**Abort handling:** `abortRef` stores a cancel function. If the user clicks Clear mid-stream, `abortRef.current()` is called which sets a `closed` flag and calls `reader.cancel()`, stopping the stream and cleaning up state.

**Suggestion chips:** On empty state, four full suggestion buttons are shown. After the first message, two shorter chips (truncated at 28 chars) appear above the input. Both call `sendMessage(text)` directly — no need to type.

**`TypingDots`** — Three bouncing dots with staggered `animationDelay` (0ms, 150ms, 300ms) shown while the first token is being generated (streaming=true but content="").

---

## 6. Test Suite

### Structure

```
tests/
  conftest.py         shared fixtures (3 sample transcripts)
  test_validation.py  38 tests — validation logic
  test_analysis.py    27 tests — aggregation functions
  test_retrieval.py   24 tests — FAISS index and search
  test_api.py         15 tests — FastAPI endpoints
```

### `conftest.py`

Defines `SAMPLE_ENRICHED`: three representative transcripts (support/negative/high-urgency, external/positive/none-churn, internal/neutral/medium-urgency). Used as fixtures by all four test files. The variety in call types, sentiments, and urgencies ensures all filter/aggregation paths are exercised.

### `test_validation.py`

Pure unit tests — no I/O, no mocks. Tests cover:
- Valid records produce no errors
- Each invalid enum value for each field produces the correct error
- All valid enum values pass
- Out-of-range and non-numeric `sentiment_score`
- Wrong types for list fields (`key_entities`, `action_items`)
- All five cross-field consistency rules (high churn + positive, critical urgency + positive, sentiment/score mismatches)
- `validate_enriched()` aggregate counts and `to_dict()` structure

### `test_analysis.py`

Unit tests for all 11 aggregation functions. Tests verify:
- Correct field values (counts, averages, ordering)
- Edge cases (empty input, records missing score fields)
- Sorting (high before medium in churn risk accounts, topics sorted descending)
- Exclusion logic (negative topics don't include positive records; high urgency excludes medium)

### `test_retrieval.py`

Tests for `embeddings.build_index()` and `embeddings.search()` with FAISS and `sentence-transformers` fully mocked. The mock model's `encode()` function uses `numpy.random.default_rng(seed=0)` for deterministic fake embeddings. The mock FAISS module replaces the real one in `sys.modules` using `patch.dict(sys.modules, {"faiss": mock_faiss})` to prevent any C extension from loading. Tests verify: file creation, metadata correctness, result count, score presence, and graceful empty return when no index exists.

### `test_api.py`

FastAPI `TestClient` tests. The startup event is patched with `patch("api.main.outputs_ready", return_value=False)` so it skips file loading; test data is injected directly into the module-level `_enriched` and `_aggregated` variables after the client context opens. Tests cover all six endpoints, filter combinations, pagination, `full_transcript` stripping in list view vs inclusion in detail view, and SSE format in the chat endpoint.

**Running the tests:**
```bash
python -m pytest transcript-intelligence/tests/ -v
```
All 104 tests pass. No OpenAI credentials or model downloads required.

---

## 7. Configuration Files

### `transcript-intelligence/requirements.txt`

| Package | Purpose |
|---|---|
| `openai` | GPT-4o-mini API — enrichment, executive insights, agent LLM |
| `fastapi` + `uvicorn` | REST API server |
| `python-multipart` | Multipart form parsing (FastAPI dependency) |
| `python-dotenv` | Loads `OPENAI_API_KEY` from `.env` file |
| `tiktoken` | Token counting (used in Streamlit legacy app) |
| `sentence-transformers` | Local embedding model (`all-MiniLM-L6-v2`) |
| `faiss-cpu` | Vector similarity index |
| `langgraph` | ReAct agent graph orchestration |
| `langchain-core` | LangChain message types and tool decorator |
| `langchain-openai` | `ChatOpenAI` LLM wrapper for LangGraph |
| `pytest` + `httpx` | Test runner and HTTP test client |

### `frontend/vite.config.ts`

Two key settings:
- `resolve.alias: { "@": "./src" }` — enables `@/` import shorthand throughout the frontend
- `server.proxy: { "/api": "http://localhost:8000" }` — proxies all `/api/*` requests from the Vite dev server to the FastAPI backend, eliminating CORS issues during development and allowing the frontend to use `/api/...` paths without hardcoding a backend URL

### `frontend/tailwind.config.js`

Extends Tailwind with four custom semantic color tokens:
- `surface: '#1e293b'` — card backgrounds (Slate-800)
- `border: '#334155'` — dividers (Slate-700)
- `muted: '#64748b'` — secondary text (Slate-500)
- `subtle: '#94a3b8'` — tertiary text (Slate-400)

These tokens mean every component uses consistent semantic colors rather than arbitrary hex values. Changing the card background requires one config change, not hunting through hundreds of components.

### `frontend/tsconfig.app.json`

Key settings beyond the Vite template:
- `"baseUrl": "."` + `"paths": { "@/*": ["./src/*"] }` — enables TypeScript to resolve `@/` imports (the Vite alias handles bundling; tsconfig handles type checking)
- `"ignoreDeprecations": "6.0"` — suppresses the TypeScript 6 deprecation warning for `baseUrl`
- `"noUnusedLocals": true` + `"noUnusedParameters": true` — enforces that all declared variables and parameters are used; prevents dead code accumulation

---

## 8. Key Design Decisions

### Why GPT-4o-mini for enrichment instead of a local model?

For a batch job on 100 transcripts, GPT-4o-mini costs ~$0.017 total and runs in under 2 minutes. A local model (e.g., Ollama + Llama 3) would require downloading 4–8GB, be slower on CPU, and produce lower-quality JSON extraction. The caching layer means the API cost is paid once.

### Why use summaries rather than full transcripts for LLM enrichment?

Transcript summaries are pre-provided by the dataset and average ~300 tokens. Full transcripts average ~3000 tokens. Sending full transcripts for enrichment would cost 10× more and provide marginal improvement for the classification task (topic, sentiment, urgency) since the summary already captures the semantically important content. The `key_moments` field (also pre-extracted) provides the high-signal churn and escalation signals.

### Why FAISS instead of a vector database?

At 100 vectors, FAISS is dramatically simpler: no server to run, no credentials to manage, just two files on disk. The `IndexFlatIP` provides exact nearest-neighbour search. For a production system at 10K+ transcripts, the upgrade path is clear: swap `IndexFlatIP` for `IndexIVFFlat` for approximate search at the same API, or adopt a managed vector store. The interface is identical from the application's perspective.

### Why LangGraph instead of a direct LLM call?

A direct LLM call with all 100 transcripts in context works for 100 transcripts (8K tokens comfortably fits in GPT-4o-mini's 128K context window). But it has three problems:
1. It doesn't scale — at 1000 transcripts it breaks
2. It's expensive — every question sends ~40K tokens regardless of relevance
3. The model must process irrelevant information, reducing answer quality

The LangGraph agent retrieves only relevant context (top 6 transcripts via FAISS), picks the right data source per question type, and can make multiple tool calls for multi-part questions. This is architecturally correct for production AI systems.

### Why TanStack Query instead of useEffect + useState?

TanStack Query handles caching, deduplication, background refresh, loading/error states, and stale-while-revalidate automatically. Without it, each page would implement its own fetch lifecycle, likely fetching the same aggregated data multiple times as the user navigates. With it, `/api/aggregated` is fetched once and shared across Dashboard, Insights, and the chat widget for 5 minutes.

### Why Server-Sent Events instead of WebSockets for streaming?

SSE is unidirectional (server → client), which is exactly what token streaming requires. WebSockets are bidirectional and require stateful connection management. SSE works over standard HTTP/1.1, is automatically reconnected by the browser, and is trivially handled by FastAPI's `StreamingResponse`. The trade-off is that SSE can't send binary data, but text tokens are always UTF-8 strings.

---

## 9. Scalability Considerations

### Current limitations and upgrade paths

| Component | Current approach | Bottleneck at scale | Production upgrade |
|---|---|---|---|
| Transcript storage | JSON files on disk | Not queryable; slow at >10K | PostgreSQL or MongoDB |
| Embedding index | FAISS in-memory flat | >1M vectors: slow search | Pinecone / Weaviate / Qdrant |
| Pipeline execution | Single-threaded serial | 100 transcripts = 2 min; 10K = 200 min | Celery + Redis task queue |
| LLM enrichment caching | SHA-256 on disk | Single machine only | Redis or a SQL cache table |
| API server | Single uvicorn worker | ~100 req/s max | Gunicorn multi-worker + load balancer |
| Frontend state | All data in memory | 100K transcripts in list = OOM | Server-side pagination already implemented |

### What already scales

- **Pagination:** `GET /api/transcripts` has `limit`/`offset` parameters. The Explorer fetches only the current page.
- **Detail-on-demand:** `full_transcript` is only fetched when a row is clicked, not returned in list responses.
- **FAISS search:** Query time is O(N) but extremely fast in practice — 1M vectors in ~50ms on CPU. For 100K transcripts the current setup requires no changes.
- **Stateless API:** The FastAPI server holds no session state; horizontal scaling is trivial.

---

## 10. Running the Application

### Prerequisites
- Python 3.11+ with `.venv` virtual environment
- Node.js 18+ with npm
- `OPENAI_API_KEY` in `.env` at project root

### One-time pipeline setup

```bash
cd take-home-assignment
source .venv/bin/activate
python transcript-intelligence/run_pipeline.py
```

Steps 2 (LLM enrichment) and 5 (FAISS index) will run on first execution. Subsequent runs skip Step 2 via the prompt cache.

### Running the app

**Terminal 1 — Backend:**
```bash
cd take-home-assignment
source .venv/bin/activate
uvicorn transcript-intelligence.api.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd take-home-assignment/frontend
npm run dev
```

Open **http://localhost:5173**

### Running the tests

```bash
cd take-home-assignment
source .venv/bin/activate
python -m pytest transcript-intelligence/tests/ -v
```

### Validating LLM outputs standalone

```bash
source .venv/bin/activate
python -m transcript-intelligence.src.validation transcript-intelligence/outputs/enriched.json
```
