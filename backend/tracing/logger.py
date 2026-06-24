import time
from typing import Optional


def make_trace(
    agent: str,
    status: str,
    start_time: float,
    error: Optional[str] = None,
    tokens: Optional[int] = None,
) -> dict:
    """
    Build a single trace entry for one agent call.

    Args:
        agent:      agent name, e.g. "security"
        status:     "ok" or "error"
        start_time: value from time.time() captured before the API call
        error:      error message if status is "error"
        tokens:     total tokens used (optional, from response.usage)

    Returns a dict that gets appended to state["traces"].
    """
    return {
        "agent": agent,
        "status": status,
        "duration_ms": int((time.time() - start_time) * 1000),
        "error": error,
        "tokens": tokens,
    }


def print_traces(traces: list[dict]) -> None:
    """Pretty-print the trace list at the end of a pipeline run."""
    print("\n=== Agent trace ===")
    total_ms = sum(t["duration_ms"] for t in traces)
    for t in traces:
        icon = "+" if t["status"] == "ok" else "!"
        token_str = f"  {t['tokens']} tokens" if t.get("tokens") else ""
        err_str = f"  ERROR: {t['error']}" if t.get("error") else ""
        print(f"  [{icon}] {t['agent']:<22} {t['duration_ms']:>5}ms{token_str}{err_str}")
    print(f"  {'─' * 38}")
    print(f"  {'total ms recorded':<22} {total_ms:>5}ms")
    print(f"  (wall time ≈ slowest parallel agent, not sum)\n")
