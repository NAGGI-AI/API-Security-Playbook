
# API security playbook agent (MVP)

This is a lightweight chat-style agent that serves OWASP API Security Top 10 (2023) guidance from an embedded knowledge base, with tailored test steps per endpoint.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Test with curl:

```bash
curl -s -X POST http://localhost:8000/ask   -H 'Content-Type: application/json'   -d '{"question":"Explain BOLA with checks","endpoint":"/orders/{id}","risks":["API1"]}' | jq
```

## Structure
- `kb/` – JSON knowledge files for API1..API10.
- `app.py` – FastAPI service with naive keyword-based retrieval (swap for your vector store later).
- `examples/postman_bola_collection.json` – Starter Postman tests for BOLA.

## Next steps
- Replace naive retrieval with Azure AI Search or your preferred vector store.
- Add an LLM layer if you want natural language synthesis (this MVP returns structured guidance directly from KB).
- Extend `/ask` to output Postman fragments for any risk on demand.
