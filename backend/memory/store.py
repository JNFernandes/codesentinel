"""
Persistent memory store for CodeSentinel.
 
Stores past reviews keyed by filename so the pipeline can tell
whether previously identified issues were fixed on subsequent reviews.
 
Storage: a single JSON file (.codesentinel_memory.json) in the project root.
Format:
{
    "auth.py": {
        "filename":      "auth.py",
        "language":      "python",
        "decision":      "block",
        "severity_score": 9,
        "summary":       "Critical SQL injection and hardcoded credentials...",
        "critical_issues": ["SQL injection in get_users()", "Hardcoded API key"],
        "reviewed_at":   "2026-01-15T10:23:45",
        "revision_count": 1
    },
    ...
}
 
Why JSON and not a vector store?
    For this project, exact filename matching is sufficient — you're looking up
    the history of a specific file, not doing semantic search. A JSON file is
    zero-dependency, human-readable, and easy to inspect. Upgrading to a vector
    store (Chroma, Pinecone) later is a one-file change.
"""
 
import json
import os
import re
from datetime import datetime
from pathlib import Path
 
MEMORY_FILE = Path(".codesentinel_memory.json")
 
 
def _load_store() -> dict:
    """Load the full memory store from disk. Returns empty dict if file doesn't exist."""
    if not MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
 
 
def _save_store(store: dict) -> None:
    """Write the full memory store to disk."""
    MEMORY_FILE.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
 
 
def _extract_summary(final_review: str) -> str:
    """
    Pull the Summary section text out of the final review.
    Returns the first 300 chars of the summary, or the first 300 chars
    of the whole review if no Summary section is found.
    """
    if "## Summary" in final_review:
        after = final_review.split("## Summary", 1)[1]
        # take everything up to the next ## section
        summary = after.split("##")[0].strip()
        return summary[:300]
    return final_review[:300]
 
 
def _extract_critical_issues(final_review: str) -> list[str]:
    """
    Pull the numbered critical issues out of the final review.
    Returns a list of up to 5 issue strings, or empty list if section not found.
    """
    if "## Critical issues" not in final_review:
        return []
 
    section = final_review.split("## Critical issues")[1].split("##")[0].strip()
 
    if "None." in section:
        return []
 
    # Extract numbered items: "1. something" or "- something"
    items = re.findall(r'(?:^\d+\.|^-)\s+(.+)', section, re.MULTILINE)
    return [item.strip()[:150] for item in items[:5]]
 
 
def load_past_review(filename: str) -> dict | None:
    """
    Retrieve the most recent review for a given filename.
 
    Args:
        filename: the file being reviewed (e.g. "auth.py", "src/utils.ts")
 
    Returns a dict with past review data, or None if never reviewed before.
    """
    if not filename:
        return None
 
    store = _load_store()
    return store.get(filename)
 
 
def save_review(state: dict, filename: str) -> None:
    """
    Persist the completed review to the memory store.
 
    Args:
        state:    the final pipeline state after gatekeeper runs
        filename: the file that was reviewed
    """
    if not filename:
        return
 
    final_review = state.get("final_review", "")
 
    entry = {
        "filename":       filename,
        "language":       state.get("language", "unknown"),
        "decision":       state.get("decision", "unknown"),
        "severity_score": state.get("severity_score"),
        "summary":        _extract_summary(final_review),
        "critical_issues": _extract_critical_issues(final_review),
        "reviewed_at":    datetime.now().isoformat(timespec="seconds"),
        "revision_count": state.get("revision_count", 0),
    }
 
    store = _load_store()
    store[filename] = entry
    _save_store(store)
 
 
def format_past_review_for_prompt(past: dict) -> str:
    """
    Format a past review entry into a string the LLM can read.
    This gets injected into the specialist agents' context so they can
    flag whether old issues are still present.
    """
    lines = [
        f"PREVIOUS REVIEW ({past['reviewed_at']}):",
        f"Decision: {past['decision'].upper()} | Score: {past['severity_score']}/10",
        f"Summary: {past['summary']}",
    ]
 
    if past.get("critical_issues"):
        lines.append("Critical issues flagged at that time:")
        for issue in past["critical_issues"]:
            lines.append(f"  - {issue}")
 
    lines.append(
        "\nIf any of these issues appear to still be present in the current code, "
        "flag them explicitly in your findings."
    )
 
    return "\n".join(lines)
 
 
def list_reviewed_files() -> list[dict]:
    """
    Return a summary of all files that have been reviewed.
    Useful for building a dashboard or audit trail.
    """
    store = _load_store()
    return [
        {
            "filename": k,
            "decision": v["decision"],
            "score":    v["severity_score"],
            "reviewed_at": v["reviewed_at"],
        }
        for k, v in store.items()
    ]
 
 
def clear_memory(filename: str | None = None) -> None:
    """
    Clear memory for a specific file, or the entire store if filename is None.
    Useful for testing.
    """
    if filename is None:
        if MEMORY_FILE.exists():
            MEMORY_FILE.unlink()
        return
 
    store = _load_store()
    if filename in store:
        del store[filename]
        _save_store(store)
