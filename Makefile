ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python.exe
else
PY := .venv/bin/python
endif

.PHONY: setup dev backend frontend test circulars

setup:
	python -m venv .venv
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	bash scripts/dev.sh

backend:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev -- --port 3000

test:
	cd backend && ../$(PY) -m pytest -q

circulars:
	$(PY) scripts/download_circulars.py
