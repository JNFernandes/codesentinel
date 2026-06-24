import asyncio
import sys
from dotenv import load_dotenv
 
from backend.graph.state import ReviewState
from backend.graph.pipeline import pipeline
from backend.tools.code_utils import clean_code, detect_language, truncate_code
from backend.tracing.logger import print_traces
from backend.memory.store import list_reviewed_files
 
load_dotenv()
 
 
async def review(
    code: str,
    language: str = "python",
    context: str = "",
    filename: str = "",
) -> dict:
    """
    Run the full CodeSentinel pipeline on a piece of code.
 
    Args:
        code:     the raw code to review
        language: programming language — auto-detected from filename if omitted
        context:  what this code is supposed to do
        filename: used for memory lookup and language detection
 
    Returns the final state dict.
    """
    if filename and language == "python":
        detected = detect_language(filename)
        if detected != "unknown":
            language = detected
 
    code = clean_code(code)
    code = truncate_code(code, max_chars=8000)
 
    initial_state: ReviewState = {
        # Input
        "code":     code,
        "language": language,
        "context":  context or "No context provided.",
        "filename": filename,
 
        # Memory — filled by memory_load node
        "past_review": None,
        "memory_key":  None,
 
        # Specialist results
        "security_review":     None,
        "performance_review":  None,
        "quality_review":      None,
        "test_review":         None,
        "architecture_review": None,
 
        # Synthesis
        "final_review":   None,
        "severity_score": None,
        "review_history": [],
 
        # Control flow
        "decision":            None,
        "gatekeeper_feedback": None,
        "revision_count":      0,
 
        # Observability
        "traces": [],
    }
 
    label = filename or "code snippet"
    print(f"\nCodeSentinel — reviewing {label}")
    print(f"Language: {language} | Lines: {len(code.splitlines())}")
    print("─" * 60)
 
    result = await pipeline.ainvoke(initial_state)
 
    print("\n" + result["final_review"])
    print(f"\n{'─' * 60}")
    print(f"Decision:       {result['decision'].upper()}")
    print(f"Severity score: {result['severity_score']}/10")
    print(f"Revisions:      {result['revision_count']}")
 
    print_traces(result["traces"])
    return result
 
 
async def review_file(filepath: str, context: str = "") -> dict:
    """Review a file from disk."""
    from pathlib import Path
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {filepath}")
        sys.exit(1)
    code = path.read_text(encoding="utf-8")
    return await review(
        code=code,
        filename=path.name,
        context=context,
    )
 
 
# ── Example code ─────────────────────────────────────────────────────────────
 
EXAMPLE_CODE = """
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
        user_list = user_list + [user]
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
 
if __name__ == "__main__":
    # Usage:
    #   python main.py                          <- review example code
    #   python main.py path/to/file.py          <- review a real file
    #   python main.py path/to/file.py "context"
    #   python main.py --history                <- show reviewed files
 
    if len(sys.argv) > 1 and sys.argv[1] == "--history":
        files = list_reviewed_files()
        if not files:
            print("No files reviewed yet.")
        else:
            print(f"\n{'File':<30} {'Decision':<18} {'Score':>5}  Reviewed")
            print("─" * 70)
            for f in files:
                print(f"{f['filename']:<30} {f['decision']:<18} {str(f['score']):>5}/10  {f['reviewed_at']}")
        sys.exit(0)
 
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        context  = sys.argv[2] if len(sys.argv) > 2 else ""
        asyncio.run(review_file(filepath, context))
    else:
        asyncio.run(review(
            code=EXAMPLE_CODE,
            language="python",
            context="Internal admin tool for managing users and running maintenance commands",
            filename="admin_utils.py",
        ))
