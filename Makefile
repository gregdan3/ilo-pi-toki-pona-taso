# MAIN=podman
# SUB=podman-compose
MAIN=docker
SUB=docker compose

init:
	pdm install

test:
	pdm run pytest -vvrP tests

dev:
	pdm run nvim src/tenpo/__main__.py

build:
	${SUB} build

up:
	${SUB} up -d

local:
	pdm run python -m tenpo

stop:
	${SUB} stop

down:
	${SUB} down

logs:
	${SUB} logs
