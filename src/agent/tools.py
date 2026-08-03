from typing import List
from langchain_community.tools.tavily_search import TavilySearchResults


def tavily_search(query: str, max_results: int = 5, snippet_char_limit: int = 400) -> List[dict]:
    """
    Run a single Tavily search and normalize results.
    Snippets are truncated to keep downstream LLM calls within token limits.
    """
    tool = TavilySearchResults(max_results=max_results)
    results = tool.invoke({"query": query})

    normalized: List[dict] = []
    for r in results or []:
        snippet = r.get("content") or r.get("snippet") or ""
        normalized.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": snippet[:snippet_char_limit],  # truncate long snippets
                "published_at": r.get("published_date") or r.get("published_at"),
                "source": r.get("source"),
            }
        )
    return normalized

import base64
import requests


def render_mermaid_to_png(mermaid_code: str) -> bytes:
    """
    Render Mermaid diagram syntax to a PNG using the free mermaid.ink API.
    No API key required. This renders actual diagram syntax rather than
    asking a generative model to "draw" a diagram from a text description,
    which avoids the illegible/garbled text problem entirely.
    """
    encoded = base64.urlsafe_b64encode(mermaid_code.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=white"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # mermaid.ink returns a 200 with an error image if the syntax is invalid,
    # so also check the response actually looks like a PNG
    if not response.content.startswith(b"\x89PNG"):
        raise RuntimeError("mermaid.ink did not return a valid PNG — check Mermaid syntax.")

    return response.content
