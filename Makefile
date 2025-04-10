venv:
	virtualenv venv
	venv/bin/pip install -r requirements.txt

run:
	chpst -e .env venv/bin/uvicorn --reload --port 8881 backend.app:app

black:
	venv/bin/black backend/
