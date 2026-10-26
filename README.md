# AutoBlog

https://github.com/user-attachments/assets/6c05e0f1-0845-48b9-a56c-142ea003d5b6

A multi-agent blog-writing system built with **LangGraph**, extended well past its
original tutorial scope into a full research → write → critique → revise →
persist → serve pipeline, evaluated against a 30-topic benchmark, with a live
deployed frontend.
 
**Live app:** `https://autoblog-v4o5.onrender.com`
**Backend API:** `https://autoblog-backend-kn8l.onrender.com/`

---

## What it does

Give it a topic, and AutoBlog:

1. **Routes** the topic into one of three modes — `closed_book` (evergreen,
   no research needed), `hybrid` (evergreen + current examples), or
   `open_book` (volatile/"latest" topics that require research)
2. **Researches** the topic via Tavily search when needed, and synthesizes
   results into deduplicated, citable evidence
3. **Plans** a 5–9 section outline with per-section goals, bullets, target
   word counts, and code/citation requirements
4. **Writes** each section in parallel (map-reduce fan-out), grounding claims
   in evidence with source links
5. **Critiques** every section — word count and code-block presence are
   checked deterministically in Python, bullet coverage is judged by an LLM —
   and fans failing sections back for **one bounded revision pass**
6. **Verifies citations**, flagging any source cited in the text that wasn't
   actually in the retrieved evidence (a hallucination check)
7. **Generates diagrams**: an LLM decides where a Mermaid diagram would help
   and what it should contain; placement in the document is done
   deterministically in Python (not by asking the LLM to reproduce the whole
   document), and diagrams are rendered via the free `mermaid.ink` API
8. **Persists** the full run — sections, evidence, critiques, diagram
   images (as bytes) — to Postgres (Neon)
9. **Serves** it all through a FastAPI backend with Server-Sent Events for
   live progress, and a Streamlit frontend for generating new posts and
   browsing past runs (80+ and counting, with filtering and pagination)

---

## Evaluation results

A dedicated eval harness (`run_evals.py`) runs the full pipeline across **30
topics spanning all three router modes** (`closed_book`/`hybrid`/`open_book`,
10 each), then scores the output on three independent signals: deterministic
critic pass rate, citation accuracy, and an LLM judge — a schema and prompt
entirely separate from the in-pipeline critic, scoring the *finished* post
the way a human reader would (clarity, depth, structure, and how trustworthy
its claims feel).

**Full run, 30/30 topics completed, 0 generation failures:**

| Metric | Score |
|---|---|
| Critic pass rate (first try, no revision needed) | 89% |
| Runs with unverified/hallucinated citations | 0/30 |
| Judge: Overall quality | 3.93/5 |
| Judge: Clarity | 3.93/5 |
| Judge: Depth | 4.20/5 |
| Judge: Structure | 4.10/5 |
| Judge: Accuracy confidence | 3.47/5 |

An earlier exploratory run on a different model (GPT-4o-mini via OpenRouter,
23/30 topics before hitting a credit limit) scored notably higher on judge
Accuracy confidence (4.87/5 vs. 3.47/5 above) at a similar critic pass rate —
a real, measured quality difference between models rather than a guess,
and a concrete reason the LLM provider is kept swappable (see below).

Raw per-topic results: [`eval/results.json`](eval/results.json).

---

## Architecture

```
Topic
  │
  ▼
Router ──(needs research?)──▶ Research (Tavily)
  │                                  │
  └──────────────┬───────────────────┘
                  ▼
             Orchestrator (plans sections)
                  │
                  ▼
         Worker (fan-out, one per section)
                  │
                  ▼
                Critic ──(any section fails, <1 revision so far)──▶ back to Worker
                  │
                  ▼
        Reducer subgraph:
          merge_content → decide_images → generate_and_place_images
                  │
                  ▼
               Persist (Postgres)
```

---

## Tech stack

