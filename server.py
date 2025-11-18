# server.py
from fastapi import FastAPI, UploadFile, File, Form
from main import analyze
from repo_loader import clone_git_repo, unzip_repo
import os, shutil, uuid

app = FastAPI()

@app.post("/analyze_git")
async def analyze_git(git_url: str = Form(...)):
    folder = f"repo_{uuid.uuid4().hex[:6]}"
    repo_path = clone_git_repo(git_url, dest_name=folder)
    return analyze(repo_path, git_url)

@app.post("/analyze_zip")
async def analyze_zip(file: UploadFile = File(...)):
    folder = f"upload_{uuid.uuid4().hex[:6]}"
    os.makedirs("uploads", exist_ok=True)
    zip_path = f"uploads/{folder}.zip"
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    repo_path = unzip_repo(zip_path, dest_name=folder)
    return analyze(repo_path, folder)
