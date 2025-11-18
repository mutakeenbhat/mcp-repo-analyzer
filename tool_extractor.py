# tool_extractor.py
import ast
import re
from pathlib import Path

def extract_python_tools(files):
    tools = []
    for f in files:
        if f["language"] != "python":
            continue
        path = f["path"]
        code = f["content"]

        try:
            tree = ast.parse(code)
        except:
            continue

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                snippet = ast.get_source_segment(code, node)
                tools.append({
                    "name": node.name,
                    "predicted_filename": path,
                    "predicted_code_snippet": snippet,
                    "input_schema": {},
                    "output_schema": {},
                    "explanation": f"Found python function {node.name} in {path}",
                    "possible_syscalls": [],
                    "confidence": 0.6,
                    "evidence": [f"Function {node.name} in {path}"]
                })
    return tools

def extract_js_tools(files):
    tools = []
    for f in files:
        if f["language"] not in ("javascript", "typescript"):
            continue

        code = f["content"]
        path = f["path"]

        matches = re.findall(r"export function (\w+)", code)
        for name in matches:
            tools.append({
                "name": name,
                "predicted_filename": path,
                "predicted_code_snippet": "<js snippet>",
                "input_schema": {},
                "output_schema": {},
                "explanation": f"Exported JS function {name} in {path}",
                "possible_syscalls": [],
                "confidence": 0.5,
                "evidence": [f"export function {name}"]
            })
    return tools

def extract_tools(files):
    tools = []
    tools.extend(extract_python_tools(files))
    tools.extend(extract_js_tools(files))
    return tools
