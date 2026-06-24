import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
from backend.memory.store import format_past_review_for_prompt

load_dotenv()
client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a staff engineer doing an architecture and design review.

Analyse the code strictly for design and architecture issues:
- Single Responsibility Principle violations
- Tight coupling between components
- Missing abstractions where they would reduce complexity
- Global state or singletons that make testing hard
- Poor separation of concerns (mixing I/O with business logic)
- Violation of the Open/Closed principle
- Missing interfaces or protocols where polymorphism would help

If a previous review is provided, explicitly state whether each past issue
is FIXED, STILL PRESENT, or CANNOT DETERMINE.

Respond in exactly this format:

SEVERITY: <high|medium|low|none>

FINDINGS:
- <specific design issue — reference the function or class>

RECOMMENDATIONS:
- <concrete refactoring suggestion>

If design is sound, respond:
SEVERITY: none
FINDINGS: Architecture and design are appropriate for this context.
RECOMMENDATIONS: None required."""


def _build_content(state: dict) -> str:
    parts = [f"Language: {state['language']}", f"Context: {state['context']}"]
    past = state.get("past_review")
    if past:
        parts += ["", format_past_review_for_prompt(past)]
    parts += ["", f"Code to review:\n```{state['language']}\n{state['code']}\n```"]
    return "\n".join(parts)


async def architecture_agent(state: dict) -> dict:
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
        trace = make_trace("architecture", "ok", start, tokens=tokens)
    except Exception as e:
        result = f"[Architecture review failed: {e}]"
        trace = make_trace("architecture", "error", start, error=str(e))

    return {**state, "architecture_review": result, "traces": state["traces"] + [trace]}