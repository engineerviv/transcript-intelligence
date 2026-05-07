"""
LangGraph ReAct agent for transcript Q&A.

Replaces the naive "dump-all-transcripts-in-context" approach with a proper
retrieval-augmented agent that:
  1. Chooses which tool to call based on the question
  2. Retrieves only the most semantically relevant transcripts via FAISS
  3. Falls back to aggregate stats for trend/distribution questions
  4. Streams tokens as they are generated

Tools
-----
search_transcripts   — semantic FAISS search over transcript summaries
get_statistics       — aggregated stats (sentiment, urgency, churn, topics)
get_account_details  — lookup by account/company name
"""

from __future__ import annotations
import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.embeddings import search as semantic_search

# Module-level data store — initialised once by the API on startup
_enriched:   list[dict] = []
_aggregated: dict = {}


def init(enriched: list[dict], aggregated: dict) -> None:
    """Populate module state with pipeline outputs."""
    global _enriched, _aggregated
    _enriched   = enriched
    _aggregated = aggregated


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def search_transcripts(query: str, top_k: int = 6) -> str:
    """
    Search for call transcripts relevant to a specific query using semantic similarity.
    Use this for questions about specific issues, complaints, accounts, or topics.
    Returns summaries and key metadata for the most relevant calls.
    """
    results = semantic_search(query, top_k=top_k)
    if not results:
        return "No relevant transcripts found in the FAISS index."

    id_to_full = {t["id"]: t for t in _enriched}
    lines = []
    for r in results:
        t = id_to_full.get(r["id"], r)
        actions = "; ".join(t.get("action_items", [])[:3]) or "none"
        lines.append(
            f"• [{t.get('title')}]  "
            f"({t.get('call_type')} | sentiment:{t.get('sentiment')} | "
            f"urgency:{t.get('urgency')} | churn:{t.get('churn_risk')})  "
            f"similarity={r['score']:.2f}\n"
            f"  Summary: {t.get('summary', '')}\n"
            f"  Action items: {actions}"
        )
    return "\n\n".join(lines)


@tool
def get_statistics(category: str = "all") -> str:
    """
    Retrieve aggregated statistics about all transcripts.
    category options: 'sentiment', 'urgency', 'churn', 'topics', 'insights', 'all'.
    Use this for trend questions, distribution questions, or executive summaries.
    """
    if not _aggregated:
        return "Aggregated stats not available."

    def _fmt(label: str, data: object) -> str:
        return f"{label}:\n{json.dumps(data, indent=2)}"

    sections: dict[str, object] = {
        "sentiment": _aggregated.get("sentiment_distribution", {}),
        "urgency":   _aggregated.get("urgency_distribution", {}),
        "churn":     {
            "distribution":  _aggregated.get("churn_risk_distribution", {}),
            "at_risk_accounts": _aggregated.get("churn_risk_accounts", [])[:5],
        },
        "topics":    {
            "top_topics":         _aggregated.get("topic_frequency", [])[:10],
            "top_negative_topics": _aggregated.get("top_negative_topics", [])[:5],
        },
        "insights":  _aggregated.get("executive_insights", {}),
    }

    if category in sections:
        return _fmt(category, sections[category])

    return "\n\n".join(_fmt(k, v) for k, v in sections.items())


@tool
def get_account_details(account_name: str) -> str:
    """
    Retrieve all calls associated with a specific account or company name.
    Use this when asked about a particular client, company, or account.
    """
    q = account_name.lower()
    matches = [
        t for t in _enriched
        if q in (
            t.get("title", "")
            + " ".join(t.get("key_entities") or [])
            + t.get("summary", "")
        ).lower()
    ]
    if not matches:
        return f"No records found mentioning '{account_name}'."

    lines = []
    for t in matches[:6]:
        lines.append(
            f"• [{t['title']}]  "
            f"{t.get('call_type')} | {t.get('sentiment')} | "
            f"urgency:{t.get('urgency')} | churn:{t.get('churn_risk')}\n"
            f"  {t.get('summary', '')}"
        )
    return f"Found {len(matches)} record(s) for '{account_name}':\n\n" + "\n\n".join(lines)


# ── Agent factory ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert business analyst with access to {n} customer call transcripts \
from AegisCloud's B2B SaaS platform.

Always use your tools to retrieve data before answering — never guess.
- For specific issues, accounts, or topics → use search_transcripts
- For trends, distributions, or summaries → use get_statistics
- For a named company or account → use get_account_details

Be concise and cite transcript titles when relevant. \
When the question has multiple parts, call the right tool for each part.\
"""


def _build_agent(n_transcripts: int):
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
    tools = [search_transcripts, get_statistics, get_account_details]
    system = SYSTEM_PROMPT.format(n=n_transcripts)
    return create_react_agent(model, tools=tools, state_modifier=system)


def stream_agent_response(
    question: str,
    enriched: list[dict],
    aggregated: dict,
    history: list[dict] | None = None,
):
    """
    Generator that yields text chunks of the agent's streamed answer.
    Filters out tool-call artifacts; yields only the final human-readable tokens.
    """
    init(enriched, aggregated)
    agent = _build_agent(len(enriched))

    # Build message history
    messages: list = []
    if history:
        for h in history:
            cls = HumanMessage if h["role"] == "user" else AIMessage
            messages.append(cls(content=h["content"]))
    messages.append(HumanMessage(content=question))

    # stream_mode="messages" yields (chunk, metadata) tuples
    for chunk, metadata in agent.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        # Only emit text tokens from the agent node (not tool results)
        if (
            metadata.get("langgraph_node") == "agent"
            and isinstance(chunk.content, str)
            and chunk.content
        ):
            yield chunk.content
