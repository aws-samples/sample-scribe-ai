app := scribe-events
platform := linux/arm64

all: help

.PHONY: help
help: Makefile
	@echo
	@echo " Choose a make command to run"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' |  sed -e 's/^/ /'
	@echo

## init: initialize a new python project
.PHONY: init
init:
	python -m venv .venv
	direnv allow .

## install: add a new package (make install <package>), or install all project dependencies from piplock.txt (make install)
.PHONY: install
install:
	python -m pip install --upgrade pip
	@if [ -z "$(filter-out install,$(MAKECMDGOALS))" ]; then \
		echo "Installing dependencies from piplock.txt"; \
		pip install -r piplock.txt; \
	else \
		pkg="$(filter-out install,$(MAKECMDGOALS))"; \
		echo "Adding package $$pkg to requirements.txt"; \
		grep -q "^$$pkg$$" requirements.txt || echo "$$pkg" >> requirements.txt; \
		pip install $$pkg; \
		pip install -r requirements.txt; \
		pip freeze > piplock.txt; \
	fi

# Empty rule to handle package name argument
%:
	@:

## start: run local project
.PHONY: start
start:
	clear
	@echo ""
	python -u main.py

## build-container: package app for aws lambda using container
.PHONY: build-container
build-container:
	cd ../; docker build -t lambda -f ./events/Dockerfile .

## start-container: run local project in container
.PHONY: start-container
start-container: build-container
	clear
	@echo ""
  docker run -it --rm -p 8080:8080 lambda

## up: run the app locally using docker compose
.PHONY: up
up:
	docker compose build && docker compose up -d && docker compose logs -f

## down: stop the app
.PHONY: down
down:
	docker compose down

## deploy: build and deploy container (make deploy app=scribe-events)
.PHONY: deploy
deploy:
	./deploy.sh ${app} ${platform}
