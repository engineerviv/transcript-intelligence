# Transcript Intelligence: What 100 Customer Calls Tell Us
### AegisCloud — Findings for Product & Engineering Leadership

---

## Slide 1 — Title

**Transcript Intelligence**
*What 100 Customer Calls Tell Us About Reliability, Risk, and Revenue*

AegisCloud · Q1 2024 Analysis
Presented by: [Your Name]

---

## Slide 2 — The Headline (lead with this, don't bury it)

### One signal dominates everything: Aegis Detect has a reliability problem that is now threatening renewals.

- **41 of 100 calls** were outage-related (41%)
- Every single high-churn-risk account cited an outage
- 7 of 15 upcoming renewals are currently negative or mixed sentiment
- Two customers called out a **second outage in 8 months**

> **So what:** This is not a support process problem or a messaging problem.
> It is an engineering reliability problem with a direct revenue consequence.

---

## Slide 3 — What We Analyzed

### 100 call transcripts. Every call enriched by AI.

| Channel | Calls | What it covers |
|---|---|---|
| External (customer-facing) | 40 | QBRs, renewals, onboarding, demos |
| Internal | 33 | Incident war rooms, sprint planning, escalations |
| Support | 27 | Active cases, break-fix, escalation bridges |

Each call was analyzed for: **sentiment · urgency · churn risk · topic · intent · emotion**

> **Speaker note:** The enrichment pipeline used GPT-4o-mini with a structured schema —
> giving us consistent, queryable fields across all 100 transcripts rather than free-form notes.

---

## Slide 4 — Sentiment Split: Customers vs. Prospects Tell Different Stories

### External calls are healthy. Support calls are not.

```
Support calls:    59% negative  |  7% positive
External calls:   50% positive  | 12% negative
Overall:          32% negative  | 31% positive  | 22% mixed
```

**Average sentiment score (1–5):**
- External / customer-facing: **3.85**
- Internal: **3.28**
- Support: **2.94** ← below acceptable

> **The insight:** The product sells. The gap is post-sale reliability.
> Prospects are optimistic; customers who've hit an outage are not.

---

## Slide 5 — 41% of All Calls Were About Outages

### "Outage Response" is the #1 topic, #1 negative topic, and #1 high-urgency topic simultaneously.

Topics mentioned in negative + high-urgency calls:
1. **Outage Response** — 7 calls
2. **Product Outage** — 2 calls
3. **Service Outage** — 2 calls
4. **Platform Outage** — 2 calls
5. **Backup Performance** — 2 calls

These aren't isolated incidents — they trace back to **Aegis Detect** in the majority of cases.

Named incidents in the data:
- Detect pipeline failure (war room call)
- Detect alert delays (Summit Trust, Trailhead Marketplace)
- Detect dashboard down (Cobalt Software)
- Detect outage — 6 hours of threat monitoring blindness (Northstar Pharma)
- Detect outage during a live regulatory audit (Meridian Capital)

> **Speaker note:** The internal war-room calls are in the dataset too, which means
> we can see both sides: the customer-facing frustration and the internal scramble.

---

## Slide 6 — Churn Risk: 63% of Accounts Are Not Safe

### Only 37 accounts are classified low or no risk.

```
High risk:    16 accounts  ████████████████
Medium risk:  47 accounts  ███████████████████████████████████████████████
Low risk:     20 accounts  ████████████████████
No risk:      17 accounts  █████████████████
```

**Pattern across all 16 high-risk accounts:**
Outage → Negative sentiment → Competitor evaluation → Renewal hesitation

Competitors explicitly referenced: **SentinelShield**, competitors described as "alternative vendors"

> **The urgency:** Medium-risk accounts (47) are one more incident away from flipping to high.

---

## Slide 7 — 6 Accounts Need a Phone Call This Week

### These accounts are actively evaluating competitors right now.

| Account | Risk | Status |
|---|---|---|
| **Quantum Edge** | 🔴 High | SLA breach, renewal proposal in flight |
| **Meridian Capital** | 🔴 High | Outage during regulatory audit; formal vendor review open |
| **Northstar Pharma** | 🔴 High | 2nd outage in 8 months; CISO evaluating alternatives |
| **Summit Trust** | 🔴 High | Competitor engaged; MFA/SSO issues unresolved |
| **Nova Retail Group** | 🔴 High | Renewal decision imminent; recent outage + compliance gaps |
| **Helix Data** | 🔴 High | Explicitly stated "considering switching vendors" |

> **Recommended action:** CS team should have a proactive call with each of these accounts
> before engineering has a resolution — acknowledgement and a timeline matter more than a fix right now.

---

## Slide 8 — The Renewal Pipeline Needs Attention

### 15 renewal-related calls in the dataset. 7 of them are negative or mixed.

That is a **47% at-risk renewal rate.**

