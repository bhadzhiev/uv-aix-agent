#!/usr/bin/env python3
"""Simple test script to execute the comprehensive Git report with warnings."""

import json
import subprocess
from datetime import datetime
from typing import Dict, Any

def execute_bash_command(name: str, command: str, timeout: int = 60) -> Dict[str, Any]:
    """Execute a bash command and return results."""
    try:
        print(f"Executing: {name}")
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

def collect_git_data() -> Dict[str, Any]:
    """Collect Git data using the commands from comprehensive.xml."""
    
    bash_commands = [
        ("repo_name", "git config --get remote.origin.url | sed 's/.*\///' | sed 's/\\.git$//' || echo 'unknown'"),
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
    
    for name, command in bash_commands:
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
    
    return {
        'bash_results': results,
        'raw_data': raw_data,
        'errors': errors
    }

def calculate_metrics(raw_data: Dict[str, Any]) -> Dict[str, Any]:
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

def generate_warnings(raw_data: Dict[str, Any], lifetime_metrics: Dict[str, Any], 
                     recent_metrics: Dict[str, Any], errors: list) -> list:
    """Generate warnings based on analysis data."""
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

def format_xml_report(raw_data: Dict[str, Any], metrics: Dict[str, Any], warnings: list, errors: list) -> str:
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

def main():
    """Main execution function."""
    print("=== Git Comprehensive Report with Dynamic Warnings ===")
    print()
    
    # Step 1: Collect Git data
    print("1. Collecting Git repository data...")
    data_collection = collect_git_data()
    raw_data = data_collection['raw_data']
    errors = data_collection['errors']
    
    print(f"   Collected data for {len(raw_data)} metrics")
    if errors:
        print(f"   {len(errors)} errors encountered during collection")
    
    # Step 2: Calculate derived metrics
    print("2. Calculating derived metrics...")
    metrics = calculate_metrics(raw_data)
    print(f"   Calculated {len(metrics['lifetime_metrics'])} lifetime metrics")
    print(f"   Calculated {len(metrics['recent_metrics'])} recent metrics")
    
    # Step 3: Generate warnings
    print("3. Generating contextual warnings...")
    warnings = generate_warnings(raw_data, metrics['lifetime_metrics'], metrics['recent_metrics'], errors)
    print(f"   Generated {len(warnings)} warnings")
    
    # Step 4: Format XML report
    print("4. Formatting XML report...")
    xml_report = format_xml_report(raw_data, metrics, warnings, errors)
    
    # Step 5: Output results
    print()
    print("=== FINAL REPORT ===")
    print(xml_report)
    
    # Also save to file
    with open('git_comprehensive_report.xml', 'w') as f:
        f.write(xml_report)
    print()
    print("Report saved to: git_comprehensive_report.xml")

if __name__ == "__main__":
    main()