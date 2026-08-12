"""
Postgres persistence layer for the blog-writing agent.

Schema:
  runs       — one row per full graph invocation (topic, plan metadata, final markdown)
  sections   — one row per section written (task_id, content, word count)
  evidence   — one row per research evidence item used in a run
  critiques  — one row per critic verdict on a section
  images     — one row per diagram generated for a run

All child tables reference runs.id via foreign key with ON DELETE CASCADE,
so deleting a run cleans up everything related to it automatically.
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from config import DATABASE_URL


@contextmanager
def get_connection():
    """Yield a Postgres connection, always closed after use."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    mode TEXT,
    needs_research BOOLEAN,
    blog_title TEXT,
    audience TEXT,
    tone TEXT,
    blog_kind TEXT,
    revision_count INTEGER DEFAULT 0,
    unverified_citation_count INTEGER DEFAULT 0,
    final_markdown TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sections (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    word_count INTEGER
);

CREATE TABLE IF NOT EXISTS evidence (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    title TEXT,
    url TEXT,
    published_at TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS critiques (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL,
    passes BOOLEAN,
    issues TEXT[]
);

CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    filename TEXT,
    alt TEXT,
    caption TEXT,
    mermaid_code TEXT
);

CREATE INDEX IF NOT EXISTS idx_sections_run_id ON sections(run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_run_id ON evidence(run_id);
CREATE INDEX IF NOT EXISTS idx_critiques_run_id ON critiques(run_id);
CREATE INDEX IF NOT EXISTS idx_images_run_id ON images(run_id);
"""


def init_schema():
    """Create all tables if they don't already exist. Safe to call on every startup."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)


def fetch_recent_runs(limit: int = 20) -> list[dict]:
    """Return summary info for the most recent runs, newest first."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, topic, blog_title, blog_kind, revision_count,
                       unverified_citation_count, created_at
                FROM runs
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def fetch_run_detail(run_id: int) -> dict | None:
    """Return full detail for one run: metadata + final markdown + sections + critiques."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM runs WHERE id = %s", (run_id,))
            run = cur.fetchone()
            if not run:
                return None

            cur.execute("SELECT * FROM sections WHERE run_id = %s ORDER BY task_id", (run_id,))
            run["sections"] = cur.fetchall()

            cur.execute("SELECT * FROM critiques WHERE run_id = %s ORDER BY task_id", (run_id,))
            run["critiques"] = cur.fetchall()

            cur.execute("SELECT * FROM evidence WHERE run_id = %s", (run_id,))
            run["evidence"] = cur.fetchall()

            cur.execute("SELECT * FROM images WHERE run_id = %s", (run_id,))
            run["images"] = cur.fetchall()

            return run