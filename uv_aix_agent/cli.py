#!/usr/bin/env python3
"""Typer CLI interface for UV AI Agent reports."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from pathlib import Path
import json
import subprocess
from datetime import datetime
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Typer app and Rich console
app = typer.Typer(
    name="uv-agent",
    help="🤖 UV AI Agent - Dynamic Git Repository Analysis Tool",
    add_completion=False
)
console = Console()

def get_available_reports() -> List[tuple]:
    """Get list of available XML report definitions."""
    reports = []
    
    # Get the script directory to locate reports relative to the CLI script
    script_dir = Path(__file__).parent
    
    # Check organized structure relative to script location
    reports_dirs = [
        script_dir / "reports/git_analysis",
        script_dir / "reports/code_quality", 
        script_dir / "reports"
    ]
    
    for reports_dir in reports_dirs:
        if reports_dir.exists():
            for xml_file in reports_dir.glob("*.xml"):
                if xml_file.name != "base_template.xml":  # Skip template
                    # Parse basic metadata
                    try:
                        import xml.etree.ElementTree as ET
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        metadata = root.find('metadata')
                        
                        name_elem = metadata.find('name')
                        name = name_elem.text if name_elem is not None else xml_file.stem
                        
                        desc_elem = metadata.find('description')
                        description = desc_elem.text if desc_elem is not None else "No description available"
                        
                        reports.append((str(xml_file), name, description))
                    except Exception:
                        # Fallback for malformed XML
                        reports.append((str(xml_file), xml_file.stem, "XML parsing error"))
    
    return reports

def execute_bash_command(name: str, command: str, timeout: int = 60) -> dict:
    """Execute a bash command and return results."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return {
            'name': name,
            'command': command,
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'error': result.stderr.strip() if result.stderr else None,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'name': name,
            'command': command,
            'success': False,
            'output': '',
            'error': f'Command timed out after {timeout} seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'name': name,
            'command': command,
            'success': False,
            'output': '',
            'error': str(e),
            'returncode': -1
        }

def collect_git_data() -> dict:
    """Collect Git data using comprehensive commands."""
    
    bash_commands = [
        ("repo_name", "git config --get remote.origin.url | sed 's/.*\\///' | sed 's/\\.git$//' || echo 'unknown'"),
        ("current_branch", "git rev-parse --abbrev-ref HEAD || echo 'unknown'"),
        ("remote_url", "git config --get remote.origin.url || echo 'unknown'"),
        ("first_commit_date", "git log --reverse --format=%ad --date=format:%Y-%m-%d --max-count=1 || echo 'unknown'"),
        ("latest_commit_date", "git log -1 --format=%ad --date=format:%Y-%m-%d || echo 'unknown'"),
        ("total_commits", "git rev-list --count HEAD || echo '0'"),
        ("total_authors", "git shortlog -sn --all | wc -l || echo '0'"),
        ("local_branches", "git branch | wc -l || echo '0'"),
        ("remote_branches", "git branch -r | wc -l || echo '0'"),
        ("total_tags", "git tag | wc -l || echo '0'"),
        ("last_tag", "git describe --tags --abbrev=0 2>/dev/null || echo 'unknown'"),
        ("merge_commits", "git log --merges --oneline | wc -l || echo '0'"),
        ("commits_7d", "git rev-list --count --since='7 days ago' HEAD || echo '0'"),
        ("authors_7d", "git shortlog -sn --since='7 days ago' | wc -l || echo '0'"),
        ("files_changed_7d", "git log --since='7 days ago' --name-only --pretty=format: | sort -u | wc -l || echo '0'"),
        ("working_tree_status", "git status --porcelain | wc -l")
    ]
    
    results = {}
    raw_data = {}
    errors = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Collecting Git repository data...", total=len(bash_commands))
        
        for name, command in bash_commands:
            progress.update(task, description=f"Executing: {name}")
            result = execute_bash_command(name, command)
            results[name] = result
            
            if result['success']:
                output = result['output'].strip()
                # Parse specific data types
                if name in ['total_commits', 'total_authors', 'local_branches', 'remote_branches', 
                           'total_tags', 'merge_commits', 'commits_7d', 'authors_7d', 
                           'files_changed_7d', 'working_tree_status']:
                    raw_data[name] = int(output) if output.isdigit() else 0
                else:
                    raw_data[name] = output or 'unknown'
            else:
                raw_data[name] = None
                errors.append(f"Command '{name}' failed: {result['error']}")
            
            progress.advance(task)
    
    return {
        'bash_results': results,
        'raw_data': raw_data,
        'errors': errors
    }

