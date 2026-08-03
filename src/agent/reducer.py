from pathlib import Path
from langgraph.graph import StateGraph, START, END
from src.agent.state import State, GlobalImagePlan
from src.agent.llm import llm
from src.agent.prompts import DECIDE_IMAGES_SYSTEM_PROMPT
from src.agent.tools import render_mermaid_to_png
from langchain_core.messages import SystemMessage, HumanMessage

OUTPUT_DIR = Path("outputs")
IMAGES_DIR = OUTPUT_DIR / "images"
OUTPUT_DIR.mkdir(exist_ok=True)


def merge_content(state: State) -> dict:
    """Step 1: join all worker sections in planned order into one markdown doc."""
    plan = state["plan"]
    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}


def decide_images(state: State) -> dict:
    """Step 2: ask the LLM whether images help, and where to place them."""
    planner = llm.with_structured_output(GlobalImagePlan)
    merged_md = state["merged_md"]
    plan = state["plan"]
    assert plan is not None

    image_plan = planner.invoke(
        [
            SystemMessage(content=DECIDE_IMAGES_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Topic: {state['topic']}\n\n"
                    "Insert placeholders + propose image prompts.\n\n"
                    f"{merged_md}"
                )
            ),
        ]
    )

    return {
        "md_with_placeholders": image_plan.md_with_placeholders,
        "image_specs": [img.model_dump() for img in image_plan.images],
    }


def generate_and_place_images(state: State) -> dict:
    """Step 3: render each planned Mermaid diagram to PNG and splice it into the markdown."""
    plan = state["plan"]
    assert plan is not None

    md = state.get("md_with_placeholders") or state["merged_md"]
    image_specs = state.get("image_specs", []) or []

    safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in plan.blog_title)
    filename = safe_title.strip().lower().replace(" ", "_") + ".md"

    if not image_specs:
        (OUTPUT_DIR / filename).write_text(md, encoding="utf-8")
        return {"final": md}

    IMAGES_DIR.mkdir(exist_ok=True)

    for spec in image_specs:
        placeholder = spec["placeholder"]
        img_filename = spec["filename"]
        out_path = IMAGES_DIR / img_filename

        if not out_path.exists():
            try:
                img_bytes = render_mermaid_to_png(spec["mermaid_code"])
                out_path.write_bytes(img_bytes)
            except Exception as e:
                # Graceful fallback: if Mermaid syntax was invalid or the render
                # service failed, show the diagram source as a code block instead
                # of silently dropping the placeholder
                fallback_block = (
                    f"> **[DIAGRAM RENDER FAILED]** {spec.get('caption', '')}\n>\n"
                    f"```mermaid\n{spec.get('mermaid_code', '')}\n```\n"
                    f"> **Error:** {e}\n"
                )
                md = md.replace(placeholder, fallback_block)
                continue

        img_md = f"![{spec['alt']}](images/{img_filename})\n*{spec['caption']}*"
        md = md.replace(placeholder, img_md)

    (OUTPUT_DIR / filename).write_text(md, encoding="utf-8")
    return {"final": md}



def build_reducer_subgraph():
    """Wire merge -> decide -> generate into a standalone subgraph, used as one node in the main graph."""
    reducer_graph = StateGraph(State)
    reducer_graph.add_node("merge_content", merge_content)
    reducer_graph.add_node("decide_images", decide_images)
    reducer_graph.add_node("generate_and_place_images", generate_and_place_images)

    reducer_graph.add_edge(START, "merge_content")
    reducer_graph.add_edge("merge_content", "decide_images")
    reducer_graph.add_edge("decide_images", "generate_and_place_images")
    reducer_graph.add_edge("generate_and_place_images", END)

    return reducer_graph.compile()


reducer_subgraph = build_reducer_subgraph()