# tool_extractor.py
"""
Tool extractor upgraded with embeddings (Option B).
If sentence-transformers is installed and the model can be loaded, ML-based
predictions (description, best-matching template, confidence) will be produced.
Otherwise falls back to heuristic detection.

Produces tool objects matching the MCP assignment fields:
- name, description, input_schema, output_schema,
  predicted_code_snippet, payload_shape, explanation,
  possible_syscalls, confidence, evidence, predicted_filename
"""
import ast
import re
from typing import List, Dict, Any
from pathlib import Path

from ml_utils import EmbeddingModel, scale_confidence

# instantiate model (may be None if model not available)
_EMB = EmbeddingModel()

# Simple templates for likely tool purposes — used for nearest-neighbor matching.
_TEMPLATES = [
    "compute cryptographic hash of input data",
    "read a file from disk and return its contents",
    "write data to a file",
    "make an HTTP request to an external API",
    "parse JSON input and validate fields",
    "validate and sanitize user input",
    "authenticate a user and return a token",
    "send an email notification",
    "execute a shell command",
    "list files in a directory",
    "process image data (resize, crop, convert)",
    "perform database query and return records",
    "serialize object to JSON",
    "deserialize JSON to object and validate",
    "stream data over websocket",
    "handle a HTTP route request and return response",
    "cache results to disk or memory",
    "compute statistics (mean, median, stddev) on numeric data"
]
# prepare templates embeddings if model exists
if _EMB.available():
    _EMB.prepare_templates(_TEMPLATES)

# helper: map simple annotation names or default values to JSON types
_TYPE_MAP = {
    'str': 'string', 'int': 'integer', 'float': 'number', 'bool': 'boolean',
    'list': 'array', 'dict': 'object'
}

def _map_annotation_to_simple(ann: Any) -> str:
    if not ann:
        return "string"
    s = str(ann).lower()
    for k, v in _TYPE_MAP.items():
        if k in s:
            return v
    # fallback
    return "string"

def detect_syscalls_from_code(code: str) -> List[Dict[str, str]]:
    syscalls = []
    if re.search(r'\bos\.system\b|\bsubprocess\.run\b|\bsubprocess\.Popen\b', code):
        syscalls.append({"syscall": "execve/system", "reason": "calls to subprocess or os.system"})
    if re.search(r'\bopen\(|\bfopen\(', code):
        syscalls.append({"syscall": "open/read/write", "reason": "file open calls found"})
    if re.search(r'\bsocket\(|listen\(|accept\(', code):
        syscalls.append({"syscall": "socket", "reason": "socket operations found"})
    if re.search(r'\brequests\.get\b|\brequests\.post\b|urllib', code):
        syscalls.append({"syscall": "network", "reason": "HTTP requests to external services"})
    return syscalls

def _infer_input_schema_from_ast(node: ast.FunctionDef, source: str) -> Dict[str, Any]:
    props = {}
    required = []

    # Build mapping of which args have defaults
    defaults = node.args.defaults or []
    args = node.args.args

    num_args = len(args)
    num_defaults = len(defaults)

    # Defaults correspond to the LAST N args
    default_arg_names = [
        args[i].arg for i in range(num_args - num_defaults, num_args)
    ] if num_defaults > 0 else []

    for arg in args:
        if arg.arg == 'self':
            continue

        # Extract annotation text if available
        ann = None
        try:
            if arg.annotation:
                ann = ast.get_source_segment(source, arg.annotation)
        except Exception:
            ann = None

        type_hint = _map_annotation_to_simple(ann)

        # Check if argument has default value
        has_default = arg.arg in default_arg_names

        props[arg.arg] = {
            "type": type_hint,
            "required": not has_default
        }

    schema = {
        "type": "object",
        "properties": props,
        "required": [name for name, v in props.items() if v.get("required")]
    }

    return schema


def _infer_output_schema_from_ast(node: ast.FunctionDef, source: str) -> Dict[str, Any]:
    # try returns annotation
    ret_ann = None
    try:
        ret_ann = ast.get_source_segment(source, node.returns) if node.returns else None
    except Exception:
        ret_ann = None
    if ret_ann:
        t = _map_annotation_to_simple(ret_ann)
        return {"type": t}
    # otherwise search for dict literal in return statements
    for n in ast.walk(node):
        if isinstance(n, ast.Return):
            if isinstance(n.value, ast.Dict):
                props = {}
                for k, v in zip(n.value.keys, n.value.values):
                    if isinstance(k, ast.Constant):
                        keyname = k.value
                        # infer type from value node
                        if isinstance(v, ast.Constant):
                            t = type(v.value).__name__
                            props[keyname] = {"type": _TYPE_MAP.get(t, "string")}
                        else:
                            props[keyname] = {"type": "string"}
                return {"type": "object", "properties": props, "required": list(props.keys())}
    # fallback
    return {"type": "object"}

