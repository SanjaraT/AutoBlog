"""
Persists a completed graph run to Postgres. Runs as the final node in the
main graph, after the reducer has assembled the final blog.
"""

from src.agent.state import State
from src.agent.db import get_connection


def persist_run(state: State) -> dict:
    plan = state["plan"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Insert the run itself, get back its generated id
            cur.execute(
                """
                INSERT INTO runs (
                    topic, mode, needs_research, blog_title, audience, tone,
                    blog_kind, revision_count, unverified_citation_count, final_markdown
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    state["topic"],
                    state.get("mode"),
                    state.get("needs_research"),
                    plan.blog_title,
                    plan.audience,
                    plan.tone,
                    plan.blog_kind,
                    state.get("revision_count", 0),
                    len(state.get("unverified_citations", [])),
                    state.get("final", ""),
                ),
            )
            run_id = cur.fetchone()[0]

            # Sections: dedupe by task_id first (same fix as merge_content —
            # revised sections can appear more than once in state["sections"])
            latest_sections: dict[int, str] = {}
            for task_id, md in state.get("sections", []):
                latest_sections[task_id] = md

            tasks_by_id = {t.id: t for t in plan.tasks}
            for task_id, content in latest_sections.items():
                task = tasks_by_id.get(task_id)
                cur.execute(
                    """
                    INSERT INTO sections (run_id, task_id, title, content, word_count)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (run_id, task_id, task.title if task else None, content, len(content.split())),
                )

            # Evidence
            for e in state.get("evidence", []):
                cur.execute(
                    """
                    INSERT INTO evidence (run_id, title, url, published_at, source)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (run_id, e.title, e.url, e.published_at, e.source),
                )

            # Critiques
            for c in state.get("critiques", []):
                cur.execute(
                    """
                    INSERT INTO critiques (run_id, task_id, passes, issues)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (run_id, c["task_id"], c["passes"], c.get("issues", [])),
                )

            # Images
            for spec in state.get("image_specs", []):
                cur.execute(
                    """
                    INSERT INTO images (run_id, filename, alt, caption, mermaid_code)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (run_id, spec.get("filename"), spec.get("alt"), spec.get("caption"), spec.get("mermaid_code")),
                )

    print(f"\n[persistence] Saved run #{run_id} to database.")
    return {"run_id": run_id}