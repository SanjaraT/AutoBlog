"""
One-off utility to export the LangGraph structure as a diagram.
Run manually when the graph shape changes, to refresh docs/architecture.png.

Usage:
    python scripts/visualize_graph.py
"""
from pathlib import Path
from src.agent.graph import app

DOCS_DIR = Path("outputs")
DOCS_DIR.mkdir(exist_ok=True)

# Mermaid source, useful for pasting directly into README.md
mermaid_source = app.get_graph().draw_mermaid()
(DOCS_DIR / "architecture.mmd").write_text(mermaid_source, encoding="utf-8")
print("Saved Mermaid source to docs/architecture.mmd")

# Rendered PNG, useful for embedding as an image
png_bytes = app.get_graph().draw_mermaid_png()
(DOCS_DIR / "architecture.png").write_bytes(png_bytes)
print("Saved PNG to outputs/architecture.png")