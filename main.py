# main.py
import argparse
from repo_loader import clone_git_repo, unzip_repo
from file_indexer import index_repo
from transport_detector import detect_transport
from tool_extractor import extract_tools
from report_generator import make_report, save_report

def infer_run_template(files):
    evidence = []
    cmd = None
    conf = 0.0
    for f in files:
        p = f["path"]
        c = f["content"].lower()
        if 'uvicorn' in c and 'app' in c:
            cmd = "uvicorn main:app --host 0.0.0.0 --port 8000"
            conf = 0.85
            evidence.append("uvicorn reference")
            break
        if 'flask' in c and 'app.run(' in c:
            cmd = "python app.py"
            conf = 0.7
            evidence.append("flask app.run found")
            break
        if 'npm start' in c or 'package.json' in p:
            cmd = "npm start"
            conf = 0.7
            evidence.append("npm start or package.json")

    if not cmd:
        for f in files:
            if f["path"].lower().startswith("readme"):
                lines = f["content"].splitlines()
                for L in lines:
                    if "python" in L or "run" in L:
                        cmd = L.strip()
                        conf = 0.4
                        evidence.append("readme run hint")
                        break
                if cmd:
                    break

    return {"cmd": cmd, "confidence": conf, "evidence": evidence}

def analyze(repo_path: str, repo_ref: str):
    files = index_repo(repo_path)
    transport = detect_transport(files)
    tools = extract_tools(files)
    run_template = infer_run_template(files)

    notes = ["Prototype analyzer using heuristics."]

    report = make_report(repo_ref, transport, tools, run_template, notes)
    save_report(report)
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--git', help='git repository url')
    parser.add_argument('--zip', help='path to zip file')
    parser.add_argument('--name', help='optional name for folder')
    args = parser.parse_args()

    if args.git:
        repo_path = clone_git_repo(args.git, dest_name=args.name)
        repo_ref = args.git
    elif args.zip:
        repo_path = unzip_repo(args.zip, dest_name=args.name)
        repo_ref = args.zip
    else:
        parser.error("Provide --git or --zip")

    report = analyze(repo_path, repo_ref)
    print("Done. Transport:", report["transport"])

if __name__ == "__main__":
    main()
