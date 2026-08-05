from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send
from src.agent.state import State, CritiquePack
from src.agent.llm import llm, with_groq_retry
from src.agent.prompts import CRITIC_SYSTEM_PROMPT
from src.agent.tools import find_unverified_citations

MAX_REVISIONS = 1  # at most one revise-and-recheck pass, bounds cost/latency


def _latest_sections_by_task_id(sections: list[tuple]) -> dict[int, str]:
    """
    sections may contain multiple entries for the same task_id after a
    revision (operator.add appends, doesn't replace). Keep only the LAST
    entry per task_id, since later entries are the most recent revision.
    """
    latest: dict[int, str] = {}
    for task_id, md in sections:
        latest[task_id] = md
    return latest


def critic_node(state: State) -> dict:
    """
    Reviews every section: word count and code presence are checked
    deterministically in Python (FIXED — was previously left to the LLM,
    which produced false failures like flagging 243 words against a
    240-360 target). Only bullet coverage goes to the LLM, since that's
    the one genuinely fuzzy judgment call here.
    """
    plan = state["plan"]
    latest = _latest_sections_by_task_id(state["sections"])
    revision_count = state.get("revision_count", 0)

    tasks_by_id = {t.id: t for t in plan.tasks}
    review_payload = []
    deterministic_issues: dict[int, list[str]] = {}

    for task_id, md in latest.items():
        task = tasks_by_id.get(task_id)
        if not task:
            continue

        actual_words = len(md.split())
        target = task.target_words
        low, high = int(target * 0.8), int(target * 1.2)  # matches writer's ±20% guidance

        issues = []
        if not (low <= actual_words <= high):
            issues.append(f"word count {actual_words}, target range {low}-{high}")
        if task.requires_code and "```" not in md:
            issues.append("requires_code=True but no code block found")

        deterministic_issues[task_id] = issues

        review_payload.append(
            {
                "task_id": task_id,
                "title": task.title,
                "bullets": task.bullets,
                "content": md,
            }
        )

    critic = with_groq_retry(llm.with_structured_output(CritiquePack))  # FIXED: was missing with_groq_retry
    result = critic.invoke(
        [
            SystemMessage(content=CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=f"Sections to review (check ONLY bullet coverage):\n{review_payload}"),
        ]
    )

    # Merge deterministic checks with the LLM's bullet-coverage judgment
    llm_results_by_id = {c.task_id: c for c in result.critiques}
    final_critiques = []
    for task_id, det_issues in deterministic_issues.items():
        llm_result = llm_results_by_id.get(task_id)
        llm_issues = llm_result.issues if llm_result else []
        all_issues = det_issues + llm_issues
        final_critiques.append({
            "task_id": task_id,
            "passes": len(all_issues) == 0,
            "issues": all_issues,
        })

    evidence_urls = {e.url for e in state.get("evidence", [])}
    unverified = find_unverified_citations(list(latest.values()), evidence_urls)

    pass_label = "initial pass" if revision_count == 0 else f"revision pass {revision_count}"
    print(f"\n[critic] Reviewing {len(final_critiques)} sections ({pass_label})...")
    for c in final_critiques:
        status = "PASS" if c["passes"] else "FAIL"
        print(f"[critic]   Section {c['task_id']}: {status}" + (f" — {c['issues']}" if c["issues"] else ""))
    if unverified:
        print(f"[critic]   {len(unverified)} unverified citation(s): {unverified}")

    return {
        "critiques": final_critiques,
        "unverified_citations": unverified,
    }


def revise_fanout(state: State, next_revision_count: int):
    """
    Re-invoke the worker ONLY for failing sections, attaching feedback.
    next_revision_count is the SAME explicit value for every parallel Send
    in this round — set once by decide_after_critic, not computed per-worker.
    """
    plan = state["plan"]
    tasks_by_id = {t.id: t for t in plan.tasks}
    failing = {c["task_id"]: c["issues"] for c in state.get("critiques", []) if not c["passes"]}

    return [
        Send(
            "worker",
            {
                "task": tasks_by_id[task_id].model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "plan": plan.model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
                "feedback": issues,
                "revision_count": next_revision_count,  # FIXED: explicit round number
            },
        )
        for task_id, issues in failing.items()
        if task_id in tasks_by_id
    ]


def decide_after_critic(state: State):
    """
    Conditional edge from critic. FIXED: now computes next_revision_count
    explicitly ONCE per round (not left to each worker to guess), then
    either fans out a revision or finalizes to reducer.
    """
    failing = [c for c in state.get("critiques", []) if not c["passes"]]
    current_revision_count = state.get("revision_count", 0)

    if failing and current_revision_count < MAX_REVISIONS:
        next_revision_count = current_revision_count + 1
        return revise_fanout(state, next_revision_count)

    return "reducer"