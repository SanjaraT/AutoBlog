from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import Task, Plan, EvidenceItem
from src.agent.llm import llm, with_groq_retry
from src.agent.prompts import WRITER_SYSTEM_PROMPT, build_writer_user_prompt


def worker_node(payload: dict) -> dict:
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]
    topic = payload["topic"]
    mode = payload.get("mode", "closed_book")
    feedback = payload.get("feedback")

    section_md = with_groq_retry(llm).invoke(
        [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=build_writer_user_prompt(plan, topic, task, mode, evidence, feedback)),
        ]
    ).content.strip()

    result = {"sections": [(task.id, section_md)]}
    
    if "revision_count" in payload:
        result["revision_count"] = payload["revision_count"]

    return result