"""
Milestone 2 test suite.

Run with:  python test_milestone2.py
or:        python test_milestone2.py utils
           python test_milestone2.py gatekeeper
           python test_milestone2.py synthesis
           python test_milestone2.py pipeline

Tests are ordered from simplest (no API calls) to most complex (full pipeline).
Always run utils and gatekeeper first — they're free (no API calls).
"""

import asyncio
import sys
from backend.graph.state import ReviewState

# ── Shared test state ────────────────────────────────────────────────────────

BASE_STATE: ReviewState = {
    "code": "import subprocess\ndef run(cmd):\n    subprocess.run(cmd, shell=True)",
    "language": "python",
    "context": "CLI utility",
    "security_review":     "SEVERITY: critical\nFINDINGS:\n- shell=True is a command injection risk\nRECOMMENDATIONS:\n- Use shell=False",
    "performance_review":  "SEVERITY: none\nFINDINGS: No performance issues.\nRECOMMENDATIONS: None required.",
    "quality_review":      "SEVERITY: medium\nFINDINGS:\n- Missing type hints\n- No docstring\nRECOMMENDATIONS:\n- Add def run(cmd: str) -> bytes",
    "test_review":         "SEVERITY: high\nFINDINGS:\n- Zero test coverage\nRECOMMENDATIONS:\n- Add unit tests with mock subprocess",
    "architecture_review": "SEVERITY: low\nFINDINGS:\n- No separation of validation from execution\nRECOMMENDATIONS:\n- Extract validate_command()",
    "final_review":        None,
    "severity_score":      None,
    "decision":            None,
    "gatekeeper_feedback": None,
    "revision_count":      0,
    "review_history":      [],
    "traces":              [],
}


# ── Test 1: code_utils (no API calls) ────────────────────────────────────────

def test_utils():
    print("\n" + "="*60)
    print("TEST: tools/code_utils.py")
    print("="*60)

    from backend.tools.code_utils import (
        clean_code, detect_language, truncate_code,
        format_code_block, count_lines
    )

    # clean_code
    assert clean_code("  def foo(): pass  \r\n") == "def foo(): pass"
    print("  OK  clean_code — strips whitespace and normalises line endings")

    # detect_language
    assert detect_language("auth.py")     == "python"
    assert detect_language("index.ts")    == "typescript"
    assert detect_language("main.go")     == "go"
    assert detect_language("Makefile")    == "unknown"
    assert detect_language("no_extension") == "unknown"
    print("  OK  detect_language — correct for known and unknown extensions")

    # truncate_code
    long_code = "x" * 20000
    result = truncate_code(long_code, max_chars=8000)
    assert len(result) < 20000
    assert "truncated" in result
    assert result.startswith("x")   # start preserved
    assert result.endswith("x")     # end preserved
    short_code = "def foo(): pass"
    assert truncate_code(short_code) == short_code  # short code untouched
    print("  OK  truncate_code — truncates long code, preserves start and end")

    # format_code_block
    block = format_code_block("def foo(): pass", "python")
    assert block.startswith("```python")
    assert "def foo(): pass" in block
    assert block.endswith("```")
    print("  OK  format_code_block — wraps in markdown fences")

    # count_lines
    assert count_lines("a\nb\nc") == 3
    assert count_lines("single line") == 1
    print("  OK  count_lines")

    print("\nPASS code_utils")


# ── Test 2: gatekeeper (no API calls — pure logic) ───────────────────────────

async def test_gatekeeper():
    print("\n" + "="*60)
    print("TEST: agents/gatekeeper.py")
    print("="*60)

    from backend.agents.gatekeeper import gatekeeper_agent

    # Scenario 1: critical security → always block regardless of verdict
    state_critical = {
        **BASE_STATE,
        "final_review": "## Summary\nMinor issues.\n\n## Critical issues (must fix before merge)\nNone.\n\n## Suggestions\nNone.\n\n## Nitpicks\nNone.\n\n## Verdict\nPASS\n\nSeverity score: 3/10\nLooks fine overall.",
        "security_review": "SEVERITY: critical\nFINDINGS:\n- command injection\nRECOMMENDATIONS:\n- fix it",
    }
    result = await gatekeeper_agent(state_critical)
    assert result["decision"] == "block", f"Expected block, got {result['decision']}"
    print("  OK  critical security finding → decision = block")

    # Scenario 2: high score → block
    state_high_score = {
        **BASE_STATE,
        "security_review": "SEVERITY: high\nFINDINGS: some issue",
        "final_review": "## Summary\nSerious issues.\n\n## Critical issues (must fix before merge)\n1. SQL injection\n\n## Suggestions\nNone.\n\n## Nitpicks\nNone.\n\n## Verdict\nBLOCK\n\nSeverity score: 9/10\nCritical security vulnerabilities.",
    }
    result = await gatekeeper_agent(state_high_score)
    assert result["decision"] == "block"
    assert result["severity_score"] == 9
    print("  OK  score 9/10 → decision = block")

    # Scenario 3: request changes → feedback is generated
    state_medium = {
        **BASE_STATE,
        "security_review": "SEVERITY: none\nFINDINGS: No issues.",
        "final_review": "## Summary\nSome improvements needed.\n\n## Critical issues (must fix before merge)\nNone.\n\n## Suggestions\n1. Add type hints\n\n## Nitpicks\nNone.\n\n## Verdict\nREQUEST CHANGES\n\nSeverity score: 5/10\nNon-critical improvements recommended.",
    }
    result = await gatekeeper_agent(state_medium)
    assert result["decision"] == "request_changes"
    assert result["gatekeeper_feedback"] is not None
    print("  OK  request_changes → feedback generated for synthesis")

    # Scenario 4: revision cap hit → stops looping
    state_at_cap = {
        **BASE_STATE,
        "revision_count": 2,
        "security_review": "SEVERITY: none\nFINDINGS: No issues.",
        "final_review": "## Summary\nOK.\n\n## Critical issues (must fix before merge)\nNone.\n\n## Suggestions\nNone.\n\n## Nitpicks\nNone.\n\n## Verdict\nREQUEST CHANGES\n\nSeverity score: 4/10\nMinor improvements.",
    }
    result = await gatekeeper_agent(state_at_cap)
    assert result["decision"] == "pass", (
        f"Expected pass (revision cap hit), got {result['decision']}"
    )
    print("  OK  revision cap → forced pass, no infinite loop")

    # Scenario 5: clean pass
    state_pass = {
        **BASE_STATE,
        "security_review": "SEVERITY: none\nFINDINGS: No security issues.\nRECOMMENDATIONS: None required.",
        "final_review": "## Summary\nWell-written code.\n\n## Critical issues (must fix before merge)\nNone.\n\n## Suggestions\nNone.\n\n## Nitpicks\nNone.\n\n## Verdict\nPASS\n\nSeverity score: 2/10\nNo significant issues found.",
    }
    result = await gatekeeper_agent(state_pass)
    assert result["decision"] == "pass"
    assert result["severity_score"] == 2
    print("  OK  clean review → decision = pass")

    print("\nPASS gatekeeper_agent")


