venv: requirements.txt setup.py
	virtualenv venv
	venv/bin/pip install -r requirements.txt
	venv/bin/pip install -e .

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

test: venv
	venv/bin/pytest --tb=short -vsx tests/

test_%: venv
	venv/bin/pytest --tb=short -vsx --pdb -k $@ tests/

iblm: isort black lint mypy
