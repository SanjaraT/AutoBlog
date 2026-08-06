from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send
from src.agent.state import State, Plan
from src.agent.llm import llm, with_groq_retry
from src.agent.prompts import PLANNER_SYSTEM_PROMPT


def orchestrator_node(state: State) -> dict:
    planner = with_groq_retry(llm.with_structured_output(Plan))
    evidence = state.get("evidence", [])
    mode = state.get("mode", "closed_book")

    plan = planner.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Topic: {state['topic']}\n"
                    f"Mode: {mode}\n\n"
                    # Cap at 16 evidence items to keep the prompt from ballooning in size
                    f"Evidence (ONLY use for fresh claims; may be empty):\n"
                    f"{[e.model_dump() for e in evidence][:16]}"
                )
            ),
        ]
    )
    return {"plan": plan}


def fanout(state: State):
    """
    Serialize plan/task/evidence to plain dicts before sending to workers.
    Send() payloads should be plain data, not pydantic objects, to keep
    parallel worker state isolated and easily serializable.
    """
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
            },
        )
        for task in state["plan"].tasks
    ]