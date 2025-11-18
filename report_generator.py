# report_generator.py
import json
from datetime import datetime

def make_report(repo_ref, transport, tools, run_template, notes):
    return {
        "repo": repo_ref,
        "analysis_time": datetime.now().isoformat(),
        "transport": transport,
        "tools": tools,
        "run_template": run_template,
        "notes": notes
    }

def save_report(report, out_path="mcp_analysis_report.json"):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_path}")
