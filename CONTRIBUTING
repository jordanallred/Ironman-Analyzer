# Contributing to Ironman Race Analyzer

Thank you for considering contributing to the Ironman Race Analyzer project! This document outlines the process for contributing to the project and provides guidelines to help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Submitting Contributions](#submitting-contributions)
- [Testing](#testing)
- [Style Guidelines](#style-guidelines)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please engage respectfully with other contributors, maintain a professional tone, and focus on creating a positive environment for everyone.

## Getting Started

1. **Fork the repository** to create your own copy on GitHub.
2. **Clone your fork** to your local machine.
3. **Create a new branch** for your contribution:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** and test them thoroughly.
5. **Commit your changes** with clear, descriptive commit messages.
6. **Push your branch** to your GitHub fork.
7. **Open a pull request** from your branch to the original repository.

## Development Environment

### Requirements

- Python 3.12+
- Development tools:
  - Ruff (linter and formatter)
  - pytest (testing framework)

### Setup

Install development dependencies:
   ```bash
   uv venv .venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

## Project Structure

```
ironman-analyzer/
├── analyze.py        # Main analysis TUI application
├── scraper.py        # Race results scraper
├── qualify.py        # Qualification slots scraper
├── results/          # Directory for race result JSON files
├── qualifying_slots.json  # Slot allocation data
├── selector.json     # Configuration for age groups and countries
├── pyproject.toml    # Project dependencies and metadata
├── tests/            # Test directory
└── docs/             # Documentation
```

### Core Modules

- **analyze.py**: The main application with the Textual-based TUI for analyzing race results.
- **scraper.py**: Scrapes race results from the Ironman website.
- **qualify.py**: Scrapes qualification slot information from the Ironman website.

## Submitting Contributions

### Types of Contributions

We welcome the following types of contributions:

- **Bug fixes**: Identify and resolve issues in the codebase.
- **Feature additions**: Implement new functionality.
- **Documentation improvements**: Enhance or correct documentation.
- **Performance optimizations**: Improve code efficiency.
- **UI enhancements**: Improve the user interface and experience.

### Pull Request Process

1. **Update documentation** if necessary.
2. **Add tests** for new functionality.
3. **Ensure all tests pass** before submitting.
4. **Describe your changes** in detail in the pull request description.
5. **Link relevant issues** that your PR addresses.
6. **Be responsive** to feedback and review comments.

## Testing

We use pytest for testing. To run tests:

```bash
pytest
```

When adding new features, please include appropriate tests. For bug fixes, add tests that reproduce the bug you're fixing.

### Test Structure

- Unit tests should be placed in `tests/` with the naming pattern `test_*.py`.
- Each function in the codebase should have corresponding tests.
- Mock external API calls to avoid hitting real services during testing.

## Style Guidelines

### Code Formatting and Linting

We use Ruff for both code formatting and linting. Before submitting your PR, format and lint your code:

```bash
# Format code
ruff format .

# Run linter
ruff check .

# Automatically fix fixable issues
ruff check --fix .
```

### Coding Conventions

- Use descriptive variable and function names.
- Include docstrings for all functions, classes, and modules.
- Follow PEP 8 guidelines.
- Keep functions focused on a single responsibility.
- Favor readability over cleverness.

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Start with a capital letter
- Be descriptive but concise
- Reference issues when relevant: "Fix #123: Add age group filtering"

## Issue Reporting

### Bug Reports

When submitting a bug report, please include:

1. A clear and descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Screenshots if applicable
6. Environment information (OS, Python version, etc.)

### Feature Requests

For feature requests, include:

1. A clear description of the feature
2. The rationale and use cases for the feature
3. Any relevant examples or mock-ups

## Data Handling

When working with real race data:

1. Do not commit personal data of athletes
2. Use anonymized examples for tests
3. Be respectful of copyright and terms of service when scraping data

## Thank You!

Your contributions help make this project better. We appreciate your time and effort!