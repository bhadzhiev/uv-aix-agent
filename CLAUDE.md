# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is the **UV AI Agent** project - a Python-based AI agent system for generating Git repository reports using LlamaIndex and OpenAI. The project is organized as follows:

- `uv_aix_agent/` - Main project directory
  - `uv_aix_agent/` - Core package with main application logic
    - `main.py` - Entry point that loads config and runs the selected report generator
    - `git_tools.py` - Git data collection utilities and Pydantic models
    - `reports/` - Report generation modules
      - `git_report/` - Git repository analysis and reporting
        - `git_data_collection.py` - Git metrics collection and data models
        - `report_definition.py` - LLM-powered report generation using LlamaIndex agents
        - `report_formatter.py` - Markdown report formatting
  - `config.json` - Configuration for LLM provider, model selection, and embedding model
  - `pyproject.toml` - Project dependencies and entry point configuration

## Development Commands

The project uses `uv` as the package manager. Key commands:

- **Run the application**: `uv run start` (configured in pyproject.toml)
- **Install dependencies**: `uv install` (installs llama_index and dependencies)
- **Development mode**: The project entry point is `uv_aix_agent.main:start`

## Architecture

The application follows a modular report generation architecture:

1. **Configuration Loading**: `main.py` loads `config.json` to determine LLM provider and models
2. **Report Type Selection**: Currently supports "git_report" type (hardcoded but designed for extension)
3. **Data Collection**: `git_data_collection.py` uses subprocess calls to gather Git repository metrics
4. **LLM Processing**: `report_definition.py` uses LlamaIndex's FunctionCallingAgentWorker to:
   - Generate structured Git reports using Pydantic models
   - Create AI-powered insights (summary, risks, improvements)
5. **Output Formatting**: `report_formatter.py` converts structured data to Markdown tables

## Key Dependencies

- **llama_index**: Core LLM framework with OpenAI integration and function calling agents
- **pydantic**: Data validation and structured model definitions
- **dotenv**: Environment variable management for API keys
- **subprocess**: Git command execution for data collection

## Configuration

The `config.json` supports:
- `provider`: "openai" or "openrouter" (OpenRouter has limited function calling support)
- `llm_model`: OpenAI model name (e.g., "gpt-3.5-turbo")
- `embedding_model`: HuggingFace embedding model for LlamaIndex

## Environment Variables

- `OPENAI_API_KEY`: Required for LLM functionality (loaded via dotenv)