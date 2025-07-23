# Development Guidelines

## Git Workflow

### Branch Management
- **Always** create a new git branch before making any changes to files
- Use descriptive branch names that reflect the feature or fix being implemented

### Commit Standards
- Write commit messages with a short first line (no wrapping)
- Follow with detailed summary lines explaining what was done
- **No emojis** in the first line, but feel free to use them in the summary
- Ensure code compiles and passes tests before committing

### Pre-commit Checks
- Run linting tools and tests before committing
- For Terraform changes: Always run `make check` in the `iac/` directory before committing

## Code Style Guidelines

### Python Conventions
- **Import Order**: Standard library first, third-party second, local modules last
- **Type Annotations**: Use type hints for function parameters and return values
- **Naming Conventions**:
  - `PascalCase` for classes
  - `snake_case` for functions and variables
  - `UPPER_SNAKE_CASE` for constants
- **Indentation**: 4 spaces (no tabs)
- **String Quotes**: Prefer single quotes, use f-strings for formatting
- **Line Length**: Keep under 100 characters
- **Privacy**: Prefix private variables with underscore (`_variable_name`)

### Error Handling
- Use specific exception types rather than generic `Exception`
- Log exceptions with descriptive messages
- Include context about what operation was being performed

### Documentation
- Use docstrings for all classes and functions
- Include parameter types and return value descriptions
- Document any side effects or important behavior

### Constants and Enums
- Use Enums for constants and status values
- Define constants at module level with descriptive names

## Testing and Quality Assurance

### Before Committing
1. Ensure code compiles (if applicable)
2. Run any existing linting tools
3. Execute test suites
4. For Terraform: Run `make check` for pre-commit hooks

### Local Development Cycle
1. Create new branch: `git checkout -b feature/your-feature-name`
2. Make changes following code style guidelines
3. Install dependencies: `make install <package>` (if needed)
4. Build and test locally: `cd web && make baseimage && make up`
5. Run tests and linting
6. Commit with proper message format
7. Push and create pull request

## File Organization Principles

### Module Structure
- Keep related functionality together in logical modules
- Use clear, descriptive file and function names
- Separate concerns between different layers (data, business logic, presentation)

### Configuration Management
- All configuration via environment variables
- Provide sensible defaults in code
- Document required vs optional environment variables