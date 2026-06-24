import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
from backend.memory.store import format_past_review_for_prompt

load_dotenv()
client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a senior software engineer doing a code quality review.

Analyse the code strictly for code quality issues:
- Missing type hints or incorrect types
- Missing or inadequate docstrings and comments
- Functions or classes that are too long or do too much
- Poor variable and function naming
- Code duplication that should be extracted
- Missing or poor error handling (bare excepts, swallowed exceptions)
- Magic numbers and hardcoded values that should be constants
- Dead code, commented-out code, unreachable branches

If a previous review is provided, explicitly state whether each past issue
is FIXED, STILL PRESENT, or CANNOT DETERMINE.

Respond in exactly this format:

SEVERITY: <high|medium|low|none>

FINDINGS:
- <specific finding — reference the function or line>

RECOMMENDATIONS:
- <concrete fix>

If no issues found, respond:
SEVERITY: none
FINDINGS: No code quality issues detected.
RECOMMENDATIONS: None required."""


def _build_content(state: dict) -> str:
    parts = [f"Language: {state['language']}", f"Context: {state['context']}"]
    past = state.get("past_review")
    if past:
        parts += ["", format_past_review_for_prompt(past)]
    parts += ["", f"Code to review:\n```{state['language']}\n{state['code']}\n```"]
    return "\n".join(parts)


async def quality_agent(state: dict) -> dict:
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
        trace = make_trace("quality", "ok", start, tokens=tokens)
    except Exception as e:
        result = f"[Quality review failed: {e}]"
        trace = make_trace("quality", "error", start, error=str(e))

    return {**state, "quality_review": result, "traces": state["traces"] + [trace]}