# Contributing to Project Kodak

Thank you for your interest in contributing to Project Kodak! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository** and clone it locally
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Set up your environment**:
   - Copy `config.yaml.example` to `config.yaml`
   - Configure your base currency and directory paths
4. **Run tests** to ensure everything works: `pytest tests/`

## Development Workflow

### Code Style

- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Add docstrings to public functions
- Use logging instead of print() statements for debugging

### Making Changes

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the code style guidelines

3. Run the tests:
   ```bash
   pytest tests/ -v
   ```

4. Commit your changes with a descriptive message:
   ```bash
   git commit -m "feat: add support for new broker"
   ```

5. Push to your fork and create a Pull Request

### Commit Message Format

We use conventional commits:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Project Structure

```
project-kodak/
├── kodak/                # Main package
│   ├── shared/           # Core utilities (db, calculations, market_data)
│   ├── pipeline/         # Data ingestion & enrichment
│   │   └── parsers/      # Broker-specific parsers
│   ├── cli/              # Terminal analysis tools
│   ├── dashboard/        # Streamlit UI
│   ├── setup/            # Database initialization
│   └── maintenance/      # Helper scripts
├── data/                 # Transaction data (not in git)
├── tests/                # Unit tests
├── workflows/            # PowerShell automation
└── config.yaml           # Configuration
```

## Adding a New Broker Parser

1. Create a new file in `kodak/pipeline/parsers/`
2. Import shared utilities:
   ```python
   from kodak.shared.parser_utils import create_empty_transaction, validate_parser_output
   from kodak.shared.utils import clean_num
   ```

3. Implement the `parse(file_path)` function that returns a list of transaction dictionaries

4. Use `create_empty_transaction()` as a template and populate fields

5. Validate output with `validate_parser_output()` before returning

6. Test with `python -m kodak.maintenance.test_parser <broker> path/to/sample.csv`

7. Add tests in `tests/test_parsers.py`

## Areas for Contribution

### High Priority
- Additional broker parsers (Interactive Brokers, Degiro, etc.)
- Improved error handling and user feedback
- Performance optimizations for large portfolios

### Medium Priority
- Additional dashboard visualizations
- Export functionality (CSV, PDF reports)
- Multi-currency improvements

### Documentation
- Usage tutorials
- API documentation
- Video walkthroughs

## Testing

Run the full test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=kodak --cov-report=term-missing
```

## Questions?

Open an issue if you have questions or need clarification on anything.
