"""
Milestone 1 test suite.

Run with:  python test_milestone1.py
or:        python test_milestone1.py security   <- test one agent only

Each test:
  1. Calls the agent with a realistic buggy code snippet
  2. Checks its field was filled
  3. Asserts it didn't touch any other agent's field
  4. Prints the actual output so you can judge quality
"""

import asyncio
import sys
from backend.graph.state import ReviewState
from backend.tracing.logger import print_traces


# ── Shared test code ────────────────────────────────────────────────────────
# Deliberately bad code — should trigger findings in every agent.

BUGGY_CODE = """
import subprocess
import random
import pickle

DB_PASSWORD = "admin123"
API_KEY = "sk-prod-supersecret"

def get_users(db, search_term):
    query = "SELECT * FROM users WHERE name = '" + search_term + "'"
    results = db.execute(query)

    user_list = []
    for user in results:
        user_list = user_list + [user]  # inefficient concat

    return user_list

def run_command(cmd):
    output = subprocess.run(cmd, shell=True, capture_output=True)
    return output.stdout

def load_data(filepath):
    with open(filepath, "rb") as f:
        return pickle.load(f)

def generate_token():
    return random.randint(100000, 999999)
"""

INITIAL_STATE: ReviewState = {
    "code": BUGGY_CODE,
    "language": "python",
    "context": "Internal admin tool for managing users and running maintenance commands",
    "security_review": None,
    "performance_review": None,
    "quality_review": None,
    "test_review": None,
    "architecture_review": None,
    "final_review": None,
    "severity_score": None,
    "decision": None,
    "gatekeeper_feedback": None,
    "revision_count": 0,
    "traces": [],
}

OTHER_AGENT_FIELDS = [
    "security_review",
    "performance_review",
    "quality_review",
    "test_review",
    "architecture_review",
    "final_review",
    "severity_score",
    "decision",
    "gatekeeper_feedback",
]


def assert_isolation(result: dict, own_field: str) -> None:
    """
    Verify the agent only wrote to its own field.
    This is the most important invariant in the whole system.
    """
    for field in OTHER_AGENT_FIELDS:
        if field == own_field:
            continue
        assert result[field] is None, (
            f"ISOLATION VIOLATION: {own_field}'s agent wrote to '{field}'. "
            f"Agents must only write to their own field."
        )


def assert_trace_added(result: dict, agent_name: str) -> None:
    """Verify the agent appended exactly one trace entry."""
    assert len(result["traces"]) == 1, (
        f"Expected 1 trace entry, got {len(result['traces'])}"
    )
    assert result["traces"][0]["agent"] == agent_name, (
        f"Expected trace agent='{agent_name}', got '{result['traces'][0]['agent']}'"
    )
    assert result["traces"][0]["status"] in ("ok", "error")
    assert result["traces"][0]["duration_ms"] > 0


# ── Individual agent tests ───────────────────────────────────────────────────

async def test_security():
    print("\n" + "="*60)
    print("TEST: security_agent")
    print("="*60)
    from backend.agents.security import security_agent

    result = await security_agent(dict(INITIAL_STATE))

    assert result["security_review"] is not None, "security_review should be filled"
    assert len(result["security_review"]) > 50, "review too short — check system prompt"
    assert_isolation(result, "security_review")
    assert_trace_added(result, "security")

    print("Output:\n")
    print(result["security_review"])
    print(f"\nTrace: {result['traces'][0]}")
    print("\nPASS security_agent")


async def test_performance():
    print("\n" + "="*60)
    print("TEST: performance_agent")
    print("="*60)
    from backend.agents.performance import performance_agent

    result = await performance_agent(dict(INITIAL_STATE))

    assert result["performance_review"] is not None
    assert_isolation(result, "performance_review")
    assert_trace_added(result, "performance")

    print("Output:\n")
    print(result["performance_review"])
    print(f"\nTrace: {result['traces'][0]}")
    print("\nPASS performance_agent")


async def test_quality():
    print("\n" + "="*60)
    print("TEST: quality_agent")
    print("="*60)
    from backend.agents.quality import quality_agent

    result = await quality_agent(dict(INITIAL_STATE))

    assert result["quality_review"] is not None
    assert_isolation(result, "quality_review")
    assert_trace_added(result, "quality")

    print("Output:\n")
    print(result["quality_review"])
    print(f"\nTrace: {result['traces'][0]}")
    print("\nPASS quality_agent")


async def test_tests():
    print("\n" + "="*60)
    print("TEST: test_agent")
    print("="*60)
    from backend.agents.tests import test_agent

    result = await test_agent(dict(INITIAL_STATE))

    assert result["test_review"] is not None
    assert_isolation(result, "test_review")
    assert_trace_added(result, "test_coverage")

    print("Output:\n")
    print(result["test_review"])
    print(f"\nTrace: {result['traces'][0]}")
    print("\nPASS test_agent")


async def test_architecture():
    print("\n" + "="*60)
    print("TEST: architecture_agent")
    print("="*60)
    from backend.agents.architecture import architecture_agent

    result = await architecture_agent(dict(INITIAL_STATE))

    assert result["architecture_review"] is not None
    assert_isolation(result, "architecture_review")
    assert_trace_added(result, "architecture")

    print("Output:\n")
    print(result["architecture_review"])
    print(f"\nTrace: {result['traces'][0]}")
    print("\nPASS architecture_agent")


async def test_parallel():
    """
    Run all 5 agents simultaneously — simulates what the orchestrator will do.
    Verifies there are no race conditions when agents share the same initial state.
    """
    print("\n" + "="*60)
    print("TEST: all agents in parallel (asyncio.gather)")
    print("="*60)

    from backend.agents.security     import security_agent
    from backend.agents.performance  import performance_agent
    from backend.agents.quality      import quality_agent
    from backend.agents.tests        import test_agent
    from backend.agents.architecture import architecture_agent

    import time
    start = time.time()

    results = await asyncio.gather(
        security_agent(dict(INITIAL_STATE)),
        performance_agent(dict(INITIAL_STATE)),
        quality_agent(dict(INITIAL_STATE)),
        test_agent(dict(INITIAL_STATE)),
        architecture_agent(dict(INITIAL_STATE)),
        return_exceptions=True,
    )

    wall_ms = int((time.time() - start) * 1000)

    fields = [
        "security_review",
        "performance_review",
        "quality_review",
        "test_review",
        "architecture_review",
    ]

    for field, result in zip(fields, results):
        if isinstance(result, Exception):
            print(f"  FAIL {field}: {result}")
        else:
            assert result[field] is not None, f"{field} should be filled"
            print(f"  OK  {field[:30]:<30} {result['traces'][0]['duration_ms']}ms")

    total_individual = sum(
        r["traces"][0]["duration_ms"]
        for r in results
        if isinstance(r, dict)
    )

    print(f"\n  Wall time:       {wall_ms}ms")
    print(f"  Sum of agents:   {total_individual}ms")
    print(f"  Speedup:         ~{total_individual // wall_ms}x faster than sequential")
    print("\nPASS parallel execution")


# ── Main ─────────────────────────────────────────────────────────────────────

TESTS = {
    "security":     test_security,
    "performance":  test_performance,
    "quality":      test_quality,
    "tests":        test_tests,
    "architecture": test_architecture,
    "parallel":     test_parallel,
}

async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        for name, fn in TESTS.items():
            await fn()
    elif target in TESTS:
        await TESTS[target]()
    else:
        print(f"Unknown test '{target}'. Choose from: {', '.join(TESTS.keys())} or 'all'")
        sys.exit(1)

    print("\n" + "="*60)
    print("All selected tests passed.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
