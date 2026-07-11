.PHONY: server ui

server:
	uv run uvicorn backend.main:app --reload

ui:
	uv run streamlit run frontend/streamlit/app.py

tg:
	uv run python -m frontend.telegram.bot