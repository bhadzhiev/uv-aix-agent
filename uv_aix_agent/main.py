import os
from dotenv import load_dotenv
import json
import sys
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

def start():
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
    
    # Use the new workflow-based system
    try:
        # Try relative imports first (when used as package)
        from .core.xml_parser import parse_report_definition
        from .orchestration.git_workflow import create_workflow_from_config
        from .core.tool_manager import ToolManager
    except ImportError:
        # Fall back to absolute imports (when run directly)
        from core.xml_parser import parse_report_definition
        from orchestration.git_workflow import create_workflow_from_config
        from core.tool_manager import ToolManager
    
    # Use the first XML report found
    report_xml_path = str(xml_reports[0])
    print(f"Using XML report definition: {report_xml_path}")
    
    try:
        # Parse report configuration
        report_config = parse_report_definition(report_xml_path)
        
        # Create workflow
        workflow = create_workflow_from_config(report_config.__dict__)
        
        # Setup tools
        tool_manager = ToolManager()
        tool_manager.load_report_tools(report_config)
        tools = tool_manager.get_all_tools(report_config)
        
        # Prepare workflow data
        workflow_data = {
            'bash_commands': report_config.data_collection.bash_commands,
            'file_analysis': report_config.data_collection.file_analysis,
            'analysis_tasks': report_config.analysis_tasks
        }
        
        # Execute workflow
        report_output = workflow.execute(config, tools, workflow_data)
        print(report_output)
        
    except Exception as e:
        print(f"Error generating XML report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start()
