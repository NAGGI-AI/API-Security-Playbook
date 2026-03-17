from fastapi.responses import FileResponse
import os
from fastapi import FastAPI
from pydantic import BaseModel
import json, os, re
from fastapi import HTTPException
from typing import List, Optional

APP_NAME = "API security playbook agent"

# Load KB in memory
KB_DIR = os.path.join(os.path.dirname(__file__), 'kb')
KB = {}
for fname in os.listdir(KB_DIR):
    if fname.endswith('.json'):
        with open(os.path.join(KB_DIR, fname), 'r', encoding='utf-8') as f:
            doc = json.load(f)
            KB[doc['id']] = doc

SECTIONS_MAP = {
    "what": "what_it_means",
    "animated_example": "animated_example",
    "quick_checks": "quick_checks",
    "how_to_test": "how_to_test",
    "expected_outcomes": "expected_outcomes",
    "minimal_example": "minimal_example"
}

app = FastAPI(title=APP_NAME)

class Query(BaseModel):
    question: str
    endpoint: Optional[str] = None
    risks: Optional[List[str]] = None  # e.g., ["API1","API3"]


def format_response(doc, endpoint=None, question=None):
    parts = []
    parts.append(f"**Risk:** {doc['id']} - {doc['name']}")
    parts.append(f"**What it means**\n{doc['what_it_means']}")
    parts.append(f"**Animated example**\n{doc['animated_example']}")
    parts.append("**Quick checks**\n- " + "\n- ".join(doc['quick_checks']))
    h2t = "- " + "\n- ".join(doc['how_to_test'])
    if endpoint:
        # Light tailoring: inject endpoint into the first test line if it looks like a path placeholder
        tailored = []
        for i, line in enumerate(doc['how_to_test']):
            if i == 0:
                tailored.append(re.sub(r"/objects/\{[^}]+\}", endpoint, line))
            else:
                tailored.append(line)
        h2t = "- " + "\n- ".join(tailored)
    parts.append(f"**How to test**\n{h2t}")
    parts.append("**Expected outcomes**\n- " + "\n- ".join(doc['expected_outcomes']))
    parts.append(f"**Minimal example**\n{doc['minimal_example']}")
    if endpoint:
        parts.append(f"**Tailored steps (endpoint: {endpoint})**\n- Ensure correct authz on {endpoint}.\n- Negative test: attempt cross-tenant/object access on {endpoint} and expect 403/404 as applicable.\n- Log denied attempts with actor and object identifiers.")
    return "\n\n".join(parts)


def retrieve_docs(question: str, risks: Optional[List[str]]):
    docs = []
    if risks:
        for r in risks:
            if r in KB:
                docs.append(KB[r])
    else:
        # naive keyword routing
        q = question.lower()
        mapping = [
            ("bola", "API1"), ("object level", "API1"),
            ("auth", "API2"), ("authentication", "API2"),
            ("property", "API3"), ("mass assignment", "API3"), ("excessive data", "API3"),
            ("rate", "API4"), ("quota", "API4"), ("429", "API4"), ("413", "API4"),
            ("bfla", "API5"), ("function level", "API5"), ("admin", "API5"),
            ("business flow", "API6"), ("checkout", "API6"),
            ("ssrf", "API7"), ("metadata", "API7"),
            ("cors", "API8"), ("misconfig", "API8"), ("headers", "API8"),
            ("inventory", "API9"), ("shadow", "API9"), ("version", "API9"),
            ("upstream", "API10"), ("unsafe consumption", "API10"), ("circuit breaker", "API10")
        ]
        seen = set()
        for key, rid in mapping:
            if key in q and rid not in seen:
                docs.append(KB[rid])
                seen.add(rid)
        if not docs:
            # default to overview of all
            docs = [KB[k] for k in sorted(KB.keys())]
    return docs[:3]


@app.post('/ask')
async def ask(q: Query):
    docs = retrieve_docs(q.question, q.risks)
    answers = [format_response(doc, endpoint=q.endpoint, question=q.question) for doc in docs]
    return {"agent": APP_NAME, "answers": answers, "supported_risks": [d['id'] for d in docs]}

@app.get("/risk")
async def get_risk(id: str, section: str | None = None):
    """
    Returns Playbook content for a specific risk id (e.g., API4).
    If 'section' is provided, returns only that section.
    Sections: what | animated_example | quick_checks | how_to_test | expected_outcomes | minimal_example
    """
    if id not in KB:
        raise HTTPException(status_code=404, detail=f"Unknown risk id: {id}")
    doc = KB[id]

    # All sections (full readout)
    full = {
        "id": doc["id"],
        "name": doc["name"],
        "what": doc["what_it_means"],
        "animated_example": doc["animated_example"],
        "quick_checks": doc["quick_checks"],
        "how_to_test": doc["how_to_test"],
        "expected_outcomes": doc["expected_outcomes"],
        "minimal_example": doc["minimal_example"]
    }

    if not section:
        return {"risk": full, "source": "Playbook"}  # (Playbook) [1](blob:https://m365.cloud.microsoft/8f0b9d5b-6a6f-4abe-870b-da4a4ff98522)

    key = SECTIONS_MAP.get(section)
    if not key:
        raise HTTPException(status_code=400, detail=f"Invalid section. Use one of: {', '.join(SECTIONS_MAP.keys())}")
    return {"risk": {"id": doc["id"], "name": doc["name"], section: doc[key]}, "source": "Playbook"}  # (Playbook) [1](blob:https://m365.cloud.microsoft/8f0b9d5b-6a6f-4abe-870b-da4a4ff98522)

@app.get("/")
async def home():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    return FileResponse(ui_path)