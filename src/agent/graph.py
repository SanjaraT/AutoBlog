from langgraph.graph import StateGraph, START, END
from src.agent.state import State
from src.agent.router import router_node, route_next
from src.agent.researcher import research_node
from src.agent.orchestrator import orchestrator_node, fanout
from src.agent.worker import worker_node
from src.agent.reducer import reducer_subgraph


def build_graph():
    g = StateGraph(State)
    g.add_node("router", router_node)
    g.add_node("research", research_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("worker", worker_node)
    # The reducer is now a compiled subgraph (merge -> decide_images -> generate_and_place_images),
    # added as a single node — LangGraph runs it as one unit from the parent graph's perspective
    g.add_node("reducer", reducer_subgraph)

    g.add_edge(START, "router")
    g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
    g.add_edge("research", "orchestrator")

    g.add_conditional_edges("orchestrator", fanout, ["worker"])
    g.add_edge("worker", "reducer")
    g.add_edge("reducer", END)

    return g.compile()


app = build_graph()