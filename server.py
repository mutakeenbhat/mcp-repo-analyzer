# server.py
"""
Professional MCP-style server (FastAPI) for the MCP Repository Analyzer.

Exposes endpoints:
- GET  /assignment              -> returns uploaded assignment file URL (local path transformed to file URL)
- POST /mcp/clone-analyze      -> body: { "git": "<git-url>", "name": "<optional name>" }
- POST /mcp/analyze-zip        -> multipart upload: file=zipfile
- POST /mcp/detect-transport   -> body: { "repo_path": "<local_repo_path>" }
- POST /mcp/extract-tools      -> body: { "repo_path": "<local_repo_path>" }
- GET  /reports/{name}         -> returns saved JSON report (mcp_analysis_report.json by default or named)
- Health / ready endpoints

Run: uvicorn server:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import shutil
import os
import uuid
from typing import Optional
from pathlib import Path

# Import your analyzer modules (must be present in project folder)
from repo_loader import clone_git_repo, unzip_repo, ensure_workdir
from file_indexer import index_repo
from transport_detector import detect_transport
from tool_extractor import extract_tools
from report_generator import make_report, save_report

app = FastAPI(title="MCP Repository Analyzer (Server)",
              description="FastAPI MCP provider exposing analyzer tools")

# ---------------------------
# Configuration / constants
# ---------------------------
# Developer note: the assignment PDF you uploaded is stored locally in the conversation environment.
# Provide its path here as a file URL. (Tooling will convert this path if needed.)
ASSIGNMENT_PDF_LOCAL_PATH = "/mnt/data/Internship Assignment_ MCP Repository Analyzer.pdf"

WORKING_ROOT = Path("working_repos")
TMP_UPLOADS = Path("tmp_uploads")
TMP_UPLOADS.mkdir(exist_ok=True)

# ---------------------------
# Pydantic models
# ---------------------------
class GitAnalyzeRequest(BaseModel):
    git: str
    name: Optional[str] = None

class RepoPathRequest(BaseModel):
    repo_path: str

# ---------------------------
# Utility
# ---------------------------
def safe_analyze_repo(repo_path: str, repo_ref: str):
    """
    Shared analyze logic: index -> detect transport -> extract tools -> build + save report
    Returns the report dict.
    """
    files = index_repo(repo_path)
    transport = detect_transport(files)
    tools = extract_tools(files)
    # infer_run_template is in main.py, but keep a simple run_template here:
    run_template = {"cmd": None, "confidence": 0.0, "evidence": []}
    notes = ["Analyzed via MCP server."]
    report = make_report(repo_ref, transport, tools, run_template, notes)
    # write a uniquely named report to avoid conflicts
    safe_name = f"mcp_report_{uuid.uuid4().hex[:8]}.json"
    save_report(report, out_path=safe_name)
    report["_saved_as"] = safe_name
    return report

# ---------------------------
# Endpoints
# ---------------------------

@app.get("/health")
def health():
    return {"status": "ok"}
@app.get("/status")
def status():
    return {"status": "ok"}

@app.get("/assignment")
def get_assignment_file():
    """
    Return the local file path as a file URL string. The environment/tooling that
    consumes this can transform the path into a downloadable URL if required.
    """
    if not Path(ASSIGNMENT_PDF_LOCAL_PATH).exists():
        raise HTTPException(status_code=404, detail="Assignment PDF not found on server.")
    # return as a file URL string (local path). The client or harness can fetch/transform.
    return {"url": f"file://{ASSIGNMENT_PDF_LOCAL_PATH}"}

@app.post("/mcp/clone-analyze")
def clone_and_analyze(payload: GitAnalyzeRequest):
    """
    Clone a git repository and run analysis. Returns the JSON report.
    Example body:
    {
      "git": "https://github.com/pallets/flask.git",
      "name": "flask-scan"
    }
    """
    git_url = payload.git
    dest_name = payload.name
    try:
        repo_path = clone_git_repo(git_url, dest_name=dest_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git clone failed: {e}")
    report = safe_analyze_repo(repo_path, git_url)
    return report

@app.post("/mcp/analyze-zip")
async def analyze_zip(file: UploadFile = File(...)):
    """
    Upload a ZIP file and analyze.
    Use multipart/form-data with field 'file'.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted.")
    tmp_name = TMP_UPLOADS / f"upload_{uuid.uuid4().hex[:8]}.zip"
    with open(tmp_name, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        repo_path = unzip_repo(str(tmp_name), dest_name=f"repo_{uuid.uuid4().hex[:6]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unzip/analysis failed: {e}")
    report = safe_analyze_repo(repo_path, f"uploaded:{file.filename}")
    return report

@app.post("/mcp/detect-transport")
def api_detect_transport(payload: RepoPathRequest):
    """
    Detect transport given a local repo path (must be accessible to server).
    """
    rp = payload.repo_path
    if not Path(rp).exists():
        raise HTTPException(status_code=404, detail="repo_path not found")
    files = index_repo(rp)
    transport = detect_transport(files)
    return transport

@app.post("/mcp/extract-tools")
def api_extract_tools(payload: RepoPathRequest):
    """
    Extract tools given a local repo path.
    """
    rp = payload.repo_path
    if not Path(rp).exists():
        raise HTTPException(status_code=404, detail="repo_path not found")
    files = index_repo(rp)
    tools = extract_tools(files)
    return {"tools": tools, "count": len(tools)}

@app.get("/reports/{name}")
def fetch_report(name: str):
    """
    Return a saved report file from the server working directory if present.
    """
    p = Path(name)
    if not p.exists():
        # also look in working directory
        alt = Path.cwd() / name
        if alt.exists():
            p = alt
        else:
            raise HTTPException(status_code=404, detail="Report not found.")
    return p.read_text(encoding="utf-8")

# ---------------------------
# Run block (for local dev)
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
