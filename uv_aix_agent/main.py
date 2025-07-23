#!/usr/bin/env python3
"""
UV AI Agent - Main entry point.

This module provides backward compatibility with the original workflow system
while the new Typer CLI interface is the recommended way to use the tool.

For new usage, use: uv run python cli.py
For legacy compatibility: python main.py
"""

import os
from dotenv import load_dotenv
import json
import sys
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

def start():
    """
    Legacy entry point for backward compatibility.
    
    Note: The new recommended way to use UV AI Agent is through the Typer CLI:
    - uv run python cli.py run --help
    - uv run python cli.py list
    - uv run python cli.py info
    """
    
    print("🤖 UV AI Agent - Legacy Entry Point")
    print("📢 Note: Consider using the new CLI interface for better experience:")
    print("   uv run python cli.py run --verbose")
    print("   uv run python cli.py list")
    print("   uv run python cli.py --help")
    print()
    
    # Check if we're in a Git repository
    if not Path(".git").exists():
        print("❌ Error: Not in a Git repository!")
        print("Please run this command from within a Git repository directory.")
        sys.exit(1)
    
    # Load configuration from config.json
    try:
        with open('config/app_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config/app_config.json not found. Please ensure it exists.")
        sys.exit(1)

    # Check for XML report definitions in organized structure
    reports_dirs = [
        Path("reports/git_analysis"),
        Path("reports/code_quality"), 
        Path("reports")  # fallback to root reports
    ]
    
    xml_reports = []
    for reports_dir in reports_dirs:
        if reports_dir.exists():
            xml_reports.extend(reports_dir.glob("*.xml"))
    
    if not xml_reports:
        print("Error: No XML report definitions found in reports/ directories.")
        sys.exit(1)
    
    # Use the first XML report found
    report_xml_path = str(xml_reports[0])
    print(f"📊 Using XML report definition: {report_xml_path}")
    
    try:
        # Import the CLI functionality and execute a report
        from cli import collect_git_data, calculate_metrics, generate_warnings, format_xml_report
        from datetime import datetime
        
        print("🔍 Collecting Git repository data...")
        data_collection = collect_git_data()
        raw_data = data_collection['raw_data']
        errors = data_collection['errors']
        
        print("🧮 Calculating derived metrics...")
        metrics = calculate_metrics(raw_data)
        
        print("⚠️  Generating contextual warnings...")
        warnings = generate_warnings(raw_data, metrics['lifetime_metrics'], metrics['recent_metrics'], errors)
        
        print("📝 Formatting XML report...")
        xml_report = format_xml_report(raw_data, metrics, warnings, errors)
        
        # Save to file
        output_file = f"git_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        with open(output_file, 'w') as f:
            f.write(xml_report)
        
        print(f"\n✅ Report generated successfully!")
        print(f"📁 Saved to: {output_file}")
        print(f"📊 Warnings generated: {len(warnings)}")
        
        # Show summary
        if warnings:
            print(f"\n⚠️  Generated Warnings:")
            for warning in warnings:
                severity_map = {"high": "🔴", "medium": "🟡", "low": "🔵"}
                icon = severity_map.get(warning["severity"], "⚪")
                print(f"   {icon} {warning['severity'].upper()}: {warning['title']}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start()