def extract_python_tools(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tools = []
    for f in files:
        if f.get("language") != "python":
            continue
        path = f["path"]
        src = f["content"]
        try:
            tree = ast.parse(src)
        except Exception:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                snippet = ast.get_source_segment(src, node) or (node.name + "(...)")
                # build ML prompt/context: function signature + first 20 lines
                context = snippet + "\n\n" + "\n".join(src.splitlines()[:40])
                description = None
                template_match = None
                sim_score = 0.0
                if _EMB.available():
                    try:
                        template_match, sim_score = _EMB.best_template(context)
                        # short description formed from template + function name
                        description = f"{template_match}. Function `{node.name}`."
                    except Exception:
                        description = f"Function `{node.name}` (heuristic description)."
                        template_match = None
                        sim_score = 0.0
                else:
                    # fallback heuristic description
                    description = f"Function `{node.name}` (heuristic description)."
                confidence = scale_confidence(sim_score) if sim_score else 0.35

                input_schema = _infer_input_schema_from_ast(node, src)
                output_schema = _infer_output_schema_from_ast(node, src)
                payload_shape = {
                    "request": {k: v.get("type", "string") for k, v in input_schema.get("properties", {}).items()},
                    "response": output_schema
                }
                possible_syscalls = detect_syscalls_from_code(snippet + "\n" + src)
                evidence = [f"function {node.name} in {path}"]  # add more evidence below
                if template_match:
                    evidence.append(f"matched template: {template_match} (sim={sim_score:.2f})")

                tools.append({
                    "name": node.name,
                    "description": description,
                    "predicted_filename": path,
                    "predicted_code_snippet": snippet,
                    "input_schema": input_schema,
                    "output_schema": output_schema,
                    "payload_shape": payload_shape,
                    "explanation": f"Detected Python function `{node.name}` in {path}",
                    "possible_syscalls": possible_syscalls,
                    "confidence": confidence,
                    "evidence": evidence
                })
    return tools

def extract_js_tools(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tools = []
    export_re = re.compile(r'(?:module\.exports|exports)\s*=\s*(\w+)|export function (\w+)|export default function (\w+)|exports\.(\w+)\s*=')
    for f in files:
        if f.get("language") not in ('javascript', 'typescript'):
            continue
        p = f["path"]
        c = f["content"]
        for m in export_re.finditer(c):
            name = next((g for g in m.groups() if g), None) or Path(p).stem
            snippet = "<js snippet unavailable>"
            # try to grab surrounding lines
            lines = c.splitlines()
            for i, L in enumerate(lines):
                if name and name in L and ('function' in L or '=>' in L):
                    snippet = "\n".join(lines[max(0, i-4):i+4])
                    break
            description = f"Exported JS function {name}"
            sim = 0.0
            if _EMB.available():
                try:
                    template_match, sim = _EMB.best_template(snippet + "\n" + c[:400])
                    description = f"{template_match}. Function `{name}`."
                except Exception:
                    pass
            confidence = scale_confidence(sim) if sim else 0.35
            input_schema = {"type": "object", "properties": {}}
            output_schema = {"type": "object"}
            payload_shape = {"request": {}, "response": {}}
            possible_syscalls = detect_syscalls_from_code(snippet + "\n" + c[:400])
            evidence = [f"exported {name} in {p}"]
            if sim:
                evidence.append(f"matched template: {template_match} (sim={sim:.2f})")
            tools.append({
                "name": name,
                "description": description,
                "predicted_filename": p,
                "predicted_code_snippet": snippet,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "payload_shape": payload_shape,
                "explanation": f"Exported function `{name}` in {p}",
                "possible_syscalls": possible_syscalls,
                "confidence": confidence,
                "evidence": evidence
            })
    return tools

def extract_tools(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tools = []
    tools.extend(extract_python_tools(files))
    tools.extend(extract_js_tools(files))
    # Also detect heuristic tools: files under tools/ or cli entrypoints
    for f in files:
        p = f.get("path", "")
        if '/tools/' in p or p.lower().startswith('tools') or 'cli' in p.lower() or 'commands' in p.lower():
            if not any(t["predicted_filename"] == p for t in tools):
                snippet = "\n".join(f.get("content","").splitlines()[:30])
                sim = 0.0
                template_match = None
                if _EMB.available():
                    try:
                        template_match, sim = _EMB.best_template(snippet)
                    except Exception:
                        template_match = None
                desc = f"Inferred tool from file {p}"
                if template_match:
                    desc = f"{template_match}. File `{p}`."
                tools.append({
                    "name": Path(p).stem,
                    "description": desc,
                    "predicted_filename": p,
                    "predicted_code_snippet": snippet,
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "payload_shape": {"request": {}, "response": {}},
                    "explanation": f"Inferred tool from tools-like file {p}",
                    "possible_syscalls": detect_syscalls_from_code(snippet),
                    "confidence": scale_confidence(sim) if sim else 0.35,
                    "evidence": [f"file {p} exists under tools/"]
                })
    return tools
