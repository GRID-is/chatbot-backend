venv:
	virtualenv venv
	venv/bin/pip install -r requirements.txt

run: venv
	chpst -e .env venv/bin/uvicorn --reload --port 8881 backend.app:app

black: venv
	venv/bin/black backend/

mypy: venv
	venv/bin/mypy --check-untyped-defs backend/
