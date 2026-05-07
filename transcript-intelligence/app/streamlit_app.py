"""
Transcript Intelligence Platform — Streamlit Frontend (v2)

New in v2:
  - Sidebar global filters (call type, sentiment, urgency, date range)
  - Cross-filtering: click chart bars/slices to drill into Explorer
  - Timeline chart: calls over time colored by sentiment
  - Account deep-dive: click at-risk account for full call history
  - Annotated charts: worst-performing topics highlighted
  - Explorer: search box, CSV export, collapsible transcript
  - KPI metric deltas vs prior pipeline run
  - Streaming chatbot with st.chat_message
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chatbot import answer_question_stream, answer_question
from src.utils import (
    badge_html,
    churn_color,
    load_json,
    outputs_ready,
    sentiment_color,
    urgency_color,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Transcript Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0f172a; }
  [data-testid="stHeader"] { background: transparent; }
  section[data-testid="stSidebar"] { background: #1e293b; border-right: 1px solid #334155; }

  h1, h2, h3, h4 { color: #f1f5f9 !important; }
  p, li, label, span { color: #cbd5e1; }

  .kpi-card {
    background: linear-gradient(135deg, #1e293b 0%, #1a2744 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
  }
  .kpi-value { font-size: 2.2rem; font-weight: 700; color: #f1f5f9; line-height: 1.1; }
  .kpi-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;
               letter-spacing: 0.08em; margin-top: 4px; }
  .kpi-sub { font-size: 0.82rem; margin-top: 3px; }
  .kpi-delta-up { color: #ef4444; }
  .kpi-delta-down { color: #22c55e; }
  .kpi-delta-neutral { color: #94a3b8; }

  .insight-card {
    background: #1e293b;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    color: #e2e8f0;
    font-size: 0.92rem;
    line-height: 1.5;
  }
  .risk-card  { border-left-color: #ef4444; }
  .churn-card { border-left-color: #f59e0b; }
  .pain-card  { border-left-color: #a855f7; }
  .rec-card   { border-left-color: #22c55e; }

  .section-header {
    font-size: 1.3rem; font-weight: 700; color: #f1f5f9;
    margin-bottom: 4px; padding-bottom: 8px;
    border-bottom: 1px solid #334155;
  }
  .section-sub { font-size: 0.82rem; color: #64748b; margin-bottom: 20px; }

  .xf-banner {
    background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 8px;
    padding: 10px 16px; margin: 8px 0 16px 0;
    color: #93c5fd; font-size: 0.88rem;
  }

  .acct-panel {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 18px;
  }

  .transcript-box {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 16px;
    font-size: 0.85rem; color: #cbd5e1;
    max-height: 360px; overflow-y: auto;
    line-height: 1.6; white-space: pre-wrap;
    font-family: 'SF Mono', monospace;
  }

  hr { border-color: #334155; }
  .js-plotly-plot { border-radius: 10px; }
  [data-baseweb="tab-list"] { background: #1e293b !important; border-radius: 8px; }
  [data-baseweb="tab"] { color: #94a3b8 !important; }
  [aria-selected="true"] { color: #f1f5f9 !important; }
  [data-testid="stTextInput"] input {
    background: #1e293b !important; border: 1px solid #475569 !important;
    color: #f1f5f9 !important; border-radius: 8px !important;
  }
  [data-testid="stChatMessage"] { background: #1e293b; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Not-ready gate ─────────────────────────────────────────────────────────────

if not outputs_ready():
    st.markdown("""
    <div style="text-align:center;padding:80px 0;">
      <h1 style="color:#f1f5f9">🔍 Transcript Intelligence Platform</h1>
      <p style="color:#94a3b8;font-size:1.1rem">Pipeline outputs not found. Run the pipeline first:</p>
      <pre style="background:#1e293b;color:#22c55e;padding:16px;border-radius:8px;display:inline-block;">
python run_pipeline.py</pre>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Data loading ───────────────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

