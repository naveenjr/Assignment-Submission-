install:
	uv sync
api:
	uv run uvicorn apps.backend.main:app --port 8000
ui:
	uv run streamlit run apps/frontend/app.py
test:
	uv run pytest tests -q