Recurring themes in at-risk renewals:
- "We need to see reliability improvements before we sign"
- "Our board is asking us to evaluate alternatives"
- "Can you give us a competitive quote?" (referencing SentinelShield)
- "The outage happened at the worst possible time"

**What the healthy renewals look like (for contrast):**
- Axiom Labs: satisfied with platform, progressing to 3-year deal
- Vanta Health: positive after backup strategy workshop

> **The pattern:** Customers who had structured success touchpoints (workshops, QBRs)
> before an incident are renewing. Those who only interacted with Aegis during incidents are not.

---

## Slide 9 — A Secondary Signal: Feature Requests Are Stacking Up

### 10 calls explicitly about feature requests. 3 carry negative sentiment.

Feature gaps mentioned:
- **Aegis Comply**: described as having "significant feature gaps" vs competitors
- **SOC 2 reporting**: customers waiting on roadmap delivery
- **Alert tuning / fatigue controls**: mentioned in multiple Detect-related calls
- **Compliance reporting automation**: manual processes causing frustration ahead of audits

> **The risk:** Feature request frustration compounds outage frustration.
> Customers who hit a reliability issue and feel the roadmap is slow to respond are the ones churning.
> Roadmap communication is as important as roadmap delivery.

---

## Slide 10 — What Good Looks Like (and Why There's Reason for Optimism)

### The product concept is resonating. The reliability issue is solvable.

- **External call sentiment avg: 3.85/5** — prospects and new customers are positive
- **Onboarding calls (4 in dataset):** generally smooth, customers engaging well
- **Satisfied customers cite:** platform capabilities, Comply v2 improvements, responsive CS teams
- **Axiom Labs** is progressing to a 3-year renewal despite a recent outage — evidence that reliability + proactive CS can recover trust

> **The framing for leadership:** This is not a product-market fit problem.
> It's a reliability and recovery confidence problem. Fix the Detect stability,
> communicate the roadmap clearly, and the churn risk is recoverable.

---

## Slide 11 — Recommendations

### Prioritized by urgency

**This week — Revenue protection**
- CS outreach to all 6 high-churn accounts before renewal dates
- Assign a named technical contact (not just a ticket queue) to each

**30 days — Engineering**
- Root cause analysis on Aegis Detect reliability — this is the single largest churn driver
- Publish an internal SLA breach timeline and remediation plan
- Prioritize alert fatigue / tuning controls (mentioned in multiple calls, blocking adoption)

**60 days — Product**
- Customer-facing roadmap update on Comply feature gaps (SOC 2 reporting, evidence automation)
- Structured QBR cadence for medium-risk accounts — proactive touchpoints before incidents happen

**Ongoing — Intelligence**
- Run this analysis on a rolling basis (weekly or monthly)
- Instrument the chat agent as an always-on signal layer for CS and PM teams

---

## Slide 12 — How We Built This (for the Engineering Audience)

### From raw call transcripts to queryable intelligence in one pipeline run.

```
Raw transcripts (JSON)
        ↓
  GPT-4o-mini enrichment
  (sentiment, urgency, churn risk, topic, intent per call)
        ↓
  FAISS semantic index
  (sentence-transformers, cosine similarity, ~10ms retrieval)
        ↓
  Aggregation layer
  (distributions, churn accounts, top topics)
        ↓
  LangGraph ReAct agent
  (3 tools: search, stats, account lookup)
        ↓
  React dashboard + streaming chat
```

**Design choices:**
- Local embedding model (no API cost for retrieval)
- Disk-level prompt cache (SHA-256) — avoid re-enriching on re-runs
- LLM output validation — catches schema drift before it corrupts downstream aggregations
- 140 automated tests

> **The pitch:** This runs on any transcript export. The same pipeline works at 1,000 calls
> with a vector DB swap (FAISS → pgvector / Pinecone). No re-architecture needed.

---

## Appendix A — Emotion Distribution

| Emotion | Count | % |
|---|---|---|
| Concerned | 49 | 49% |
| Frustrated | 22 | 22% |
| Satisfied | 25 | 25% |
| Optimistic | 4 | 4% |

**71% of customer interactions carry concern or frustration.**

---

## Appendix B — Intent Distribution

| Intent | Count |
|---|---|
| Reporting an issue | 28 |
| Planning / reviewing | 21 |
| Seeking renewal | 15 |
| Requesting a feature | 9 |
| Onboarding | 6 |
| Escalating | 4 |

28 of 100 calls are customers reporting a problem — the highest single intent in the dataset.

---

## Appendix C — Full Churn Risk Account List

*(Medium + High risk accounts with summaries — available in the dashboard)*

Access the live dashboard at: `http://localhost:5173`
Use the Explorer tab to filter by churn risk, sentiment, or urgency.
Use the chat interface to query the data in natural language.
