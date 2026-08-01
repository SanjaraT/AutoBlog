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