def calculate_metrics(raw_data: dict) -> dict:
    """Calculate derived metrics."""
    total_commits = raw_data.get('total_commits', 0)
    total_authors = raw_data.get('total_authors', 0)
    merge_commits = raw_data.get('merge_commits', 0)
    commits_7d = raw_data.get('commits_7d', 0)
    files_changed_7d = raw_data.get('files_changed_7d', 0)
    authors_7d = raw_data.get('authors_7d', 0)
    
    lifetime_metrics = {
        'commits_per_author': round(total_commits / total_authors, 2) if total_authors > 0 else 0.0,
        'merge_commit_ratio': round(merge_commits / total_commits, 2) if total_commits > 0 else 0.0,
        'repo_age_days': 0  # Placeholder - would need date calculation
    }
    
    recent_metrics = {
        'commit_velocity': round(commits_7d / 7.0, 2) if commits_7d > 0 else 0.0,
        'change_density': round(files_changed_7d / commits_7d, 2) if commits_7d > 0 else 0.0,
        'author_participation_rate': round(authors_7d / total_authors, 2) if total_authors > 0 else 0.0
    }
    
    return {
        'lifetime_metrics': lifetime_metrics,
        'recent_metrics': recent_metrics
    }

def generate_warnings(raw_data: dict, lifetime_metrics: dict, recent_metrics: dict, errors: list) -> list:
    """Generate contextual warnings based on analysis data."""
    warnings = []
    
    # Data collection warnings
    if errors or not raw_data:
        warnings.append({
            "id": "bash_tool_unavailable",
            "severity": "high",
            "title": "Limited bash tool availability affected data collection",
            "description": "The bash executor tool was not available or failed to execute commands properly",
            "actions": [
                {"priority": "high", "description": "Ensure bash executor tool is properly configured"},
                {"priority": "medium", "description": "Verify Git repository access and permissions"},
                {"priority": "low", "description": "Consider implementing fallback data collection methods"}
            ]
        })
    
    # Check for incomplete metrics
    if any(value is None for value in raw_data.values()):
        warnings.append({
            "id": "incomplete_metrics",
            "severity": "medium", 
            "title": "Some metrics may be incomplete or unavailable",
            "description": "Data collection was partially successful but some metrics could not be calculated",
            "actions": [
                {"priority": "high", "description": "Review failed Git commands and fix underlying issues"},
                {"priority": "medium", "description": "Validate repository structure and Git configuration"},
                {"priority": "low", "description": "Enable debug logging for data collection process"}
            ]
        })
    
    # Repository health warnings
    commits_7d = raw_data.get('commits_7d', 0)
    if commits_7d <= 1:
        warnings.append({
            "id": "low_commit_activity",
            "severity": "medium",
            "title": "Low recent commit activity detected", 
            "description": "Repository shows minimal commit activity in recent period",
            "actions": [
                {"priority": "medium", "description": "Review development workflow and encourage regular commits"},
                {"priority": "low", "description": "Consider implementing automated commit reminders"}
            ]
        })
    
    # Single contributor warning
    total_authors = raw_data.get('total_authors', 0)
    if total_authors == 1:
        warnings.append({
            "id": "single_contributor",
            "severity": "high",
            "title": "Repository has only one active contributor",
            "description": "All recent commits are from a single author, indicating potential bus factor risk",
            "actions": [
                {"priority": "high", "description": "Encourage code reviews and pair programming"},
                {"priority": "high", "description": "Document critical system knowledge"},
                {"priority": "medium", "description": "Consider bringing additional team members onto the project"}
            ]
        })
    
    # High commits per author warning
    commits_per_author = lifetime_metrics.get('commits_per_author', 0)
    if commits_per_author > 100:
        warnings.append({
            "id": "high_commits_per_author",
            "severity": "low",  
            "title": "High commits per author ratio",
            "description": "Average commits per author is unusually high, may indicate lack of contribution diversity",
            "actions": [
                {"priority": "medium", "description": "Review commit granularity and encourage atomic commits"},
                {"priority": "low", "description": "Consider squashing related commits before merging"}
            ]
        })
    
    # Merge commit analysis
    merge_commit_ratio = lifetime_metrics.get('merge_commit_ratio', 0)
    if merge_commit_ratio == 0.0:
        warnings.append({
            "id": "no_merge_commits",
            "severity": "low",
            "title": "No merge commits detected",
            "description": "Repository appears to use linear history, which may indicate lack of feature branch workflow",
            "actions": [
                {"priority": "low", "description": "Consider implementing feature branch workflow"},
                {"priority": "low", "description": "Evaluate benefits of merge vs rebase strategies"}
            ]
        })
    
    # Change density warning
    change_density = recent_metrics.get('change_density', 0)
    if change_density > 10.0:
        warnings.append({
            "id": "high_change_density",
            "severity": "medium",
            "title": "High change density in recent commits",
            "description": "Recent commits show unusually high file change density",
            "actions": [
                {"priority": "medium", "description": "Review large commits for potential refactoring opportunities"},
                {"priority": "low", "description": "Consider breaking large changes into smaller, focused commits"}
            ]
        })
    
    return warnings