| Layer | Tools |
|---|---|
| Agent orchestration | LangGraph (map-reduce fan-out, conditional revision loop, subgraph) |
| LLM | Provider-swappable via a single `llm.py` (OpenAI-compatible interface) — evaluated against `gpt-oss-120b` (Groq) and `gpt-4o-mini` (OpenRouter); originally Groq `llama-3.3-70b-versatile`, migrated off after model decommission |
| Search | Tavily (`langchain-tavily`) |
| Schemas | Pydantic (structured LLM outputs throughout) |
| Diagrams | Mermaid syntax, rendered via `mermaid.ink` |
| Persistence | PostgreSQL via Neon (runs, sections, evidence, critiques, images — including diagram bytes) |
| Backend | FastAPI, Server-Sent Events for live streaming progress |
| Frontend | Streamlit (with topic search + paginated history across 80+ runs) |
| Evaluation | Custom harness: 30-topic benchmark, deterministic + LLM-judged scoring |
| Observability | LangSmith (local dev tracing) |
| Deployment | Render (backend + frontend as separate web services), Neon (managed Postgres) |

---

## Key engineering decisions

- **Diagrams are never AI-generated images.** Diffusion models reliably
  produce illegible text and broken diagrams for technical content. Instead,
  an LLM outputs Mermaid *syntax*, which is deterministically rendered —
  legible every time.
- **The LLM never reproduces the full document.** An earlier version asked
  the LLM to rewrite the entire blog just to insert diagram placeholders;
  smaller/faster models silently truncated or summarized it instead of
  copying faithfully. Placement is now decided by the LLM (which heading a
  diagram goes after) and spliced in with plain Python string logic, which
  can't lose content.
- **Diagram images live in Postgres, not local disk.** Deployment platforms
  like Render have ephemeral filesystems — anything written to disk is wiped
  on restart/redeploy. Images are stored as bytes in Postgres and served
  dynamically, so they survive redeploys.
- **The LLM provider is swappable with zero changes to business logic.**
  `llm.py` is the only file that knows which provider is in use; every node
  (router, planner, worker, critic, judge) just calls `.with_structured_output()`
  on whatever it's given. This let the project move from Groq →
  OpenRouter without touching a single prompt or pipeline node — and made it
  possible to *measure* a real quality difference between models (see
  Evaluation above) instead of just asserting one.
- **Word count and code-block checks are deterministic, not LLM-judged.**
  An LLM critic was unreliable at counting words. Only the genuinely fuzzy
  judgment — bullet coverage — is left to the LLM.
- **The revision loop is capped and uses an explicit round counter** (not a
  naive summed counter), after an earlier version looped 12 times instead of
  the intended 1 due to how parallel `Send` writes were being merged.
- **The managed database itself needed a migration plan.** Render's free
  Postgres tier expires after a fixed period — this took down the original
  database mid-project. Migrated to Neon (which doesn't share that
  expiration behavior) using `pg_dump`/`psql` for the recoverable data, plus
  a custom backfill script to reconstruct historical runs from local disk
  output where the original database rows were already gone.

---

## Running locally

```bash
# backend
uvicorn app.backend:api --reload --port 8000

# frontend (separate terminal)
streamlit run streamlit_app.py
```

Requires a `.env` with `DATABASE_URL` (Neon or local Postgres),
`OPENROUTER_API_KEY` or `GROQ_API_KEY` depending on configured provider,
`TAVILY_API_KEY`, and (optionally, for tracing) `LANGCHAIN_TRACING_V2`,
`LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`.

### Running the eval harness

```bash
python run_evals.py
```

Runs all 30 benchmark topics (skipping any already completed in
`eval/results.json`, so it's safe to stop and resume), then prints a
summary table ready to paste into this README.

---

## Future work

- Redeploy on AWS as an additional infra target beyond Render
- Automated tests covering the critic/revision loop, image placement, and
  citation verification
- Rate limiting on the public `/generate` endpoint
- Cost/token usage tracking per run
- LinkedIn-ready draft generation as an optional output format
- Response caching layer for repeated/similar topics
- Expand the eval set beyond 30 topics, and track judge scores over time as
  prompts/models change, to catch regressions rather than only improvements.