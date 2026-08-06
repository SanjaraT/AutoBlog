from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import State, EvidencePack
from src.agent.llm import llm, with_groq_retry
from src.agent.prompts import RESEARCH_SYSTEM_PROMPT
from src.agent.tools import tavily_search


def research_node(state: State) -> dict:
    queries = state.get("queries", []) or []
    max_results_per_query = 3          # reduced from 6
    max_total_raw_results = 15         # hard cap regardless of query count

    raw_results: List[dict] = []
    for q in queries:
        raw_results.extend(tavily_search(q, max_results=max_results_per_query))

    # Cap total raw results sent to the LLM, keeping the most relevant (first) ones
    raw_results = raw_results[:max_total_raw_results]

    if not raw_results:
        return {"evidence": []}

    extractor = with_groq_retry(llm.with_structured_output(EvidencePack))
    pack = extractor.invoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
            HumanMessage(content=f"Raw results:\n{raw_results}"),
        ]
    )

    dedup = {}
    for e in pack.evidence:
        if e.url:
            dedup[e.url] = e

    return {"evidence": list(dedup.values())}