"""
Eval harness for AutoBlog. Runs the full agent pipeline across a fixed set
of topics and reports three signals: critic pass rate, citation accuracy,
and independent LLM judge quality scores.

"""

import json
import time
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.graph import app as agent_graph
from src.agent.llm import llm, with_groq_retry
from eval_topics import EVAL_TOPICS
from eval_schemas import QualityJudgment
from eval_prompts import JUDGE_SYSTEM_PROMPT

RESULTS_PATH = Path("eval/results.json")
RESULTS_PATH.parent.mkdir(exist_ok=True)


def _initial_state(topic: str) -> dict:
    return {
        "topic": topic,
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "sections": [],
        "critiques": [],
        "unverified_citations": [],
        "revision_count": 0,
        "merged_md": "",
        "md_with_placeholders": "",
        "image_specs": [],
        "final": "",
        "run_id": None,
    }


def judge_quality(topic: str, final_markdown: str) -> QualityJudgment:
    judge = with_groq_retry(llm.with_structured_output(QualityJudgment))
    return judge.invoke(
        [
            SystemMessage(content=JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=f"Topic: {topic}\n\nBlog post to evaluate:\n\n{final_markdown}"),
        ]
    )


def run_one(topic: str) -> dict:
    print(f"\n=== Running: {topic} ===")
    try:
        result = agent_graph.invoke(_initial_state(topic), config={"max_concurrency": 2})
    except Exception as e:
        print(f"  FAILED to generate: {e}")
        return {"topic": topic, "error": str(e)}

    critiques = result.get("critiques", [])
    total_sections = len(critiques)
    passed_sections = sum(1 for c in critiques if c.get("passes"))
    critic_pass_rate = passed_sections / total_sections if total_sections else None

    unverified = result.get("unverified_citations", [])

    final_md = result.get("final", "")
    try:
        judgment = judge_quality(topic, final_md)
        judgment_dict = judgment.model_dump()
    except Exception as e:
        print(f"  Judge call failed: {e}")
        judgment_dict = None

    return {
        "topic": topic,
        "run_id": result.get("run_id"),
        "total_sections": total_sections,
        "passed_sections": passed_sections,
        "critic_pass_rate": critic_pass_rate,
        "unverified_citation_count": len(unverified),
        "judgment": judgment_dict,
    }


def load_existing_results() -> list[dict]:
    """Load any results already saved from a previous (possibly interrupted) run."""
    if RESULTS_PATH.exists():
        try:
            return json.loads(RESULTS_PATH.read_text())
        except json.JSONDecodeError:
            return []
    return []


def summarize(results: list[dict]) -> None:
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    print("\n" + "=" * 60)
    print(f"EVAL SUMMARY -- {len(results)} topics ({len(failed)} failed to generate)")
    print("=" * 60)

    if not successful:
        print("No successful runs to summarize.")
        return

    pass_rates = [r["critic_pass_rate"] for r in successful if r["critic_pass_rate"] is not None]
    avg_critic_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0

    total_unverified = sum(r["unverified_citation_count"] for r in successful)
    runs_with_unverified = sum(1 for r in successful if r["unverified_citation_count"] > 0)

    judged = [r["judgment"] for r in successful if r.get("judgment")]
    if judged:
        avg_overall = sum(j["overall"] for j in judged) / len(judged)
        avg_clarity = sum(j["clarity"] for j in judged) / len(judged)
        avg_depth = sum(j["depth"] for j in judged) / len(judged)
        avg_structure = sum(j["structure"] for j in judged) / len(judged)
        avg_accuracy = sum(j["accuracy_confidence"] for j in judged) / len(judged)
    else:
        avg_overall = avg_clarity = avg_depth = avg_structure = avg_accuracy = 0

    print(f"\nCritic pass rate (sections passing on first try, avg across runs): {avg_critic_pass_rate:.0%}")
    print(f"Unverified citations: {total_unverified} total, across {runs_with_unverified}/{len(successful)} runs")
    print(f"\nJudge scores (avg of {len(judged)} runs, out of 5):")
    print(f"  Overall:   {avg_overall:.2f}")
    print(f"  Clarity:   {avg_clarity:.2f}")
    print(f"  Depth:     {avg_depth:.2f}")
    print(f"  Structure: {avg_structure:.2f}")
    print(f"  Accuracy:  {avg_accuracy:.2f}")

    print("\n--- Markdown snippet for README ---\n")
    print("| Metric | Score |")
    print("|---|---|")
    print(f"| Topics evaluated | {len(results)} ({len(failed)} generation failures) |")
    print(f"| Critic pass rate (first try) | {avg_critic_pass_rate:.0%} |")
    print(f"| Runs with unverified citations | {runs_with_unverified}/{len(successful)} |")
    print(f"| Judge: Overall quality | {avg_overall:.2f}/5 |")
    print(f"| Judge: Clarity | {avg_clarity:.2f}/5 |")
    print(f"| Judge: Depth | {avg_depth:.2f}/5 |")
    print(f"| Judge: Structure | {avg_structure:.2f}/5 |")
    print(f"| Judge: Accuracy confidence | {avg_accuracy:.2f}/5 |")


def main():
    results = load_existing_results()
    done_topics = {r["topic"] for r in results}

    remaining = [t for t in EVAL_TOPICS if t not in done_topics]
    if done_topics:
        print(f"Resuming: {len(done_topics)} topics already done, {len(remaining)} remaining.")

    for i, topic in enumerate(remaining, start=1):
        print(f"\n[{i}/{len(remaining)} remaining]", end=" ")
        results.append(run_one(topic))
        RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))  # save after every topic
        time.sleep(2)  # small pause between runs to ease rate limits

    summarize(results)
    print(f"\nFull results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()