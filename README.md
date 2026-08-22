# AutoBlog

A multi-agent blog-writing system built with **LangGraph**, extended well past its
original tutorial scope into a full research → write → critique → revise →
persist → serve pipeline, with a live deployed frontend.
 
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
   images (as bytes) — to Postgres
9. **Serves** it all through a FastAPI backend with Server-Sent Events for
   live progress, and a Streamlit frontend for generating new posts and
   browsing past runs

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
| LLM | Groq (`llama-3.3-70b-versatile`, since migrated off after model decommission) |
| Search | Tavily (`langchain-tavily`) |
| Schemas | Pydantic (structured LLM outputs throughout) |
| Diagrams | Mermaid syntax, rendered via `mermaid.ink` |
| Persistence | PostgreSQL (runs, sections, evidence, critiques, images — including diagram bytes) |
| Backend | FastAPI, Server-Sent Events for live streaming progress |
| Frontend | Streamlit |
| Observability | LangSmith (local dev tracing) |
| Deployment | Render (backend + frontend as separate web services) |

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
- **Word count and code-block checks are deterministic, not LLM-judged.**
  An LLM critic was unreliable at counting words. Only the genuinely fuzzy
  judgment — bullet coverage — is left to the LLM.
- **The revision loop is capped and uses an explicit round counter** (not a
  naive summed counter), after an earlier version looped 12 times instead of
  the intended 1 due to how parallel `Send` writes were being merged.

---

## Running locally

```bash
# backend
uvicorn app.backend:api --reload --port 8000

# frontend (separate terminal)
streamlit run streamlit_app.py
```

Requires a `.env` with `DATABASE_URL`, `GROQ_API_KEY`, `TAVILY_API_KEY`, and
(optionally, for tracing) `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`,
`LANGCHAIN_PROJECT`.

---

## Future work

- **LLM evaluation harness** — a 30-topic eval set spanning all three router
  modes (`closed_book`/`hybrid`/`open_book`), since output quality is
  expected to vary by mode, scored on three signals: critic pass rate,
  citation accuracy, and an independent LLM judge (a dedicated schema +
  prompt separate from the in-pipeline critic, scoring the *finished* post
  on clarity, depth, structure, and accuracy confidence)
- Migrate from Groq to OpenAI and redeploy on AWS
- Automated tests covering the critic/revision loop, image placement, and
  citation verification
- Rate limiting on the public `/generate` endpoint
- Cost/token usage tracking per run 
- LinkedIn-ready draft generation as an optional output format
- Response caching layer for repeated/similar topics
