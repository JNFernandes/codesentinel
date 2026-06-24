import asyncio
import time
from langgraph.graph import StateGraph, END

from backend.graph.state import ReviewState
from backend.agents.security     import security_agent
from backend.agents.performance  import performance_agent
from backend.agents.quality      import quality_agent
from backend.agents.tests        import test_agent
from backend.agents.architecture import architecture_agent
from backend.agents.synthesis    import synthesis_agent
from backend.agents.gatekeeper   import gatekeeper_agent
from backend.memory.store        import load_past_review, save_review
from backend.tracing.logger      import make_trace
 
 
# ── Node: load past review from memory ───────────────────────────────────────
 
async def memory_load(state: ReviewState) -> ReviewState:
    """
    Check the memory store for a previous review of this file.
 
    Runs BEFORE specialists so they can factor in past findings.
    If this file was never reviewed, past_review stays None and
    specialists run as normal — no change in behaviour.
 
    Reads:  state["filename"]
    Writes: state["past_review"], state["memory_key"]
    """
    start = time.time()
    filename = state.get("filename", "").strip()
    past = load_past_review(filename) if filename else None

    if past:
        print(f"  Memory: found previous review for '{filename}' "
              f"({past['reviewed_at']}, score {past['severity_score']}/10)")
    else:
        print(f"  Memory: no previous review for '{filename}'")

    return {
        **state,
        "past_review":  past,
        "memory_key":   filename,
        "traces": state["traces"] + [make_trace("memory_load", "ok", start)],
    }
 
 
# ── Node: parallel specialist fan-out ────────────────────────────────────────
 
async def run_specialists(state: ReviewState) -> ReviewState:
    """
    Run all 5 specialist agents simultaneously using asyncio.gather.
 
    If a past review exists, it is appended to the code prompt so each
    specialist can flag whether previously identified issues are still present.
    """
    results = await asyncio.gather(
        security_agent(state),
        performance_agent(state),
        quality_agent(state),
        test_agent(state),
        architecture_agent(state),
        return_exceptions=True,
    )
 
    field_map = [
        "security_review",
        "performance_review",
        "quality_review",
        "test_review",
        "architecture_review",
    ]
 
    merged = dict(state)
    all_traces = list(state.get("traces", []))
 
    for field, result in zip(field_map, results):
        if isinstance(result, Exception):
            merged[field] = f"[Agent failed: {type(result).__name__}: {result}]"
        else:
            merged[field] = result.get(field)
            all_traces.extend(result.get("traces", []))
 
    merged["traces"] = all_traces
    return merged
 
 
# ── Node: save final review to memory ────────────────────────────────────────
 
async def memory_save(state: ReviewState) -> ReviewState:
    """
    Persist the completed review to the JSON memory store.
 
    Runs AFTER gatekeeper so we only save finalised reviews.
    State is unchanged — this node is a side-effect only.
 
    Reads:  state["final_review"], state["memory_key"], state["decision"], etc.
    Writes: disk only (no state mutation)
    """
    start = time.time()
    key = (state.get("memory_key") or state.get("filename", "")).strip()

    if key and state.get("final_review"):
        save_review(state, key)
        print(f"  Memory: saved review for '{key}'")
    else:
        print(f"  Memory: skipped save (no key or no review)")

    return {
        **state,
        "traces": state["traces"] + [make_trace("memory_save", "ok", start)],
    }
 
 
# ── Routing function ──────────────────────────────────────────────────────────
 
def route_after_gatekeeper(state: ReviewState) -> str:
    """
    LangGraph calls this after the gatekeeper node.
    Returns "end" → pipeline finishes
    Returns "synthesise" → loop back for revision
    """
    decision = state.get("decision", "request_changes")
    if decision in ("pass", "block"):
        return "end"
    return "synthesise"
 
 
# ── Build and compile the graph ───────────────────────────────────────────────
 
def build_graph():
    """
    Graph shape:
        START
          ↓
        memory_load    ← NEW: retrieve past review
          ↓
        specialists    (parallel fan-out)
          ↓
        synthesise
          ↓
        gatekeeper
          ↓ (conditional)
        ┌─────────────────────────────────────┐
        │ "end"       → memory_save → END     │
        │ "synthesise"→ synthesise (revision) │
        └─────────────────────────────────────┘
    """
    graph = StateGraph(ReviewState)
 
    graph.add_node("memory_load",  memory_load)
    graph.add_node("specialists",  run_specialists)
    graph.add_node("synthesise",   synthesis_agent)
    graph.add_node("gatekeeper",   gatekeeper_agent)
    graph.add_node("memory_save",  memory_save)
 
    graph.set_entry_point("memory_load")
    graph.add_edge("memory_load", "specialists")
    graph.add_edge("specialists", "synthesise")
    graph.add_edge("synthesise",  "gatekeeper")
 
    graph.add_conditional_edges(
        "gatekeeper",
        route_after_gatekeeper,
        {
            "end":        "memory_save",   # save then finish
            "synthesise": "synthesise",    # revision loop
        }
    )
 
    graph.add_edge("memory_save", END)
 
    return graph.compile()
 
 
pipeline = build_graph()