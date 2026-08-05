import re
import base64
from typing import List

import requests
from langchain_community.tools.tavily_search import TavilySearchResults


# =============================================================================
# Web search (Tavily)
# =============================================================================

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


# =============================================================================
# Citation verification 
# =============================================================================

def extract_cited_urls(markdown: str) -> List[str]:
    """
    Pull every [Source](URL) style link out of generated markdown.
    Used to check the model didn't cite a URL it never actually retrieved.
    """
    return re.findall(r"\[Source\]\((https?://[^\)\s]+)\)", markdown)


def find_unverified_citations(sections_md: List[str], evidence_urls: set) -> List[str]:
    """
    Compare every cited URL across all sections against the known evidence URLs.
    Anything cited that isn't in evidence is a likely hallucinated source.
    """
    all_cited: List[str] = []
    for md in sections_md:
        all_cited.extend(extract_cited_urls(md))

    return sorted(set(all_cited) - evidence_urls)


# =============================================================================
# Diagram rendering (Mermaid) 
# =============================================================================

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
    if not response.content.startswith(b"\x89PNG"):
        raise RuntimeError("mermaid.ink did not return a valid PNG — check Mermaid syntax.")

    return response.content