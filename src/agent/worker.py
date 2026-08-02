from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import Task, Plan, EvidenceItem
from src.agent.llm import llm
from src.agent.prompts import WRITER_SYSTEM_PROMPT, build_writer_user_prompt


def worker_node(payload: dict) -> dict:
    # Payload arrives as plain dicts (see fanout) — rebuild typed objects
    # here so the rest of the function gets type safety/autocomplete
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]
    topic = payload["topic"]
    mode = payload.get("mode", "closed_book")

    section_md = llm.invoke(
        [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=build_writer_user_prompt(plan, topic, task, mode, evidence)),
        ]
    ).content.strip()

    # Return (task_id, markdown) instead of just markdown — lets the reducer
    # restore planned order even though workers finish in arbitrary order
    return {"sections": [(task.id, section_md)]}