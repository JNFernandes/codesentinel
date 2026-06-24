import re
import time
from backend.tracing.logger import make_trace

DECISION_PASS            = "pass"
DECISION_REQUEST_CHANGES = "request_changes"
DECISION_BLOCK           = "block"

BLOCK_SCORE_THRESHOLD = 9
MAX_REVISIONS = 2


def _parse_severity_score(review: str) -> int:
    match = re.search(r'[Ss]everity score[:\s]+(\d+)\s*/\s*10', review)
    if match:
        return min(10, max(1, int(match.group(1))))
    match = re.search(r'\b(\d+)\s*/\s*10\b', review)
    if match:
        return min(10, max(1, int(match.group(1))))
    return 5


def _parse_verdict(review: str) -> str:
    verdict_section = ""
    if "## Verdict" in review:
        verdict_section = review.split("## Verdict")[-1].upper()
    else:
        verdict_section = review.upper()

    if "BLOCK" in verdict_section:
        return DECISION_BLOCK
    if "REQUEST CHANGES" in verdict_section:
        return DECISION_REQUEST_CHANGES
    if "PASS" in verdict_section:
        return DECISION_PASS

    return DECISION_REQUEST_CHANGES


def _build_feedback(review: str, score: int) -> str:
    issues = []

    if score >= 7:
        issues.append(
            "The severity score is high — ensure critical issues are at the top "
            "of the review and each one has a specific location (function name or line) "
            "and a concrete fix."
        )

    if not re.search(r'line \d+|def |class |function', review, re.IGNORECASE):
        issues.append(
            "The review lacks specific code references. Add function names, "
            "line numbers, or variable names from the actual code."
        )

    if not issues:
        issues.append(
            "Make the recommendations more actionable — each suggestion should "
            "include a concrete code change or example, not just a description of the problem."
        )

    return " ".join(issues)


async def gatekeeper_agent(state: dict) -> dict:
    start = time.time()
    review = state.get("final_review", "")

    verdict = _parse_verdict(review)
    score = _parse_severity_score(review)

    # Hard override 1: critical security → always block
    security = state.get("security_review", "") or ""
    if "SEVERITY: critical" in security:
        verdict = DECISION_BLOCK
        score = max(score, 9)

    # Hard override 2: score at threshold → block
    if score >= BLOCK_SCORE_THRESHOLD:
        verdict = DECISION_BLOCK

    # Hard override 3: revision cap → stop looping
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        if verdict == DECISION_REQUEST_CHANGES:
            verdict = DECISION_PASS

    feedback = None
    if verdict == DECISION_REQUEST_CHANGES:
        feedback = _build_feedback(review, score)

    trace = make_trace("gatekeeper", "ok", start)

    return {
        **state,
        "decision": verdict,
        "severity_score": score,
        "gatekeeper_feedback": feedback,
        "traces": state["traces"] + [trace],
    }