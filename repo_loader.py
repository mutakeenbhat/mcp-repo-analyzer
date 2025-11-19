# repo_loader.py
import shutil
import zipfile
from git import Repo
from pathlib import Path
import os
import stat
import shutil

def force_delete(path):
    """
    Windows-safe folder deletion.
    Removes read-only flags, deletes .git locked files, and force-removes directories.
    """
    if not os.path.exists(path):
        return

    def handle_remove_error(func, target_path, exc_info):
        # Remove "read-only" flag and retry
        try:
            os.chmod(target_path, stat.S_IWRITE)
            func(target_path)
        except Exception:
            pass

    shutil.rmtree(path, onerror=handle_remove_error)

WORK_DIR = Path("working_repos")

def ensure_workdir():
    WORK_DIR.mkdir(exist_ok=True)

def clone_git_repo(git_url: str, dest_name: str = None) -> str:
    ensure_workdir()
    dest = WORK_DIR / (dest_name or Path(git_url).stem)
    if dest.exists():
       force_delete(dest)


    Repo.clone_from(git_url, dest)
    return str(dest)

def unzip_repo(zip_path: str, dest_name: str = None) -> str:
    ensure_workdir()
    dest = WORK_DIR / (dest_name or Path(zip_path).stem)
    if dest.exists():
        force_delete(dest)

    dest.mkdir()
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest)
    return str(dest)