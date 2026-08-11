"""Quick CLI check: list recent runs from the database."""
from src.agent.db import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, topic, blog_title, revision_count, created_at FROM runs ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()

for row in rows:
    print(row)