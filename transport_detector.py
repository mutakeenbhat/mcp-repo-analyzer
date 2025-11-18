# transport_detector.py
import re

TRANSPORTS = ["stdio", "websocket", "http", "sse"]

def detect_transport(files):
    evidence = []
    scores = {t: 0 for t in TRANSPORTS}

    for f in files:
        c = f["content"].lower()
        p = f["path"]

        if "flask" in c or "express" in c or "fastapi" in c:
            scores["http"] += 1
            evidence.append(f"HTTP pattern in {p}")

        if "websocket" in c or "socket.io" in c:
            scores["websocket"] += 1
            evidence.append(f"WS pattern in {p}")

        if "eventsource" in c or "text/event-stream" in c:
            scores["sse"] += 1
            evidence.append(f"SSE pattern in {p}")

        if "sys.stdin" in c or "argparse" in c:
            scores["stdio"] += 1
            evidence.append(f"CLI pattern in {p}")

    best = max(scores, key=scores.get)

    return {
        "type": best,
        "confidence": 1.0 if scores[best] > 0 else 0.1,
        "evidence": evidence
    }
