import time
from dotenv import load_dotenv
import anthropic
from backend.tracing.logger import make_trace
from backend.memory.store import format_past_review_for_prompt
 
load_dotenv()
client = anthropic.AsyncAnthropic()
 
SYSTEM_PROMPT = """You are a senior application security engineer doing a code review.
 
Analyse the code strictly for security issues:
- Injection vulnerabilities (SQL, command, LDAP, XSS)
- Hardcoded secrets, API keys, passwords, tokens
- Insecure deserialization (pickle, eval, exec)
- Broken authentication or missing authorisation checks
- Sensitive data exposure (logging PII, unencrypted storage)
- Dangerous function calls (shell=True, os.system, unsafe eval)
- Path traversal or directory listing vulnerabilities
- Insecure randomness (random instead of secrets)
 
If a previous review is provided, explicitly state whether each past issue
is FIXED, STILL PRESENT, or CANNOT DETERMINE.
 
Respond in exactly this format:
 
SEVERITY: <critical|high|medium|low|none>
 
FINDINGS:
- <specific finding — include line reference if possible>
 
RECOMMENDATIONS:
- <concrete fix for each finding>
 
If no issues found, respond:
SEVERITY: none
FINDINGS: No security issues detected.
RECOMMENDATIONS: None required."""
 
 
def _build_content(state: dict) -> str:
    parts = [
        f"Language: {state['language']}",
        f"Context: {state['context']}",
    ]
    past = state.get("past_review")
    if past:
        parts += ["", format_past_review_for_prompt(past)]
    parts += [
        "",
        f"Code to review:\n```{state['language']}\n{state['code']}\n```"
    ]
    return "\n".join(parts)
 
 
async def security_agent(state: dict) -> dict:
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
        trace = make_trace("security", "ok", start, tokens=tokens)
    except Exception as e:
        result = f"[Security review failed: {e}]"
        trace = make_trace("security", "error", start, error=str(e))
 
    return {
        **state,
        "security_review": result,
        "traces": state["traces"] + [trace],
    }
 