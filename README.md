uv venv
source .venv/bin/activate
uv run uvicorn app.main:app --reload
http://127.0.0.1:8000
