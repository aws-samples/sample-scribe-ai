# Scribe AI Project Guidelines

## Instructions

Before making any changes to files in the user's workspace, always first checkout a new git branch.

After making changes, be sure to ensure that the code compiles (if working on a compiled language) and run any linting tools or tests that the user has setup.

When you're finished making all changes, git commit your changes with a commit message where the first line is short enough to not wrap, followed by more lines that clearly summarize what you did. Don't use emojis in the 1st line, but feel free to use them in the summary when appropriate.


## Build/Test/Lint Commands

- Install dependencies: `make install <package>`
- Build base image (after installing dependencies): `cd web && make baseimage`
- Run locally: `cd web && make up`
- Stop local environment: `cd web && make down`


## Code Style Guidelines

- **Imports**: Standard library first, third-party second, local modules last
- **Type Annotations**: Use type hints for function parameters and return values
- **Naming**: PascalCase for classes, snake_case for functions/variables, UPPER_SNAKE_CASE for constants
- **Indentation**: 4 spaces
- **String Quotes**: Prefer single quotes with f-strings for formatting
- **Line Length**: Keep under 100 characters
- **Error Handling**: Use specific exception types, log exceptions with descriptive messages
- **Documentation**: Use docstrings for classes and functions
- **Enums**: Use for constants and status values
- **Privacy**: Prefix private variables with underscore (_variable_name)

## Terraform

When writing/updating Terraform code, always run `make check` which runs pre-commit hooks like linting, document generation, etc., before committing changes to git.
