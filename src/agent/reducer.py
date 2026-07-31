from pathlib import Path
from agent.state import State

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Join all generated sections into final Markdown
def reducer(state: State) -> dict:
    title = state["plan"].blog_title
    body = "\n\n".join(state["sections"]).strip()
    final_md = f"# {title}\n\n{body}\n"

    filename = title.lower().replace(" ", "_") + ".md"
    (OUTPUT_DIR / filename).write_text(final_md, encoding="utf-8")

    return {"final": final_md}