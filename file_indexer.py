# file_indexer.py
from pathlib import Path
import mimetypes

EXT_LANG_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.java': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.cpp': 'cpp',
    '.c': 'c',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.sh': 'shell',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.html': 'html',
    '.md': 'markdown',
}

def read_text_safe(path: Path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except:
        return ""

def index_repo(repo_path: str):
    root = Path(repo_path)
    files = []
    for path in root.rglob('*'):
        if path.is_file():
            ext = path.suffix.lower()
            files.append({
                "path": str(path.relative_to(root)),
                "abs_path": str(path),
                "extension": ext,
                "language": EXT_LANG_MAP.get(ext),
                "mime": mimetypes.guess_type(path.name)[0],
                "content": read_text_safe(path)
            })
    return files
