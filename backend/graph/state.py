from typing import TypedDict, Optional


class ReviewState(TypedDict):
    """
    The single data structure that flows through the entire pipeline.
 
    Every agent reads from this dict and returns a NEW dict with
    its field filled in. No agent mutates state in place.
 
    Who fills what:
        You (main.py)       -> code, language, context, filename,
                               revision_count, review_history, traces
        memory_load node    -> past_review, memory_key
        Specialist agents   -> security/performance/quality/test/architecture_review
        synthesis_agent()   -> final_review, review_history, revision_count
        gatekeeper_agent()  -> decision, severity_score, gatekeeper_feedback
        memory_save node    -> (writes to disk, no state change)
    """

    # ── Input ────────────────────────────────────────────────────────────────
    # Set once in main.py before the pipeline starts. Never modified after.
    code: str           # the raw code to review
    language: str       # e.g. "python", "typescript", "go"
    context: str        # what this code is supposed to do
    filename: str       # used as the memory key — e.g. "auth.py"


    # ── Memory ───────────────────────────────────────────────────────────────
    # Loaded before specialists run. None if file has never been reviewed.
    past_review: Optional[dict]   # the previous review entry from the JSON store
    memory_key: Optional[str]     # normalised filename used as the store key

    # ── Specialist results ───────────────────────────────────────────────────
    # Start as None. Each specialist agent fills its own field during
    # the parallel fan-out. No agent touches another agent's field.
    security_review: Optional[str]
    performance_review: Optional[str]
    quality_review: Optional[str]
    test_review: Optional[str]
    architecture_review: Optional[str]

    # ── Synthesis ────────────────────────────────────────────────────────────
    # Filled after all 5 specialists complete.
    final_review: Optional[str]    # the full structured PR review
    severity_score: Optional[int]  # 1-10, where 10 = block immediately
    review_history: list[dict]     # multi-turn message history across revisions
                                   # grows each loop: [user, assistant, user, ...]
                                   # synthesis uses this so the LLM sees its own
                                   # previous attempt, not just feedback about it

    # ── Control flow ─────────────────────────────────────────────────────────
    # These drive LangGraph routing in Milestone 2.
    decision: Optional[str]           # "pass" | "request_changes" | "block"
    gatekeeper_feedback: Optional[str] # critique sent back to synthesis on revision
    revision_count: int               # how many synthesis loops have run (cap at 2)

    # ── Observability ────────────────────────────────────────────────────────
    # Every agent appends one entry. Gives you a full audit trail at the end.
    traces: list[dict]
