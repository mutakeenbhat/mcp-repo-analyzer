# MCP Repository Analyzer

A lightweight repository analyzer that inspects Git or ZIP-based codebases and produces an **MCP-compatible JSON analysis report**.  
The analyzer identifies:

- Supported transport types (HTTP, WebSocket, SSE, Stdio)
- Tools (Python functions, JS exported functions)
- Run template / startup command
- Evidence for all detections
- Notes & metadata about the repository

This project fulfills the requirements of the **MCP Internship Assignment**.

---

##  Features

###  Git Repository Cloning  
Automatically clones a GitHub repository using `gitpython`.

###  ZIP File Extraction  
(Feature available but optional for this assignment.)

### File Indexing  
Scans the entire repository:
- Detects file types
- Reads content safely
- Captures languages, extensions, and paths

###  Transport Detection  
Identifies communication patterns:
- HTTP servers (Flask, FastAPI, Express)
- WebSockets
- SSE
- Command-line / stdio

### Tool Extraction  
Extracts potential MCP tools:
- Python functions via AST parsing  
- JavaScript exported functions

###  Run Template Inference  
Heuristics to find:
- `uvicorn` startup commands  
- Flask run commands  
- npm scripts  
- README-based hints

###  MCP JSON Report  
Outputs a JSON analysis file:

