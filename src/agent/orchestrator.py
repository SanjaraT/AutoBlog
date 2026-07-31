from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import State, Plan
from agent.llm import llm
from agent.prompts import PLANNER_SYSTEM_PROMPT

# define node (breaks the big task (blog) into small subtasks)
def orchestrator(state: State) -> dict:
    plan = llm.with_structured_output(Plan).invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"Topic: {state['topic']}"),
        ]
    )
    return {"plan": plan}

# Conditional Edge (routing logic)
def fanout(state: State):
    from langgraph.types import Send
    return [
        Send("worker", {"task": task, "topic": state["topic"], "plan": state["plan"]})
        for task in state["plan"].tasks
    ]