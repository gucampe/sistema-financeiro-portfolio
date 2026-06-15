tailwind-watch:
	npm run tailwind:watch

django-runserver:
	python3 manage.py runserver 0.0.0.0:8000

dev:
	make -j 2 tailwind-watch django-runserver