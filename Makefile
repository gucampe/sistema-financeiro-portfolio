PYTHON ?= python3

tailwind-watch:
	npm run tailwind:watch

django-runserver:
	$(PYTHON) manage.py runserver 0.0.0.0:8000

dev:
	make -j 2 tailwind-watch django-runserver

test: test-unit

test-unit:
	$(PYTHON) -m pytest -m "not performance_extended" --ignore=e2e

test-e2e-mvp:
	$(PYTHON) -m pytest e2e/specs/mvp e2e/specs/integrity -m mvp --browser chromium

test-e2e-smoke:
	$(PYTHON) -m pytest e2e/specs/contas e2e/specs/categorias e2e/specs/usuarios -m cadastro_smoke --browser chromium

test-e2e:
	$(PYTHON) -m pytest e2e/specs -m "not synthetic" --browser chromium

ajuda-screenshots:
	$(PYTHON) -m pytest e2e/specs/ajuda/test_gerar_screenshots.py --browser chromium -s