def format_xml_report(raw_data: dict, metrics: dict, warnings: list, errors: list) -> str:
    """Format results as XML report."""
    
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<git_comprehensive_report>')
    
    # Metadata
    xml_parts.append('  <metadata>')
    xml_parts.append('    <name>Git Comprehensive Report</name>')
    xml_parts.append(f'    <generated_at>{datetime.now().isoformat()}</generated_at>')
    xml_parts.append('    <version>1.0</version>')
    xml_parts.append('  </metadata>')
    
    # Raw data
    xml_parts.append('  <repository_data>')
    for key, value in raw_data.items():
        xml_parts.append(f'    <{key}>{value}</{key}>')
    xml_parts.append('  </repository_data>')
    
    # Metrics
    xml_parts.append('  <lifetime_metrics>')
    for key, value in metrics['lifetime_metrics'].items():
        xml_parts.append(f'    <{key}>{value}</{key}>')
    xml_parts.append('  </lifetime_metrics>')
    
    xml_parts.append('  <recent_metrics>')
    for key, value in metrics['recent_metrics'].items():
        xml_parts.append(f'    <{key}>{value}</{key}>')
    xml_parts.append('  </recent_metrics>')
    
    # Warnings and actions
    xml_parts.append('  <warnings>')
    for warning in warnings:
        xml_parts.append('    <warning>')
        xml_parts.append(f'      <id>{warning["id"]}</id>')
        xml_parts.append(f'      <severity>{warning["severity"]}</severity>')
        xml_parts.append(f'      <title>{warning["title"]}</title>')
        xml_parts.append(f'      <description>{warning["description"]}</description>')
        xml_parts.append('      <actions>')
        for action in warning["actions"]:
            xml_parts.append('        <action>')
            xml_parts.append(f'          <priority>{action["priority"]}</priority>')
            xml_parts.append(f'          <description>{action["description"]}</description>')
            xml_parts.append('        </action>')
        xml_parts.append('      </actions>')
        xml_parts.append('    </warning>')
    xml_parts.append('  </warnings>')
    
    # Errors if any
    if errors:
        xml_parts.append('  <errors>')
        for error in errors:
            xml_parts.append(f'    <error>{error}</error>')
        xml_parts.append('  </errors>')
    
    xml_parts.append('</git_comprehensive_report>')
    
    return '\n'.join(xml_parts)

@app.command("list")
def list_reports():
    """📋 List all available report definitions."""
    console.print("\n🤖 [bold blue]Available UV AI Agent Reports[/bold blue]\n")
    
    reports = get_available_reports()
    
    if not reports:
        console.print("[red]❌ No report definitions found![/red]")
        console.print("Make sure you have XML report files in the reports/ directory.")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=30)
    table.add_column("File", style="green", width=40) 
    table.add_column("Description", style="yellow")
    
    for file_path, name, description in reports:
        # Shorten the description if too long
        short_desc = description[:80] + "..." if len(description) > 80 else description
        table.add_row(name, Path(file_path).name, short_desc)
    
    console.print(table)
    console.print(f"\n[dim]Found {len(reports)} report(s)[/dim]")

