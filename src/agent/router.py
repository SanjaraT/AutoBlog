from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import State, RouterDecision
from src.agent.llm import with_groq_retry, llm
from src.agent.prompts import ROUTER_SYSTEM_PROMPT


def router_node(state: State) -> dict:
    """
    Runs first. Decides whether the topic needs live web research
    before any planning happens.
    """
    decider = with_groq_retry(llm.with_structured_output(RouterDecision))
    decision = decider.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=f"Topic: {state['topic']}"),
        ]
    )
    return {
        "needs_research": decision.needs_research,
        "mode": decision.mode,
        "queries": decision.queries,
    }

# conditional edge
def route_next(state: State) -> str:
    """Conditional edge: send to research node, or skip straight to orchestrator."""
    return "research" if state["needs_research"] else "orchestrator"