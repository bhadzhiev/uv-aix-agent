# 🤖 UV AI Agent CLI Usage Guide

UV AI Agent now features a modern Typer-based CLI interface with Rich formatting for an enhanced user experience.

## Installation

Ensure dependencies are installed:
```bash
uv sync
```

## CLI Commands

### 📋 List Available Reports
```bash
uv run python cli.py list
```

Shows all available XML report definitions with descriptions.

### 🚀 Run Analysis Report
```bash
# Run with default settings (current directory)
uv run python cli.py run

# Run with verbose output
uv run python cli.py run --verbose

# Run and display XML output
uv run python cli.py run --show-xml

# Specify custom output file
uv run python cli.py run --output my_report.xml

# Analyze a different directory
uv run python cli.py run --dir /path/to/git/repo

# Analyze parent directory
uv run python cli.py run --dir ..

# Run specific report by name
uv run python cli.py run "Git Comprehensive Report"

# Combine multiple options
uv run python cli.py run --dir ../other-repo --verbose --output custom_report.xml
```

### ℹ️ Show Information
```bash
uv run python cli.py info
```

Displays information about UV AI Agent and its features.

### 📖 Get Help
```bash
uv run python cli.py --help
uv run python cli.py run --help
```

## Example Usage

1. **Quick Analysis (Current Directory)**:
   ```bash
   python cli.py run
   ```

2. **Analyze Different Repository**:
   ```bash
   python cli.py run --dir /path/to/other/repo --verbose
   ```

3. **Detailed Analysis with All Options**:
   ```bash
   python cli.py run --dir .. --verbose --show-xml --output detailed_report.xml
   ```

4. **List and Select Report**:
   ```bash
   python cli.py list
   python cli.py run "Comprehensive Report"
   ```

## Features

- 🎨 **Rich CLI Interface**: Beautiful colored output with progress indicators
- 📊 **Comprehensive Git Analysis**: 16+ repository metrics
- ⚠️ **Dynamic Warning System**: 7 contextual warning types with actionable recommendations
- 📝 **XML Report Output**: Structured, machine-readable reports
- 🔍 **Verbose Mode**: Detailed execution information
- 🎯 **Flexible Output**: Custom file names and display options
- 📁 **Directory Flexibility**: Analyze any Git repository with `--dir` option

## Report Structure

Generated reports include:

### 📈 **Repository Data**
- Basic info (name, branch, remote URL)
- Commit and author statistics
- Branch and tag information
- Recent activity metrics

### 📊 **Calculated Metrics**
- **Lifetime**: commits per author, merge commit ratio, repo age
- **Recent**: commit velocity, change density, author participation

### ⚠️ **Dynamic Warnings**
- **High Severity**: Single contributor, data collection issues
- **Medium Severity**: Low commit activity, high change density, incomplete metrics
- **Low Severity**: No merge commits, high commits per author

### 🎯 **Actionable Recommendations**
Each warning includes prioritized action items to improve repository health.

## Legacy Compatibility

The original `main.py` entry point is still available:
```bash
uv run python main.py
```

However, the new CLI interface is recommended for the best experience.

## Requirements

- Python 3.12+
- Git repository (run from within a Git directory)
- Dependencies: `typer`, `rich`, `python-dotenv`

## Examples of Generated Warnings

**🔴 High Severity - Single Contributor**
- *Issue*: Only one active contributor detected
- *Actions*: Encourage pair programming, document knowledge, add team members

**🟡 Medium Severity - High Change Density**
- *Issue*: 61 files changed in recent commits (density: 61.0)
- *Actions*: Review large commits, break into smaller focused commits

**🔵 Low Severity - No Merge Commits**
- *Issue*: Linear history detected (0% merge commits)
- *Actions*: Consider feature branch workflow, evaluate merge vs rebase