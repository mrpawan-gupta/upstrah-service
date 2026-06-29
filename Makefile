up:
	docker-compose up

clean-containers:
	docker container prune -f || true
	docker rm -f $$(docker ps -aq) || true

clean-images:
	docker image prune -af || true
	docker rmi -f $$(docker images -q) || true

clean: clean-containers clean-images

# ─── Local dev ───────────────────────────────────────────────────────────────

run:
	cd src && uvicorn upstrah.asgi:app --reload --host 127.0.0.1 --port 8000

celery-worker:
	cd src && celery -A upstrah worker -l info --pool=prefork --concurrency=4

celery-beat:
	cd src && celery -A upstrah beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

migrate:
	$(ENV_VARS) venv/bin/python src/manage.py migrate

makemigrations:
	$(ENV_VARS) venv/bin/python src/manage.py makemigrations

showmigrations:
	$(ENV_VARS) venv/bin/python src/manage.py showmigrations

shell:
	$(ENV_VARS) venv/bin/python src/manage.py shell_plus

dbshell:
	$(ENV_VARS) venv/bin/python src/manage.py dbshell

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	PYTHONPATH=src venv/bin/python -m pytest src/ --maxfail=0

test-fast:
	PYTHONPATH=src venv/bin/python -m pytest src/ -m "not slow" --maxfail=0

# ─── Code quality ────────────────────────────────────────────────────────────

install-hooks:
	pre-commit install
	pre-commit autoupdate

secrets-check:
	detect-secrets scan --baseline .secrets.baseline

pre-push:
	ruff check --fix .
	ruff format .
	pre-commit run --all-files
