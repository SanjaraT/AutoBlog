from pathlib import Path
from src.agent.state import State

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def reducer_node(state: State) -> dict:
    plan = state["plan"]

    # Sort by task_id since parallel workers may finish in any order
    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    final_md = f"# {plan.blog_title}\n\n{body}\n"

    safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in plan.blog_title)
    filename = safe_title.strip().lower().replace(" ", "_") + ".md"
    (OUTPUT_DIR / filename).write_text(final_md, encoding="utf-8")

    return {"final": final_md}