@st.cache_data(ttl=300)
def load_data():
    enriched = load_json(os.path.join(BASE_DIR, "outputs", "enriched.json"))
    agg = load_json(os.path.join(BASE_DIR, "outputs", "aggregated.json"))
    prior_path = os.path.join(BASE_DIR, "outputs", "prior_aggregated.json")
    prior = load_json(prior_path) if os.path.exists(prior_path) else None
    return enriched, agg, prior

enriched, agg, prior_agg = load_data()
insights = agg.get("executive_insights", {})
df = pd.DataFrame(enriched)
df["date"] = pd.to_datetime(df["start_time"], utc=True).dt.date

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔍 Transcript Intelligence")
    st.markdown("---")
    st.markdown("**Global Filters**")

    call_types_all = sorted(df["call_type"].dropna().unique().tolist())
    selected_types = st.multiselect(
        "Call Type", call_types_all, default=call_types_all, key="sb_ct"
    )

    sentiments_all = ["positive", "neutral", "mixed", "negative"]
    selected_sentiments = st.multiselect(
        "Sentiment", sentiments_all, default=sentiments_all, key="sb_sent"
    )

    urgencies_all = ["low", "medium", "high", "critical"]
    selected_urgencies = st.multiselect(
        "Urgency", urgencies_all, default=urgencies_all, key="sb_urg"
    )

    date_min = df["date"].min()
    date_max = df["date"].max()
    date_range = st.date_input(
        "Date Range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        key="sb_date",
    )

    st.markdown("---")
    n_total = len(df)

    if st.button("Reset Filters", use_container_width=True):
        for k in ["xf_topic", "xf_sentiment", "xf_account", "chat_history"]:
            st.session_state.pop(k, None)
        st.rerun()

# ── Apply global filters ───────────────────────────────────────────────────────

d_start, d_end = (date_range if len(date_range) == 2 else (date_min, date_max))

df_f = df[
    df["call_type"].isin(selected_types if selected_types else call_types_all) &
    df["sentiment"].isin(selected_sentiments if selected_sentiments else sentiments_all) &
    df["urgency"].isin(selected_urgencies if selected_urgencies else urgencies_all) &
    (df["date"] >= d_start) &
    (df["date"] <= d_end)
].copy()

enriched_f = df_f.to_dict("records")
n_filtered = len(df_f)

with st.sidebar:
    st.markdown(
        f"<div style='color:#64748b;font-size:0.8rem;text-align:center'>"
        f"Showing {n_filtered} / {n_total} transcripts</div>",
        unsafe_allow_html=True,
    )

# ── Helpers ────────────────────────────────────────────────────────────────────

PLOTLY_BASE = dict(
    paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
    font_color="#cbd5e1", margin=dict(l=10, r=10, t=40, b=10),
)


def section(title: str, sub: str = ""):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="section-sub">{sub}</div>', unsafe_allow_html=True)


def render_insight_cards(items: list, card_class: str, icon: str):
    for item in items:
        st.markdown(
            f'<div class="insight-card {card_class}">{icon} {item}</div>',
            unsafe_allow_html=True,
        )


def _kpi_delta_html(current, prior, higher_is_bad: bool = False):
    if prior is None:
        return ""
    diff = current - prior
    if diff == 0:
        cls, arrow = "kpi-delta-neutral", "→"
    elif diff > 0:
        cls = "kpi-delta-up" if higher_is_bad else "kpi-delta-down"
        arrow = "↑"
    else:
        cls = "kpi-delta-down" if higher_is_bad else "kpi-delta-up"
        arrow = "↓"
    return f'<div class="kpi-sub {cls}">{arrow} {abs(diff):.0f} vs last run</div>'


def kpi(col, value, label, delta_html=""):
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding: 24px 0 8px 0;">
  <h1 style="font-size:2rem;font-weight:800;color:#f1f5f9;margin:0;">
    🔍 Transcript Intelligence Platform
  </h1>
  <p style="color:#64748b;font-size:1rem;margin:4px 0 0 2px;">
    AI-powered intelligence extraction from enterprise conversations
  </p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ── KPI Row ────────────────────────────────────────────────────────────────────

sent_dist = dict(Counter(df_f["sentiment"]))
neg_pct = (
    sent_dist.get("negative", 0) + sent_dist.get("mixed", 0)
) / max(n_filtered, 1) * 100

