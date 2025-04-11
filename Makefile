venv:
	virtualenv venv
	venv/bin/pip install -r requirements.txt

run: venv
	chpst -e .env venv/bin/uvicorn --reload --port 8881 backend.app:app

black: venv
	venv/bin/black backend/

mypy: venv
	venv/bin/mypy --check-untyped-defs backend/

lint: venv
	venv/bin/ruff check --fix backend/

isort: venv
	venv/bin/ruff check --select I --fix
	venv/bin/ruff format

iblm: isort black lint mypy
