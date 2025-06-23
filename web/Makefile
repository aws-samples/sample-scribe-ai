app := scribe
platform := linux/arm64

all: help

.PHONY: help
help: Makefile
	@echo
	@echo " Choose a make command to run"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' |  sed -e 's/^/ /'
	@echo

## init: run this once to initialize a new python project
.PHONY: init
init:
	python3 -m venv .venv
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
	git ls-files | grep -v iac | entr -r python main.py

## baseimage: build base image
.PHONY: baseimage
baseimage:
	docker build -t ai-chatbot.base:0.1.0 -f Dockerfile.base --platform ${platform} .

## deploy: build and deploy container:
.PHONY: deploy
deploy:
	./deploy.sh ${app} ${platform}

## up: run the app locally using docker compose
.PHONY: up
up:
	cd ../; docker build -f ./web/Dockerfile -t scribe-web --platform ${platform} .; \
	cd web; docker compose up -d && docker compose logs -f

## down: stop the app
.PHONY: down
down:
	docker compose down

## start-docker: run local project using docker compose
.PHONY: start-docker
start-docker:
	clear
	@echo ""
	git ls-files | grep -v iac | entr -r make up
