import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
 
load_dotenv()
client = anthropic.AsyncAnthropic()
 
SYSTEM_PROMPT = """You are a staff engineer writing a pull request review.
 
You will receive reports from five specialist reviewers:
- Security engineer
- Performance engineer
- Code quality engineer
- Test coverage engineer
- Architecture engineer
 
Your job is to synthesise their findings into a single, well-structured review
that a developer would actually find useful. Be specific. Reference line numbers
and function names where the specialists have. Avoid filler language.
 
If a previous review attempt exists with feedback, address the feedback directly
in this revision.
 
Respond in exactly this format — do not add extra sections:
 
## Summary
One honest paragraph assessing the overall state of this code.
 
## Critical issues (must fix before merge)
Numbered list. Each item: what the problem is, where it is, why it matters.
Write "None." if there are no critical issues.
 
## Suggestions (should fix)
Numbered list. Each item: what to improve and a concrete way to do it.
Write "None." if there are no suggestions.
 
## Nitpicks (optional improvements)
Numbered list. Minor style or polish items.
Write "None." if there are no nitpicks.
 
## Verdict
PASS | REQUEST CHANGES | BLOCK
 
Severity score: X/10
 
Score using this rubric — pick the highest score that applies:
1  = style and nitpick issues only, safe to merge as-is
2  = minor code quality issues, no functional impact
3  = a few non-critical improvements recommended
4  = several medium issues across multiple areas
5  = one high-severity issue OR many medium issues
6  = multiple high-severity issues, must fix before merge
7  = a critical bug or data integrity risk present
8  = critical bug AND additional high-severity issues
9  = critical security vulnerability OR data loss risk
10 = immediate block — production system at serious risk
 
Rules:
- Any "SEVERITY: critical" in the security report → minimum score of 9
- Any "SEVERITY: high" in two or more reports → minimum score of 6
- "SEVERITY: none" across all reports → maximum score of 3
- Be consistent: the same findings should produce the same score every time
 
One sentence justification for the verdict."""
 
 
def _build_specialist_prompt(state: dict) -> str:
    """
    Build the first user message containing all specialist reports.
    This is always the first message in the conversation, whether it's
    the first attempt or a revision.
    """
    return "\n".join([
        f"Language: {state['language']}",
        f"Context: {state['context']}",
        "",
        "=== SPECIALIST REPORTS ===",
        "",
        f"SECURITY REVIEW:\n{state.get('security_review') or '[Not available]'}",
        "",
        f"PERFORMANCE REVIEW:\n{state.get('performance_review') or '[Not available]'}",
        "",
        f"CODE QUALITY REVIEW:\n{state.get('quality_review') or '[Not available]'}",
        "",
        f"TEST COVERAGE REVIEW:\n{state.get('test_review') or '[Not available]'}",
        "",
        f"ARCHITECTURE REVIEW:\n{state.get('architecture_review') or '[Not available]'}",
    ])
 
 
def _build_messages(state: dict) -> list[dict]:
    """
    Build the messages array for this synthesis call.
 
    First attempt (review_history is empty):
        messages = [{ role: user, content: specialist reports }]
 
    Revision (review_history has previous turns):
        messages = [
            { role: user,      content: specialist reports },   <- original ask
            { role: assistant, content: first review attempt }, <- what LLM wrote
            { role: user,      content: revision feedback },    <- gatekeeper critique
        ]
 
    This way the LLM sees its own previous output and can improve it
    directly, rather than starting from scratch with only a description
    of what was wrong.
    """
    history = state.get("review_history", [])
 
    if not history:
        # first attempt — no history yet
        return [{
            "role": "user",
            "content": _build_specialist_prompt(state)
        }]
 
    # revision — use existing history and append the gatekeeper's feedback
    feedback = state.get("gatekeeper_feedback", "Please improve the review.")
    return history + [{
        "role": "user",
        "content": (
            f"Your review was returned for revision. Feedback:\n\n"
            f"{feedback}\n\n"
            f"Please revise your review addressing this feedback specifically."
        )
    }]
 
 
async def synthesis_agent(state: dict) -> dict:
    """
    Reads all five specialist reviews and writes a structured final review.
 
    On first call:  builds a fresh message with all specialist reports
    On revisions:   uses multi-turn history so the LLM sees its own
                    previous attempt alongside the gatekeeper's critique
 
    Reads:  all *_review fields, language, context,
            review_history, gatekeeper_feedback
    Writes: state["final_review"], state["review_history"],
            increments state["revision_count"]
    """
    start = time.time()
    messages = _build_messages(state)
 
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        result = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        trace = make_trace("synthesis", "ok", start, tokens=tokens)
 
    except Exception as e:
        result = f"[Synthesis failed: {e}]"
        trace = make_trace("synthesis", "error", start, error=str(e))
        # on failure keep history unchanged
        return {
            **state,
            "final_review": result,
            "traces": state["traces"] + [trace],
        }
 
    # append this turn to history:
    # the messages we sent + the assistant's response
    updated_history = messages + [{
        "role": "assistant",
        "content": result
    }]
 
    return {
        **state,
        "final_review": result,
        "review_history": updated_history,
        "revision_count": state.get("revision_count", 0) + 1,
        "traces": state["traces"] + [trace],
    }