tailwind-watch:
	npm run tailwind:watch

django-runserver:
	python3 manage.py runserver

dev:
	make -j 2 tailwind-watch django-runserver