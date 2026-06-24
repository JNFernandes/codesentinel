import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
from backend.memory.store import format_past_review_for_prompt

load_dotenv()
client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a senior performance engineer doing a code review.

Analyse the code strictly for performance issues:
- Algorithmic complexity (O(n²) loops, nested iterations over large datasets)
- N+1 query patterns (database calls inside loops)
- Missing caching for expensive repeated computations
- Unnecessary memory allocations (large list copies, redundant data structures)
- Blocking I/O in async contexts
- Inefficient string concatenation in loops
- Premature loading of data that may not be needed

If a previous review is provided, explicitly state whether each past issue
is FIXED, STILL PRESENT, or CANNOT DETERMINE.

Respond in exactly this format:

SEVERITY: <high|medium|low|none>

FINDINGS:
- <specific finding — include line reference and complexity if relevant>

RECOMMENDATIONS:
- <concrete fix with code snippet if helpful>

If no issues found, respond:
SEVERITY: none
FINDINGS: No performance issues detected.
RECOMMENDATIONS: None required."""


def _build_content(state: dict) -> str:
    parts = [f"Language: {state['language']}", f"Context: {state['context']}"]
    past = state.get("past_review")
    if past:
        parts += ["", format_past_review_for_prompt(past)]
    parts += ["", f"Code to review:\n```{state['language']}\n{state['code']}\n```"]
    return "\n".join(parts)


async def performance_agent(state: dict) -> dict:
    start = time.time()
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_content(state)}]
        )
        result = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        trace = make_trace("performance", "ok", start, tokens=tokens)
    except Exception as e:
        result = f"[Performance review failed: {e}]"
        trace = make_trace("performance", "error", start, error=str(e))

    return {**state, "performance_review": result, "traces": state["traces"] + [trace]}