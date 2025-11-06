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

## voice-install: install Node.js dependencies for voice interface
.PHONY: voice-install
voice-install:
	cd voice-interview-react && npm install

## voice-build: build React.js voice interface component
.PHONY: voice-build
voice-build:
	cd voice-interview-react && npm run build

## voice-build-dev: build React.js voice interface component in development mode
.PHONY: voice-build-dev
voice-build-dev:
	cd voice-interview-react && npm run build:dev

## voice-watch: build React.js voice interface component in watch mode
.PHONY: voice-watch
voice-watch:
	cd voice-interview-react && npm run build:watch

## voice-clean: clean built voice interface files
.PHONY: voice-clean
voice-clean:
	cd voice-interview-react && npm run clean

## baseimage: build base image
.PHONY: baseimage
baseimage:
	docker build -t ai-chatbot.base:0.1.0 -f Dockerfile.base --platform ${platform} .

## web-build: build the web container
.PHONY: web-build
web-build: voice-build
	cd ../; docker build -f ./web/Dockerfile -t scribe-web --platform ${platform} .; \

## start-web:
.PHONY: start-web
start-web: web-build
	docker compose up -d

## up: run the app locally using docker compose and show logs
.PHONY: up
up: start-web
	docker compose logs -f

## down: stop the app
.PHONY: down
down:
	docker compose down

## deploy: build and deploy container:
.PHONY: deploy
deploy:
	./deploy.sh ${app} ${platform}
