app := scribe-dev-voice
platform := linux/arm64

all: help

.PHONY: help
help: Makefile
	@echo
	@echo " Choose a make command to run"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' |  sed -e 's/^/ /'
	@echo

## install
.PHONY: install
install:
	npm install

## build: build the lambda function for deployment
.PHONY: build
build:
	@echo "build the lambda function for deployment"
	npm ci --only=production

## clean: Clean build artifacts and dependencies
.PHONY: clean
clean:
	@echo "Clean build artifacts and dependencies"
	npm run clean
	rm -rf node_modules/
	rm -f package-lock.json

## deploy: build and deploy container (make deploy app=scribe-voice)
.PHONY: deploy
deploy:
	./deploy.sh ${app} ${platform}