urg_dist = dict(Counter(df_f["urgency"]))
high_urgency = urg_dist.get("high", 0) + urg_dist.get("critical", 0)

topic_freq = Counter(df_f["topic"]).most_common(1)
top_topic = topic_freq[0][0] if topic_freq else "N/A"

at_risk_count = len([
    a for a in agg.get("churn_risk_accounts", []) if a["churn_risk"] == "high"
])

# Deltas from prior run
prior_neg_pct, prior_high_urg, prior_at_risk = None, None, None
if prior_agg:
    p_sent = prior_agg.get("sentiment_distribution", {})
    prior_neg_pct = (
        p_sent.get("negative", {}).get("pct", 0) +
        p_sent.get("mixed", {}).get("pct", 0)
    )
    p_urg = prior_agg.get("urgency_distribution", {})
    prior_high_urg = (
        p_urg.get("high", {}).get("count", 0) +
        p_urg.get("critical", {}).get("count", 0)
    )
    prior_at_risk = len([
        a for a in prior_agg.get("churn_risk_accounts", []) if a["churn_risk"] == "high"
    ])

k1, k2, k3, k4, k5 = st.columns(5)
kpi(k1, n_filtered, "Transcripts", f'<div class="kpi-sub" style="color:#64748b">{n_total} total</div>')
kpi(k2, top_topic, "Top Issue Category")
kpi(k3, f"{neg_pct:.0f}%", "Negative Sentiment",
    _kpi_delta_html(neg_pct, prior_neg_pct, higher_is_bad=True))
kpi(k4, high_urgency, "High Urgency Calls",
    _kpi_delta_html(high_urgency, prior_high_urg, higher_is_bad=True))
kpi(k5, at_risk_count, "At-Risk Accounts",
    _kpi_delta_html(at_risk_count, prior_at_risk, higher_is_bad=True))

st.markdown("<br>", unsafe_allow_html=True)

# ── Cross-filter banner ────────────────────────────────────────────────────────

xf_topic = st.session_state.get("xf_topic")
xf_sentiment = st.session_state.get("xf_sentiment")

