# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Newsletter Summarizer - A Python CLI tool that fetches AI-focused newsletters from Gmail, analyzes them with LLMs (via OpenRouter by default), and generates concise summary reports for regular users.

## Common Development Commands

```bash
# Setup environment (Python 3.11 recommended)
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing

# Run the application
python main.py [options]

# Run all tests
pytest

# Run specific test file
pytest test_fetch_api.py
pytest test_e2e_cli.py

# Run specific test
pytest test_fetch_api.py::test_get_ai_newsletters_success

# Verify OpenRouter setup
python verify_openrouter.py

# Analyze API costs
python analyze_costs.py

# Review newsletter website mappings
python review_newsletter_websites.py

# Validate configuration
python config_validator.py
```

## High-Level Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Flow
1. **Authentication** (`auth.py`) - Handles Gmail OAuth using Google API credentials
2. **Email Fetching** (`fetch.py`) - Retrieves newsletters from Gmail with "ai-newsletter" label
3. **LLM Analysis** (`llm.py`) - Sends content to LLMs (OpenRouter/direct APIs) for analysis
4. **Report Generation** (`report.py`) - Creates markdown reports with summaries and insights

### Key Architectural Decisions

- **OpenRouter as Default**: All LLM calls route through OpenRouter by default for cost efficiency and tracking
- **Provider Abstraction**: Supports multiple LLM providers (OpenAI, Anthropic, Google) with consistent interface
- **Newsletter Website Caching**: Maintains `newsletter_websites.json` to cache and verify newsletter sources
- **Mock Data Support**: E2E tests and development can use `NEWSLETTER_SUMMARY_MOCK_DATA` env var
- **Cost Tracking**: OpenRouter usage logged to `openrouter_costs.json` for analysis

### Environment Configuration

Required `.env.local` file:
```
OPENROUTER_API_KEY=your_key_here  # Required
USE_OPENROUTER=true               # Default behavior
# Direct API keys only needed if USE_OPENROUTER=false
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### Model Selection Logic

The `--llm-provider` flag maps to specific models:
- With OpenRouter: `claude` → `anthropic/claude-sonnet-4`, `openai` → `openai/gpt-4.1-mini`
- Direct APIs: `claude` → `claude-3-7-sonnet-20250219`, `openai` → `gpt-4.1-2025-04-14`
- Custom models via `--model` parameter override these presets

### Testing Strategy

- **Unit Tests** (`test_fetch_api.py`): Mock Gmail API responses, test filtering logic
- **E2E Tests** (`test_e2e_cli.py`): Run full CLI with mock data, verify report generation
- Tests use monkeypatching and environment variables to avoid external dependencies

### Key Files to Understand Cross-Module Behavior

1. **main.py** orchestrates the entire flow - start here to understand how modules connect
2. **llm.py** contains the unified analysis prompt and model routing logic
3. **report.py** handles both report generation and newsletter website detection/caching
4. **fetch.py** parses email bodies and extracts clean text from HTML newsletters
5. **config_validator.py** validates all configuration files and environment variables

### Configuration Validation

The project includes comprehensive configuration validation via `config_validator.py`:
- **Environment Variables**: Validates API keys, file paths, and OpenRouter settings
- **JSON Files**: Validates `newsletter_websites.json` structure, URLs, and detects duplicates/tracking URLs
- **Credentials**: Validates Gmail OAuth configuration files
- Run `python config_validator.py` to check all configuration before running the main application