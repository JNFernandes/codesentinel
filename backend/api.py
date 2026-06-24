"""
CodeSentinel API — FastAPI server wrapping the multi-agent pipeline.
 
Endpoints:
    POST /review          review code from text
    POST /review/file     review an uploaded file
    GET  /history         list all reviewed files
    DELETE /history/{fn}  clear memory for a file
    GET  /health          health check
 
Run with:
    uvicorn api:app --reload --port 8000
"""
 
import re
import asyncio
from pathlib import Path
from dotenv import load_dotenv
 
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
 
from backend.graph.state import ReviewState
from backend.graph.pipeline import pipeline
from backend.tools.code_utils import clean_code, detect_language, truncate_code
from backend.memory.store import list_reviewed_files, clear_memory
 
load_dotenv()
 
app = FastAPI(title="CodeSentinel", version="1.0.0")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


 
# ── Request / response models ─────────────────────────────────────────────────
 
class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    context: str = ""
    filename: str = ""
 
 
class AgentTrace(BaseModel):
    agent: str
    status: str
    duration_ms: int
    tokens: int | None = None
    error: str | None = None
 
 
class ReviewResponse(BaseModel):
    decision: str
    severity_score: int
    revision_count: int
    final_review: str
    summary: str
    critical_issues: list[str]
    suggestions: list[str]
    nitpicks: list[str]
    traces: list[AgentTrace]
    memory_hit: bool
    filename: str
 
 
# ── Parsing helpers ───────────────────────────────────────────────────────────
 
def _extract_section(review: str, section: str) -> str:
    """Extract a named ## section from the final review text."""
    if f"## {section}" not in review:
        return ""
    after = review.split(f"## {section}", 1)[1]
    return after.split("##")[0].strip()
 
 
def _extract_items(section_text: str) -> list[str]:
    """
    Pull numbered or bulleted items from a section.
    Handles: "1. item", "- item", "* item"
    Returns empty list if section says "None."
    """
    if not section_text or "None." in section_text[:20]:
        return []
    items = re.findall(r'(?:^\d+\.|^[-*])\s+(.+)', section_text, re.MULTILINE)
    # clean markdown bold from items
    cleaned = [re.sub(r'\*\*(.+?)\*\*', r'\1', i).strip() for i in items]
    return [c for c in cleaned if c]
 
 
def _build_response(result: dict) -> ReviewResponse:
    """Convert final pipeline state into a clean API response."""
    review = result.get("final_review", "")
 
    summary   = _extract_section(review, "Summary")
    critical  = _extract_items(_extract_section(review, "Critical issues (must fix before merge)"))
    suggests  = _extract_items(_extract_section(review, "Suggestions (should fix)"))
    nitpicks  = _extract_items(_extract_section(review, "Nitpicks (optional improvements)"))
 
    traces = [
        AgentTrace(
            agent=t.get("agent", ""),
            status=t.get("status", "ok"),
            duration_ms=t.get("duration_ms", 0),
            tokens=t.get("tokens"),
            error=t.get("error"),
        )
        for t in result.get("traces", [])
    ]
 
    return ReviewResponse(
        decision=result.get("decision", "unknown"),
        severity_score=result.get("severity_score") or 0,
        revision_count=result.get("revision_count", 0),
        final_review=review,
        summary=summary,
        critical_issues=critical,
        suggestions=suggests,
        nitpicks=nitpicks,
        traces=traces,
        memory_hit=result.get("past_review") is not None,
        filename=result.get("filename", ""),
    )
 
 
async def _run_pipeline(
    code: str,
    language: str,
    context: str,
    filename: str,
) -> ReviewResponse:
    """Build initial state and invoke the pipeline."""
    code = clean_code(code)
    code = truncate_code(code, max_chars=8000)
 
    if filename and language == "python":
        detected = detect_language(filename)
        if detected != "unknown":
            language = detected
 
    initial_state: ReviewState = {
        "code":                code,
        "language":            language,
        "context":             context or "No context provided.",
        "filename":            filename,
        "past_review":         None,
        "memory_key":          None,
        "security_review":     None,
        "performance_review":  None,
        "quality_review":      None,
        "test_review":         None,
        "architecture_review": None,
        "final_review":        None,
        "severity_score":      None,
        "review_history":      [],
        "decision":            None,
        "gatekeeper_feedback": None,
        "revision_count":      0,
        "traces":              [],
    }
 
    result = await pipeline.ainvoke(initial_state)
    return _build_response(result)
 
 
# ── Endpoints ─────────────────────────────────────────────────────────────────
 
@app.get("/health")
async def health():
    return {"status": "ok", "service": "CodeSentinel"}
 
 
@app.post("/review", response_model=ReviewResponse)
async def review_code(req: ReviewRequest):
    """Review code submitted as text."""
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code must not be empty")
    return await _run_pipeline(req.code, req.language, req.context, req.filename)
 
 
@app.post("/review/file", response_model=ReviewResponse)
async def review_file(
    file: UploadFile = File(...),
    context: str = "",
):
    """Review an uploaded source file."""
    content = await file.read()
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="file must be UTF-8 encoded text")
 
    filename = Path(file.filename).name if file.filename else ""
    language = detect_language(filename)
    if language == "unknown":
        language = "python"
 
    return await _run_pipeline(code, language, context, filename)
 
 
@app.get("/history")
async def get_history():
    """Return all files that have been reviewed."""
    return {"files": list_reviewed_files()}
 
 
@app.delete("/history/{filename}")
async def delete_history(filename: str):
    """Clear memory for a specific file."""
    clear_memory(filename)
    return {"deleted": filename}
