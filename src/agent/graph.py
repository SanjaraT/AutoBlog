from langgraph.graph import StateGraph, START, END
from src.agent.state import State
from src.agent.router import router_node, route_next
from src.agent.researcher import research_node
from src.agent.orchestrator import orchestrator_node, fanout
from src.agent.worker import worker_node
from src.agent.critic import critic_node, decide_after_critic, revise_fanout
from src.agent.reducer import reducer_subgraph
from src.agent.persistence import persist_run

def after_worker(state: State) -> str:
    """
    After ANY worker run (first pass or revision pass), route to critic —
    critic always re-checks, and decide_after_critic decides if we loop again.
    """
    return "critic"


def build_graph():
    g = StateGraph(State)
    g.add_node("router", router_node)
    g.add_node("research", research_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("worker", worker_node)
    g.add_node("critic", critic_node)
    g.add_node("reducer", reducer_subgraph)
    g.add_node("persist", persist_run)

    g.add_edge(START, "router")
    g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
    g.add_edge("research", "orchestrator")

    g.add_conditional_edges("orchestrator", fanout, ["worker"])
    g.add_edge("worker", "critic")  # every worker completion (first pass or revision) leads to critic

    g.add_conditional_edges("critic", decide_after_critic, ["worker", "reducer"])

    g.add_edge("reducer", "persist")
    g.add_edge("persist", END)

    return g.compile()


app = build_graph()
