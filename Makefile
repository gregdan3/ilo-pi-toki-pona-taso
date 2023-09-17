# ILO=podman-compose
ILO=docker compose

init:
	pdm sync --dev

test:
	pdm run pytest tests/ -m "not skip"

profile:
	pdm run python -m kernprof -lv tests/profile.py

dev:
	pdm run ${EDITOR} src/tenpo/__main__.py

local:
	pdm run python -m tenpo

build:
	${ILO} build

up:
	${ILO} up -d

stop:
	${ILO} stop

down:
	${ILO} down

push:
	echo "Not implemented!"
	exit 1
	${ILO} push

logs:
	${ILO} logs
