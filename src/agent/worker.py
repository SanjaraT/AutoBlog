from langchain_core.messages import SystemMessage, HumanMessage
from agent.llm import llm
from agent.prompts import WRITER_SYSTEM_PROMPT, build_writer_user_prompt

# Worker node
def worker(payload: dict) -> dict:
    task = payload["task"]
    topic = payload["topic"]
    plan = payload["plan"]

    section_md = llm.invoke(
        [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=build_writer_user_prompt(plan.blog_title, topic, task)),
        ]
    ).content.strip()

    return {"sections": [section_md]}