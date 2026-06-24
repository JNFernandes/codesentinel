import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
from backend.memory.store import format_past_review_for_prompt

load_dotenv()
client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a senior QA engineer doing a test coverage review.

Analyse the code strictly for testing gaps:
- Missing unit tests for core logic
- Untested edge cases (empty inputs, None, zero, negative numbers)
- Missing error path tests
- Missing tests for security-sensitive paths
- Lack of input validation tests
- Tests that exist but are too weak

If a previous review is provided, explicitly state whether each past issue
is FIXED, STILL PRESENT, or CANNOT DETERMINE.

Respond in exactly this format:

SEVERITY: <high|medium|low|none>

FINDINGS:
- <specific gap — reference the function that needs testing>

RECOMMENDATIONS:
- <concrete test case to add>

If coverage is adequate, respond:
SEVERITY: none
FINDINGS: Test coverage is adequate.
RECOMMENDATIONS: None required."""


def _build_content(state: dict) -> str:
    parts = [f"Language: {state['language']}", f"Context: {state['context']}"]
    past = state.get("past_review")
    if past:
        parts += ["", format_past_review_for_prompt(past)]
    parts += ["", f"Code to review:\n```{state['language']}\n{state['code']}\n```"]
    return "\n".join(parts)


async def test_agent(state: dict) -> dict:
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
        trace = make_trace("test_coverage", "ok", start, tokens=tokens)
    except Exception as e:
        result = f"[Test coverage review failed: {e}]"
        trace = make_trace("test_coverage", "error", start, error=str(e))

    return {**state, "test_review": result, "traces": state["traces"] + [trace]}