from agent.graph import app

def test_graph_runs_end_to_end():
    result = app.invoke({"topic": "Self Attention", "sections": []})
    assert "final" in result
    assert result["final"].startswith("#")