# ── Test 3: synthesis (requires API key) ────────────────────────────────────

async def test_synthesis():
    print("\n" + "="*60)
    print("TEST: agents/synthesis.py  [requires API key]")
    print("="*60)

    from backend.agents.synthesis import synthesis_agent

    result = await synthesis_agent(dict(BASE_STATE))

    assert result["final_review"] is not None
    assert len(result["final_review"]) > 100, "Review too short"
    assert result["revision_count"] == 1, "revision_count should have incremented"
    assert len(result["traces"]) == 1
    assert result["traces"][0]["agent"] == "synthesis"

    # Check the review has the expected sections
    review = result["final_review"]
    for section in ["## Summary", "## Verdict"]:
        assert section in review, f"Missing section: {section}"

    print("  Output preview:")
    print("  " + result["final_review"][:300].replace("\n", "\n  "))
    print(f"\n  Trace: {result['traces'][0]}")
    print("\nPASS synthesis_agent")


# ── Test 4: full pipeline (requires API key) ─────────────────────────────────

async def test_pipeline():
    print("\n" + "="*60)
    print("TEST: full pipeline — graph/pipeline.py  [requires API key]")
    print("="*60)

    from backend.graph.pipeline import pipeline

    initial_state: ReviewState = {
        "code": """
import subprocess

def run_command(user_input):
    # Runs any user command — used in the admin CLI
    result = subprocess.run(user_input, shell=True, capture_output=True)
    return result.stdout

SECRET_KEY = "hardcoded-secret-do-not-commit"
""",
        "language": "python",
        "context": "Admin CLI tool for running maintenance scripts",
        "security_review":     None,
        "performance_review":  None,
        "quality_review":      None,
        "test_review":         None,
        "architecture_review": None,
        "final_review":        None,
        "severity_score":      None,
        "decision":            None,
        "gatekeeper_feedback": None,
        "revision_count":      0,
        "review_history":      [],
        "traces":              [],
    }

    print("  Running full pipeline (all agents + synthesis + gatekeeper)...")
    result = await pipeline.ainvoke(initial_state)

    # All specialist fields should be filled
    for field in ["security_review", "performance_review", "quality_review",
                  "test_review", "architecture_review"]:
        assert result[field] is not None, f"{field} should be filled"

    # Synthesis and gatekeeper should have run
    assert result["final_review"] is not None
    assert result["decision"] in ("pass", "request_changes", "block")
    assert result["severity_score"] is not None
    assert len(result["traces"]) >= 6  # 5 specialists + synthesis + gatekeeper

    print(f"\n  Decision:       {result['decision'].upper()}")
    print(f"  Severity score: {result['severity_score']}/10")
    print(f"  Revisions:      {result['revision_count']}")
    print(f"  Total agents:   {len(result['traces'])}")

    from backend.tracing.logger import print_traces
    print_traces(result["traces"])

    print("PASS full pipeline")


# ── Main ─────────────────────────────────────────────────────────────────────

TESTS = {
    "utils":      lambda: test_utils(),           # sync
    "gatekeeper": lambda: asyncio.run(test_gatekeeper()),
    "synthesis":  lambda: asyncio.run(test_synthesis()),
    "pipeline":   lambda: asyncio.run(test_pipeline()),
}

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    # Free tests (no API calls) — always run these first
    free = ["utils", "gatekeeper"]
    paid = ["synthesis", "pipeline"]

    if target == "all":
        print("\nRunning free tests first (no API calls)...")
        for name in free:
            TESTS[name]()
        print("\nRunning API tests (requires ANTHROPIC_API_KEY)...")
        for name in paid:
            TESTS[name]()
    elif target == "free":
        for name in free:
            TESTS[name]()
    elif target in TESTS:
        TESTS[target]()
    else:
        print(f"Unknown: '{target}'. Choose from: {', '.join(TESTS.keys())}, all, free")
        sys.exit(1)

    print("\n" + "="*60)
    print("All selected tests passed.")
    print("="*60)

if __name__ == "__main__":
    main()