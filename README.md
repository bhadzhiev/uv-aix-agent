# UV AI Agent

An AI-powered Git repository analysis tool that generates comprehensive reports using XML-driven definitions and modern CLI interface.

## Features

- 🔍 **Comprehensive Git Analysis**: 16+ metrics including commits, branches, merges, contributors, and file statistics
- ⚠️ **Intelligent Warnings**: 7 contextual warning rules with prioritized actions
- 📊 **Rich Reports**: Markdown-formatted reports with tables, metrics, and AI-generated insights
- 🎯 **XML-Driven**: All analysis logic defined in declarative XML format for easy customization
- 🖥️ **Modern CLI**: Typer-based command-line interface with rich formatting and progress indicators
- 🔄 **Flexible Directory Support**: Analyze any Git repository from any location

## Installation

### Using UV (Recommended)

```bash
# Install globally
uv tool install uv-aix-agent

# Or install from source
uv tool install . --from git+https://github.com/bhadzhiev/uv-aix-agent.git
```

### Using pip

```bash
pip install uv-aix-agent
```

## Quick Start

```bash
# Analyze current directory
uv-agent run

# Analyze specific directory
uv-agent run --dir /path/to/repository

# Save report to file
uv-agent run --output analysis.md

# Verbose output
uv-agent run --verbose

# List available reports
uv-agent list

# Show tool information
uv-agent info
```

## Configuration

Create a `config.json` file to customize LLM settings:

```json
{
  "provider": "openai",
  "llm_model": "gpt-3.5-turbo",
  "embedding_model": "BAAI/bge-small-en-v1.5"
}
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Report Structure

The tool generates comprehensive reports with:

- **Repository Overview**: Basic repository information
- **Commit Analysis**: Total commits, authors, frequency
- **Branch Analysis**: Branch count, merge patterns
- **Contributor Insights**: Top contributors, commit distribution
- **File Statistics**: File types, sizes, and complexity
- **Warning Messages**: Contextual warnings with recommended actions
- **AI-Generated Summary**: Executive summary and improvement suggestions

## Available Reports

### Git Analysis Report (`git_analysis/comprehensive.xml`)

The default report includes:

#### Data Collection Commands
- `git log --oneline --all --no-merges | wc -l` - Total commits
- `git shortlog -sn --all | head -20` - Top contributors
- `git branch -r | wc -l` - Remote branches count
- `git log --merges --oneline | wc -l` - Total merges
- And 12+ more commands...

#### Warning Rules
1. **High Commit Concentration** - When single author has >70% commits
2. **Excessive Branches** - When >10 remote branches exist
3. **Low Merge Activity** - When <5% of commits are merges
4. **Large Files Warning** - When >10MB files found
5. **Old Branch Warning** - When branches >30 days old
6. **Binary Files Warning** - When >5 binary files found
7. **Staleness Warning** - When last commit >30 days old

#### Calculated Metrics
- Commits per author ratio
- Merge commit ratio
- Average commits per day
- File type distribution

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/bhadzhiev/uv-aix-agent.git
cd uv-aix-agent

# Install dependencies
uv sync

# Run in development mode
uv run start
```

### Project Structure

```
uv-aix-agent/
├── uv_aix_agent/
│   ├── main.py              # Entry point
│   ├── cli.py               # Typer CLI interface
│   ├── git_tools.py         # Git utilities and models
│   └── reports/
│       └── git_analysis/
│           ├── git_data_collection.py
│           ├── report_definition.py
│           └── report_formatter.py
├── reports/
│   └── git_analysis/
│       └── comprehensive.xml # XML report definition
├── config.json              # LLM configuration
└── pyproject.toml          # Project metadata
```

### Adding New Reports

1. Create XML report definition in `reports/[category]/[name].xml`
2. Define data collection commands
3. Add warning rules with conditions
4. Specify output format
5. Test with `uv-agent run --show-xml`

## Examples

### Basic Usage

```bash
# Analyze current repository
uv-agent run

# Output to file with verbose logging
uv-agent run --output report.md --verbose

# Analyze specific project
uv-agent run --dir ~/projects/my-app
```

### Sample Output

```markdown
# Git Repository Analysis Report

## Repository Overview
- **Repository**: my-awesome-project
- **Branch**: main
- **Total Commits**: 245
- **Contributors**: 8

## Commit Analysis
| Metric | Value |
|--------|--------|
| Total Commits | 245 |
| Active Authors | 8 |
| Commits per Author | 30.6 |

## Warnings
⚠️ **High Commit Concentration**: Author 'alice' has 65% of commits.
- **Action**: Encourage more contributors to participate
- **Priority**: Medium

## AI Summary
The repository shows healthy development activity with good contributor distribution...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/bhadzhiev/uv-aix-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bhadzhiev/uv-aix-agent/discussions)