@app.command("run")
def run_report(
    report: Optional[str] = typer.Argument(None, help="Report name or file path to execute"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    show_xml: bool = typer.Option(False, "--show-xml", help="Display XML output in terminal"),
    directory: str = typer.Option(".", "--dir", help="Directory to inspect")
):
    """🚀 Execute a Git repository analysis report."""
    
    console.print("\n🤖 [bold blue]UV AI Agent - Git Repository Analysis[/bold blue]\n")
    
    # Convert directory to Path and resolve it
    target_dir = Path(directory).resolve()
    
    # Check if the directory exists
    if not target_dir.exists():
        console.print(f"[red]❌ Error: Directory '{directory}' does not exist![/red]")
        raise typer.Exit(1)
    
    # Check if it's a Git repository
    git_dir = target_dir / ".git"
    if not git_dir.exists():
        console.print(f"[red]❌ Error: '{directory}' is not a Git repository![/red]")
        console.print("Please specify a directory that contains a Git repository.")
        raise typer.Exit(1)
    
    # Change to the target directory
    original_cwd = os.getcwd()
    os.chdir(target_dir)
    
    console.print(f"📁 [dim]Analyzing directory:[/dim] {target_dir}")
    console.print()
    
    try:
        # Get available reports
        reports = get_available_reports()
        
        if not reports:
            console.print("[red]❌ No report definitions found![/red]")
            raise typer.Exit(1)
        
        # Select report
        selected_report = None
        if report:
            # Try to find by name or file path
            for file_path, name, description in reports:
                if report in [name, Path(file_path).name, file_path]:
                    selected_report = (file_path, name, description)
                    break
            
            if not selected_report:
                console.print(f"[red]❌ Report '{report}' not found![/red]")
                console.print("Use 'uv-agent list' to see available reports.")
                raise typer.Exit(1)
        else:
            # Use first available report (usually comprehensive)
            selected_report = reports[0]
        
        file_path, name, description = selected_report
        
        console.print(f"📊 [bold green]Running Report:[/bold green] {name}")
        console.print(f"📄 [dim]Description:[/dim] {description}")
        console.print(f"📁 [dim]Definition:[/dim] {Path(file_path).name}\n")
        
        # Step 1: Collect Git data
        console.print("🔍 [bold yellow]Step 1:[/bold yellow] Collecting Git repository data...")
        data_collection = collect_git_data()
        raw_data = data_collection['raw_data']
        errors = data_collection['errors']
        
        if verbose:
            console.print(f"   📈 Collected data for {len(raw_data)} metrics")
            if errors:
                console.print(f"   ⚠️  {len(errors)} errors encountered during collection")
        
        # Step 2: Calculate derived metrics  
        console.print("🧮 [bold yellow]Step 2:[/bold yellow] Calculating derived metrics...")
        metrics = calculate_metrics(raw_data)
        
        if verbose:
            console.print(f"   📊 Calculated {len(metrics['lifetime_metrics'])} lifetime metrics")
            console.print(f"   📈 Calculated {len(metrics['recent_metrics'])} recent metrics")
        
        # Step 3: Generate warnings
        console.print("⚠️  [bold yellow]Step 3:[/bold yellow] Generating contextual warnings...")
        warnings = generate_warnings(raw_data, metrics['lifetime_metrics'], metrics['recent_metrics'], errors)
        
        if verbose:
            console.print(f"   🚨 Generated {len(warnings)} warnings")
        
        # Step 4: Format XML report
        console.print("📝 [bold yellow]Step 4:[/bold yellow] Formatting XML report...")
        xml_report = format_xml_report(raw_data, metrics, warnings, errors)
        
        # Step 5: Save and display results
        output_file = output or f"git_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
        with open(output_file, 'w') as f:
            f.write(xml_report)
        
        console.print(f"\n✅ [bold green]Report generated successfully![/bold green]")
        console.print(f"📁 [dim]Saved to:[/dim] {output_file}")
        
        # Display summary
        console.print(f"\n📊 [bold blue]Summary:[/bold blue]")
        console.print(f"   • Repository: {raw_data.get('repo_name', 'unknown')}")
        console.print(f"   • Branch: {raw_data.get('current_branch', 'unknown')}")
        console.print(f"   • Total Commits: {raw_data.get('total_commits', 0)}")
        console.print(f"   • Authors: {raw_data.get('total_authors', 0)}")
        console.print(f"   • Warnings Generated: {len(warnings)}")
        
        # Show warnings summary
        if warnings:
            console.print(f"\n⚠️  [bold red]Warnings Found:[/bold red]")
            for warning in warnings:
                severity_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(warning["severity"], "white")
                console.print(f"   • [{severity_color}]{warning['severity'].upper()}[/{severity_color}]: {warning['title']}")
        
        # Display XML if requested
        if show_xml:
            console.print(f"\n📄 [bold blue]Generated XML Report:[/bold blue]")
            syntax = Syntax(xml_report, "xml", theme="monokai", line_numbers=True)
            console.print(syntax)
            
    except Exception as e:
        console.print(f"\n[red]❌ Error generating report: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)

@app.command("info")
def show_info():
    """ℹ️  Show information about UV AI Agent."""
    
    info_panel = Panel.fit(
        "[bold blue]🤖 UV AI Agent[/bold blue]\n\n"
        "[yellow]Dynamic Git Repository Analysis Tool[/yellow]\n\n"
        "Features:\n"
        "• 📊 Comprehensive Git metrics collection\n"
        "• ⚠️  Contextual warning generation\n"
        "• 🎯 Actionable improvement recommendations\n"
        "• 📝 XML report output\n"
        "• 🎨 Rich CLI interface\n\n"
        "[dim]Built with Typer, Rich, and LlamaIndex[/dim]",
        title="About",
        border_style="blue"
    )
    
    console.print(info_panel)

if __name__ == "__main__":
    app()