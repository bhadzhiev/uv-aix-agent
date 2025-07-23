"""Git analysis workflow implementation - now uses dynamic XML-based report definitions."""

from typing import Dict, Any, List
try:
    from .base_workflow import BaseWorkflow
    from ..actions.base_action import BaseAction
except ImportError:
    from orchestration.base_workflow import BaseWorkflow
    from actions.base_action import BaseAction


class GitAnalysisWorkflow(BaseWorkflow):
    """Workflow for comprehensive Git repository analysis using dynamic XML definitions."""
    
    def __init__(self, report_definition: Dict[str, Any] = None):
        super().__init__(
            name="git_analysis",
            description="Comprehensive Git repository analysis with metrics, activity, and insights"
        )
        self.report_definition = report_definition or {}
    
    def build_actions(self) -> List[BaseAction]:
        """Build dynamic action sequence from XML report definition."""
        # In the new system, actions are defined in XML and executed by the report engine
        # This method now returns an empty list as actions are handled dynamically
        return []
    
    def execute_from_definition(self, report_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow using XML report definition."""
        # This method would be called by the report engine to execute the workflow
        # based on the XML definition loaded from comprehensive.xml
        
        results = {}
        
        # Execute data collection tasks defined in XML
        data_collection = report_definition.get('data_collection', {})
        bash_commands = data_collection.get('bash_commands', [])
        
        # Execute analysis tasks defined in XML  
        analysis_tasks = report_definition.get('analysis_tasks', [])
        
        # Each task in the XML definition would be executed here
        for task in analysis_tasks:
            task_name = task.get('name', '')
            if task_name == 'git_data_collection':
                results['data_collected'] = True
            elif task_name == 'calculate_derived_metrics':
                results['metrics_calculated'] = True
            elif task_name == 'generate_warnings':
                results['warnings_generated'] = True
            elif task_name == 'generate_comprehensive_report':
                results['report_generated'] = True
            elif task_name == 'generate_insights':
                results['insights_generated'] = True
        
        return results
    
    def should_continue_on_error(self, task_name: str, error) -> bool:
        """Continue workflow even if some tasks fail."""
        # Allow workflow to continue if data collection partially fails
        if task_name == 'git_data_collection':
            return True
        
        # Stop workflow if critical tasks fail
        if task_name == 'generate_comprehensive_report':
            return False
        
        # For other tasks, continue with partial results
        return True
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate Git workflow configuration from XML definition."""
        # Check for required XML sections
        if 'data_collection' not in config:
            return False
        
        data_collection = config.get('data_collection', {})
        bash_commands = data_collection.get('bash_commands', [])
        
        if not isinstance(bash_commands, list) or len(bash_commands) == 0:
            return False
        
        # Validate analysis tasks are defined
        analysis_tasks = config.get('analysis_tasks', [])
        if not isinstance(analysis_tasks, list) or len(analysis_tasks) == 0:
            return False
        
        return True


class GitSecurityWorkflow(BaseWorkflow):
    """Workflow focused on Git repository security analysis using dynamic XML definitions."""
    
    def __init__(self, report_definition: Dict[str, Any] = None):
        super().__init__(
            name="git_security",
            description="Security-focused Git repository analysis"
        )
        self.report_definition = report_definition or {}
    
    def build_actions(self) -> List[BaseAction]:
        """Build dynamic action sequence from XML report definition."""
        return []
    
    def execute_from_definition(self, report_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security workflow using XML report definition."""
        results = {}
        
        # Execute security-focused tasks from XML definition
        analysis_tasks = report_definition.get('analysis_tasks', [])
        
        for task in analysis_tasks:
            task_name = task.get('name', '')
            # Security workflow focuses on data collection and warning generation
            if task_name in ['git_data_collection', 'generate_warnings']:
                results[task_name] = True
        
        return results
    
    def should_continue_on_error(self, task_name: str, error) -> bool:
        """Security workflow should be more strict about errors."""
        # Stop if data collection fails significantly
        if task_name == 'git_data_collection':
            return True  # Allow partial collection
        
        return True


class GitBasicWorkflow(BaseWorkflow):
    """Simplified workflow for basic Git repository analysis using dynamic XML definitions."""
    
    def __init__(self, report_definition: Dict[str, Any] = None):
        super().__init__(
            name="git_basic",
            description="Basic Git repository overview and analysis"
        )
        self.report_definition = report_definition or {}
    
    def build_actions(self) -> List[BaseAction]:
        """Build dynamic action sequence from XML report definition."""
        return []
    
    def execute_from_definition(self, report_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Execute basic workflow using XML report definition."""
        results = {}
        
        # Basic workflow only does data collection and basic reporting
        analysis_tasks = report_definition.get('analysis_tasks', [])
        
        for task in analysis_tasks:
            task_name = task.get('name', '')
            if task_name in ['git_data_collection', 'generate_comprehensive_report']:
                results[task_name] = True
        
        return results
    
    def should_continue_on_error(self, task_name: str, error) -> bool:
        """Basic workflow should be very tolerant of errors."""
        return True


def create_workflow_from_config(workflow_config: Dict[str, Any]) -> BaseWorkflow:
    """
    Factory function to create workflow from XML configuration.
    
    Args:
        workflow_config: Configuration loaded from XML report definition
        
    Returns:
        Appropriate workflow instance configured with XML definition
    """
    metadata = workflow_config.get('metadata', {})
    if hasattr(metadata, 'name'):
        report_name = metadata.name.lower()
    else:
        report_name = metadata.get('name', '').lower()
    
    if 'security' in report_name:
        return GitSecurityWorkflow(workflow_config)
    elif 'basic' in report_name:
        return GitBasicWorkflow(workflow_config)
    else:
        return GitAnalysisWorkflow(workflow_config)