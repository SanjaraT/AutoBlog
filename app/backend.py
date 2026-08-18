"""
FastAPI backend for the blog-writing agent.

Endpoints:
  POST /generate       — stream a new blog generation run via SSE
  GET  /runs            — list recent past runs
  GET  /runs/{run_id}   — full detail of one past run
"""

import json
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.graph import app as agent_graph
from src.agent.db import init_schema, fetch_recent_runs, fetch_run_detail, fetch_image

api = FastAPI(title="Blog Writing Agent API")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["https://autoblog-v4o5.onrender.com"],  
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.on_event("startup")
def on_startup():
    init_schema()


@api.get("/images/{run_id}/{filename}")
def get_image(run_id: int, filename: str):
    """
    Serve a diagram image straight from Postgres rather than local disk.
    Local disk is NOT reliable in deployment -- e.g. Render's filesystem
    is ephemeral and gets wiped on every restart/redeploy, which would
    silently break every past run's images. The database is the durable
    source of truth here.
    """
    data = fetch_image(run_id, filename)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="image/png")


class GenerateRequest(BaseModel):
    topic: str


def _initial_state(topic: str) -> dict:
    return {
        "topic": topic,
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "sections": [],
        "critiques": [],
        "unverified_citations": [],
        "revision_count": 0,
        "merged_md": "",
        "md_with_placeholders": "",
        "image_specs": [],
        "final": "",
        "run_id": None,
    }


# Human-readable labels for each node, sent to the frontend as progress events
NODE_LABELS = {
    "router": "Deciding whether research is needed...",
    "research": "Researching the topic...",
    "orchestrator": "Planning blog sections...",
    "worker": "Writing sections...",
    "critic": "Reviewing section quality...",
    "reducer": "Assembling final blog and diagrams...",
    "persist": "Saving to database...",
}


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@api.post("/generate")
def generate(req: GenerateRequest):
    def event_stream():
        try:
            for step in agent_graph.stream(_initial_state(req.topic), config={"max_concurrency": 2}):
                for node_name, node_output in step.items():
                    label = NODE_LABELS.get(node_name, node_name)
                    yield _sse_event("progress", {"node": node_name, "label": label})

                    # When the final node completes, send the full result too
                    if node_name == "persist":
                        yield _sse_event("done", {
                            "run_id": node_output.get("run_id"),
                        })
        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@api.get("/runs")
def list_runs(limit: int = 20):
    return fetch_recent_runs(limit=limit)


@api.get("/runs/{run_id}")
def get_run(run_id: int):
    run = fetch_run_detail(run_id)
    if not run:
        return {"error": "Run not found"}, 404
    return run