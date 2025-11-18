# repo_loader.py
import shutil
import zipfile
from git import Repo
from pathlib import Path

WORK_DIR = Path("working_repos")

def ensure_workdir():
    WORK_DIR.mkdir(exist_ok=True)

def clone_git_repo(git_url: str, dest_name: str = None) -> str:
    ensure_workdir()
    dest = WORK_DIR / (dest_name or Path(git_url).stem)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    Repo.clone_from(git_url, dest)
    return str(dest)

def unzip_repo(zip_path: str, dest_name: str = None) -> str:
    ensure_workdir()
    dest = WORK_DIR / (dest_name or Path(zip_path).stem)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir()
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest)
    return str(dest)