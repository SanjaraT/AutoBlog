from agent.graph import app
from agent.orchestrator import orchestrator

def test_graph_runs_end_to_end():
    result = app.invoke({"topic": "Self Attention", "sections": []})
    assert "final" in result
    assert result["final"].startswith("#")

def test_plan_has_exactly_one_common_mistakes_section():
    state = orchestrator({"topic": "Self Attention"})
    types = [t.section_type for t in state["plan"].tasks]
    assert types.count("common_mistakes") == 1