run:
	pdm run python src/tenpo/__main__.py

test:
	pdm run pytest -rP tests

dev:
	pdm run nvim src/tenpo/__main__.py