if xf_topic or xf_sentiment:
    parts = []
    if xf_topic:
        parts.append(f"Topic = <b>{xf_topic}</b>")
    if xf_sentiment:
        parts.append(f"Sentiment = <b>{xf_sentiment}</b>")
    filter_str = " &nbsp;+&nbsp; ".join(parts)
    col_b, col_c = st.columns([5, 1])
    col_b.markdown(
        f'<div class="xf-banner">🔗 Chart filter active: {filter_str} — '
        f'Explorer tab is pre-filtered</div>',
        unsafe_allow_html=True,
    )
    if col_c.button("✕ Clear", key="clear_xf"):
        st.session_state.pop("xf_topic", None)
        st.session_state.pop("xf_sentiment", None)
        st.rerun()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Dashboard",
    "🔎  Explorer",
    "💡  Executive Insights",
    "💬  Ask the Data",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    section("Call Analytics Overview", f"Based on {n_filtered} filtered transcripts")

    # ── Row 1: Topic frequency + Sentiment pie ─────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        tf = Counter(df_f["topic"]).most_common(12)
        tf_df = pd.DataFrame(tf, columns=["topic", "count"])

        # Highlight most negative topic
        neg_counts = Counter(
            t["topic"] for t in enriched_f if t.get("sentiment") in ("negative", "mixed")
        )
        worst = neg_counts.most_common(1)[0][0] if neg_counts else None

        bar_colors = [
            "#ef4444" if t == worst else "#3b82f6"
            for t in tf_df["topic"]
        ]
        fig_tf = go.Figure(go.Bar(
            x=tf_df["count"], y=tf_df["topic"],
            orientation="h",
            marker_color=bar_colors,
            marker_line_width=0,
            hovertemplate="%{y}: %{x} calls<extra></extra>",
        ))
        if worst and worst in tf_df["topic"].values:
            worst_count = tf_df.loc[tf_df["topic"] == worst, "count"].values[0]
            fig_tf.add_annotation(
                x=worst_count, y=worst,
                text="⚠ Most negative",
                showarrow=True, arrowhead=2,
                ax=40, ay=0,
                font=dict(color="#ef4444", size=11),
                arrowcolor="#ef4444",
            )
        fig_tf.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Top Topics by Frequency  <sup>(click to filter)</sup>", font_size=14),
            coloraxis_showscale=False,
            yaxis=dict(categoryorder="total ascending"),
            height=400,
            clickmode="event+select",
        )
        topic_event = st.plotly_chart(
            fig_tf, use_container_width=True,
            on_select="rerun", key="topic_chart",
        )
        if topic_event and topic_event.selection and topic_event.selection.points:
            clicked = topic_event.selection.points[0].get("y")
            if clicked:
                st.session_state["xf_topic"] = clicked
                st.session_state.pop("xf_sentiment", None)
                st.rerun()

    with col_b:
        sent_labels = list(dict(Counter(df_f["sentiment"])).keys())
        sent_values = [dict(Counter(df_f["sentiment"]))[s] for s in sent_labels]
        sent_colors = [sentiment_color(s) for s in sent_labels]

        fig_pie = go.Figure(go.Pie(
            labels=sent_labels, values=sent_values,
            hole=0.55,
            marker=dict(colors=sent_colors, line=dict(color="#0f172a", width=2)),
            hovertemplate="%{label}: %{value} calls (%{percent})<extra></extra>",
        ))
        fig_pie.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Sentiment Distribution  <sup>(click to filter)</sup>", font_size=14),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            height=400,
            annotations=[dict(
                text=f"{n_filtered}<br>calls",
                x=0.5, y=0.5, font_size=18, font_color="#f1f5f9", showarrow=False,
            )],
            clickmode="event+select",
        )
        sent_event = st.plotly_chart(
            fig_pie, use_container_width=True,
            on_select="rerun", key="sent_chart",
        )
        if sent_event and sent_event.selection and sent_event.selection.points:
            clicked_sent = sent_event.selection.points[0].get("label")
            if clicked_sent:
                st.session_state["xf_sentiment"] = clicked_sent
                st.session_state.pop("xf_topic", None)
                st.rerun()

    # Inline cross-filter preview
    if xf_topic or xf_sentiment:
        preview_df = df_f.copy()
        if xf_topic:
            preview_df = preview_df[preview_df["topic"] == xf_topic]
        if xf_sentiment:
            preview_df = preview_df[preview_df["sentiment"] == xf_sentiment]

        with st.expander(f"📋 {len(preview_df)} transcripts matching filter — preview", expanded=False):
            for _, row in preview_df.head(10).iterrows():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{row['title']}**")
                c1.markdown(f"<small style='color:#64748b'>{row.get('summary','')[:120]}…</small>", unsafe_allow_html=True)
                c2.markdown(
                    " ".join([
                        badge_html("", row.get("sentiment","").capitalize(), sentiment_color(row.get("sentiment",""))),
                        badge_html("", row.get("urgency","").capitalize(), urgency_color(row.get("urgency",""))),
                    ]),
                    unsafe_allow_html=True,
                )
                st.markdown("<hr style='margin:6px 0;border-color:#1e293b'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Sentiment by call type + Urgency ────────────────────────────────
    col_c, col_d = st.columns(2)

    with col_c:
        sbt = df_f.groupby(["call_type", "sentiment"]).size().unstack(fill_value=0)
        fig_sbt = go.Figure()
        for sent in ["positive", "neutral", "mixed", "negative"]:
            if sent in sbt.columns:
                fig_sbt.add_trace(go.Bar(
                    name=sent.capitalize(),
                    x=sbt.index.tolist(),
                    y=sbt[sent].tolist(),
                    marker_color=sentiment_color(sent),
                ))
        fig_sbt.update_layout(
            **PLOTLY_BASE,
            barmode="stack",
            title=dict(text="Sentiment by Call Type", font_size=14),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25),
            height=320,
        )
        st.plotly_chart(fig_sbt, use_container_width=True)

    with col_d:
        urg_order = ["low", "medium", "high", "critical"]
        urg_counts = dict(Counter(df_f["urgency"]))
        urg_labels = [u.capitalize() for u in urg_order if u in urg_counts]
        urg_vals   = [urg_counts[u] for u in urg_order if u in urg_counts]
        urg_colors = [urgency_color(u) for u in urg_order if u in urg_counts]

        fig_urg = go.Figure(go.Bar(
            x=urg_labels, y=urg_vals,
            marker_color=urg_colors, marker_line_width=0,
            text=urg_vals, textposition="auto",
            hovertemplate="%{x}: %{y} calls<extra></extra>",
        ))
        fig_urg.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Urgency Distribution", font_size=14),
            height=320,
        )
        st.plotly_chart(fig_urg, use_container_width=True)

    # ── Timeline ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section("Call Activity Timeline", "Each bubble = one call · size = duration · color = sentiment")

    tl_df = df_f.copy()
    tl_df["date_str"] = tl_df["date"].astype(str)
    tl_df["sentiment_score_num"] = pd.to_numeric(tl_df["sentiment_score"], errors="coerce")
    tl_df["size_norm"] = tl_df["duration_minutes"].clip(upper=90).fillna(20)

    fig_tl = px.scatter(
        tl_df,
        x="date_str",
        y="sentiment_score_num",
        color="sentiment",
        size="size_norm",
        hover_name="title",
        hover_data={"call_type": True, "topic": True, "urgency": True,
                    "date_str": False, "size_norm": False, "sentiment_score_num": False},
        color_discrete_map={
            "positive": "#22c55e",
            "neutral": "#94a3b8",
            "mixed": "#f59e0b",
            "negative": "#ef4444",
        },
        size_max=22,
    )
    fig_tl.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title="Date", tickangle=-30, gridcolor="#1e293b"),
        yaxis=dict(title="Sentiment Score (1–5)", range=[0.5, 5.5], gridcolor="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        height=340,
    )
    st.plotly_chart(fig_tl, use_container_width=True)

    # ── Row 3: Negative topics + Churn risk ───────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_e, col_f = st.columns(2)

    with col_e:
        neg_topics = Counter(
            t["topic"] for t in enriched_f if t.get("sentiment") in ("negative", "mixed")
        ).most_common(8)
        neg_df = pd.DataFrame(neg_topics, columns=["topic", "count"])

        fig_neg = px.bar(
            neg_df, x="topic", y="count",
            color="count",
            color_continuous_scale=[[0, "#7f1d1d"], [1, "#ef4444"]],
        )
        if not neg_df.empty:
            top_neg_topic = neg_df.iloc[0]["topic"]
            top_neg_count = neg_df.iloc[0]["count"]
            fig_neg.add_annotation(
                x=top_neg_topic, y=top_neg_count,
                text="⚠ Highest risk",
                showarrow=True, arrowhead=2,
                ay=-30, font=dict(color="#ef4444", size=11),
                arrowcolor="#ef4444",
            )
        fig_neg.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Top Topics with Negative/Mixed Sentiment", font_size=14),
            coloraxis_showscale=False,
            xaxis_tickangle=-30,
            height=320,
        )
        st.plotly_chart(fig_neg, use_container_width=True)

    with col_f:
        churn_order = ["none", "low", "medium", "high"]
        churn_counts = dict(Counter(df_f["churn_risk"]))
        ch_labels = [c.capitalize() for c in churn_order if c in churn_counts]
        ch_vals   = [churn_counts[c] for c in churn_order if c in churn_counts]
        ch_colors = [churn_color(c) for c in churn_order if c in churn_counts]

        fig_churn = go.Figure(go.Bar(
            x=ch_labels, y=ch_vals,
            marker_color=ch_colors, marker_line_width=0,
            text=ch_vals, textposition="auto",
            hovertemplate="%{x}: %{y} accounts<extra></extra>",
        ))
        fig_churn.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Churn Risk Distribution", font_size=14),
            height=320,
        )
        st.plotly_chart(fig_churn, use_container_width=True)

    # ── At-Risk Accounts + Deep-Dive ──────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section("⚠️ At-Risk Accounts", "Click a row to see full account history")

    risk_accounts = agg.get("churn_risk_accounts", [])
    if risk_accounts:
        risk_df = pd.DataFrame(risk_accounts)[["account", "churn_risk", "sentiment", "urgency", "summary"]]
        risk_df.columns = ["Account", "Churn Risk", "Sentiment", "Urgency", "Summary"]

        risk_event = st.dataframe(
            risk_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="risk_table",
            column_config={"Summary": st.column_config.TextColumn("Summary", width="large")},
        )

        selected_rows = risk_event.selection.rows if risk_event.selection else []
        if selected_rows:
            acct = risk_accounts[selected_rows[0]]
            acct_name = acct["account"]
            st.session_state["xf_account"] = acct_name

        selected_account = st.session_state.get("xf_account")
        if selected_account:
            acct_calls = df[df["title"].str.contains(selected_account, case=False, na=False)]

            st.markdown(f"<br>", unsafe_allow_html=True)
            st.markdown(
                f'<div class="acct-panel">',
                unsafe_allow_html=True,
            )
            section(f"📂 Account Deep-Dive: {selected_account}",
                    f"{len(acct_calls)} calls found")

            if not acct_calls.empty:
                # Mini sentiment timeline for this account
                acct_tl = acct_calls.copy()
                acct_tl["date_str"] = acct_tl["date"].astype(str)
                acct_tl["sentiment_score_num"] = pd.to_numeric(
                    acct_tl["sentiment_score"], errors="coerce"
                )

                fig_acct = px.line(
                    acct_tl.sort_values("date_str"),
                    x="date_str", y="sentiment_score_num",
                    markers=True,
                    color_discrete_sequence=["#3b82f6"],
                )
                fig_acct.update_layout(
                    **PLOTLY_BASE,
                    title=dict(text="Sentiment Score Over Time", font_size=13),
                    xaxis=dict(title="", tickangle=-20),
                    yaxis=dict(title="Score (1–5)", range=[0.5, 5.5]),
                    height=220,
                )
                st.plotly_chart(fig_acct, use_container_width=True)

                # Call list
                for _, row in acct_calls.sort_values("date", ascending=False).iterrows():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{row['title']}**  \n<small style='color:#64748b'>{row['date']}</small>", unsafe_allow_html=True)
                    c2.markdown(
                        badge_html("", row.get("sentiment","").capitalize(), sentiment_color(row.get("sentiment",""))),
                        unsafe_allow_html=True,
                    )
                    c3.markdown(
                        badge_html("", row.get("urgency","").capitalize(), urgency_color(row.get("urgency",""))),
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"<small style='color:#94a3b8'>{row.get('summary','')[:160]}…</small>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin:6px 0;border-color:#334155'>", unsafe_allow_html=True)

                # Ask about this account
                if st.button(f"💬 Ask the data about {selected_account}", key="acct_ask"):
                    q = f"Tell me everything about the calls with {selected_account}. What are their main concerns, sentiment trends, and churn risk?"
                    st.session_state["chatbot_prefill"] = q
                    st.info("Question pre-loaded — switch to the 'Ask the Data' tab.")

            if st.button("✕ Close", key="close_acct"):
                st.session_state.pop("xf_account", None)
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No high/medium churn risk accounts detected.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Explorer
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    section("Transcript Explorer", "Browse, search, and export individual call transcripts")

    # Search box
    search_query = st.text_input(
        "Search", placeholder="Search titles and summaries…",
        label_visibility="collapsed", key="explorer_search",
    )

    # Filters (pre-populate from cross-filter state)
    f1, f2, f3 = st.columns(3)
    with f1:
        ct_opts = ["All"] + sorted(df_f["call_type"].unique().tolist())
        ct_default = xf_topic and "All" or "All"
        ct_filter = st.selectbox("Call Type", ct_opts)
    with f2:
        sent_opts = ["All"] + sorted(df_f["sentiment"].dropna().unique().tolist())
        sent_default_val = xf_sentiment if xf_sentiment in sent_opts else "All"
        sent_filter = st.selectbox("Sentiment", sent_opts, index=sent_opts.index(sent_default_val))
    with f3:
        urg_filter = st.selectbox("Urgency", ["All", "critical", "high", "medium", "low"])

    explorer_df = df_f.copy()
    if ct_filter != "All":
        explorer_df = explorer_df[explorer_df["call_type"] == ct_filter]
    if sent_filter != "All":
        explorer_df = explorer_df[explorer_df["sentiment"] == sent_filter]
    if urg_filter != "All":
        explorer_df = explorer_df[explorer_df["urgency"] == urg_filter]
    if xf_topic:
        explorer_df = explorer_df[explorer_df["topic"] == xf_topic]
    if search_query.strip():
        q = search_query.strip().lower()
        explorer_df = explorer_df[
            explorer_df["title"].str.lower().str.contains(q, na=False) |
            explorer_df["summary"].str.lower().str.contains(q, na=False)
        ]

    col_count, col_export = st.columns([3, 1])
    col_count.markdown(
        f"<small style='color:#64748b'>{len(explorer_df)} transcripts match</small>",
        unsafe_allow_html=True,
    )
    csv = explorer_df.drop(columns=["full_transcript", "date"], errors="ignore").to_csv(index=False)
    col_export.download_button(
        "⬇ Export CSV", csv, "transcripts.csv", "text/csv",
        use_container_width=True,
    )

    if explorer_df.empty:
        st.warning("No transcripts match the selected filters.")
    else:
        selected_title = st.selectbox("Select Transcript", explorer_df["title"].tolist())
        selected = explorer_df[explorer_df["title"] == selected_title].iloc[0]

        left, right = st.columns([3, 2])

        with left:
            st.markdown("**Transcript**")
            with st.expander("Full transcript", expanded=True):
                st.markdown(
                    f'<div class="transcript-box">{selected.get("full_transcript", "No transcript available.")}</div>',
                    unsafe_allow_html=True,
                )

            with st.expander("Action Items"):
                items = selected.get("action_items", [])
                if items:
                    for item in items:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("_No action items recorded._")

            with st.expander("Key Moments"):
                for m in selected.get("key_moments", []):
                    icon = {"churn_signal": "⚠️", "technical_issue": "🔧",
                            "concern": "❗", "positive_pivot": "✅"}.get(m.get("type", ""), "•")
                    st.markdown(f"{icon} **{m.get('type','').replace('_',' ').title()}**: {m.get('text','')}")

        with right:
            st.markdown("**AI Analysis**")
            sent  = selected.get("sentiment", "neutral")
            urg   = selected.get("urgency", "low")
            churn = selected.get("churn_risk", "none")

            st.markdown(
                " &nbsp; ".join([
                    badge_html("Sentiment", sent.capitalize(), sentiment_color(sent)),
                    badge_html("Urgency", urg.capitalize(), urgency_color(urg)),
                    badge_html("Churn", churn.capitalize(), churn_color(churn)),
                ]),
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

            m1, m2 = st.columns(2)
            m1.markdown(f"**Call Type**\n\n{selected.get('call_type','').capitalize()}")
            m2.markdown(f"**Duration**\n\n{selected.get('duration_minutes', 0)} min")
            m1.markdown(f"**Topic**\n\n{selected.get('topic', '—')}")
            m2.markdown(f"**Sub-Topic**\n\n{selected.get('sub_topic', '—')}")
            m1.markdown(f"**Intent**\n\n{selected.get('intent', '—').replace('_',' ').title()}")
            m2.markdown(f"**Emotion**\n\n{selected.get('emotion','—').capitalize()}")

            st.markdown("**Summary**")
            st.info(selected.get("summary", ""))

            st.markdown("**Key Entities**")
            entities = selected.get("key_entities", [])
            if entities:
                entity_html = " ".join([
                    f'<span style="background:#1e3a5f;color:#93c5fd;padding:2px 8px;'
                    f'border-radius:4px;font-size:0.8rem;margin:2px">{e}</span>'
                    for e in entities
                ])
                st.markdown(entity_html, unsafe_allow_html=True)

            sent_score = selected.get("sentiment_score")
            if sent_score is not None:
                st.markdown("**Sentiment Score** (1–5)")
                score_pct = (float(sent_score) - 1) / 4
                color = sentiment_color(sent)
                st.markdown(
                    f'<div style="background:#0f172a;border-radius:999px;height:8px;overflow:hidden;">'
                    f'<div style="width:{score_pct*100:.0f}%;height:8px;background:{color};border-radius:999px;"></div>'
                    f'</div><small style="color:#64748b">{sent_score}/5</small>',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Executive Insights
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    section("Executive Intelligence Brief",
            "AI-synthesized insights from the transcript dataset")

    col_i1, col_i2 = st.columns(2)

    with col_i1:
        st.markdown("#### 🔑 Key Business Insights")
        render_insight_cards(insights.get("key_insights", []), "", "💡")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🟢 Recommendations")
        render_insight_cards(insights.get("recommendations", []), "rec-card", "→")

    with col_i2:
        st.markdown("#### 🚨 Operational Risks")
        render_insight_cards(insights.get("operational_risks", []), "risk-card", "⚠️")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⚡ Churn Indicators")
        render_insight_cards(insights.get("churn_indicators", []), "churn-card", "📉")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 😤 Customer Pain Points")
        render_insight_cards(insights.get("customer_pain_points", []), "pain-card", "🎯")

    st.divider()
    st.markdown("#### 🗺️ Topic × Sentiment Matrix")
    st.markdown('<div class="section-sub">Which topics generate the most negative sentiment?</div>', unsafe_allow_html=True)

    top_topics_list = [t for t, _ in Counter(df_f["topic"]).most_common(10)]
    heat_df = df_f[df_f["topic"].isin(top_topics_list)].copy()
    heat_df["sentiment"] = heat_df["sentiment"].fillna("neutral")
    pivot = heat_df.groupby(["topic", "sentiment"]).size().unstack(fill_value=0)
    pivot = pivot.reindex(columns=["positive", "neutral", "mixed", "negative"], fill_value=0)

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=[[0, "#0f172a"], [0.3, "#1e3a5f"], [0.7, "#1d4ed8"], [1, "#ef4444"]],
        title="Topic × Sentiment Heatmap (call count)",
        text_auto=True,
        aspect="auto",
    )
    fig_heat.update_layout(
        **PLOTLY_BASE,
        title_font_size=14,
        height=400,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Ask the Data (Streaming)
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    section("Ask the Data",
            "Chat with your transcript data — responses stream in real time")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    def _build_history():
        return [
            msg
            for turn in st.session_state["chat_history"]
            for msg in (
                {"role": "user",      "content": turn["question"]},
                {"role": "assistant", "content": turn["answer"]},
            )
        ] or None

    def _run_streaming_question(q: str):
        with st.chat_message("user", avatar="👤"):
            st.markdown(q)
        with st.chat_message("assistant", avatar="🤖"):
            full = st.write_stream(
                answer_question_stream(q, enriched_f, agg, history=_build_history())
            )
        st.session_state["chat_history"].append({"question": q, "answer": full})

    # Suggestion buttons
    st.markdown("**Suggested questions:**")
    suggestions = [
        "What are the biggest customer pain points?",
        "Which accounts are at highest churn risk?",
        "What operational risks stand out from internal calls?",
        "What trends should the product team prioritize?",
        "Which topics drive the most negative sentiment?",
    ]
    sug_cols = st.columns(len(suggestions))
    for i, sug in enumerate(suggestions):
        if sug_cols[i].button(sug, key=f"sug_{i}", use_container_width=True):
            _run_streaming_question(sug)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pre-fill from account deep-dive button
    prefill = st.session_state.pop("chatbot_prefill", "")

    # Render existing history
    for turn in st.session_state["chat_history"]:
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["question"])
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(turn["answer"])

    # Input
    question = st.chat_input(
        "Ask anything about your transcript data…",
    )
    if prefill and not question:
        question = prefill

    if question:
        _run_streaming_question(question)

    if st.session_state["chat_history"]:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()
