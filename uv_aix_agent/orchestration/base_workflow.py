"""Base workflow class for UV AI Agent."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
try:
    from ..actions.base_action import BaseAction, ActionContext, ActionError
except ImportError:
    from actions.base_action import BaseAction, ActionContext, ActionError


class BaseWorkflow(ABC):
    """Abstract base class for all workflows."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.actions: List[BaseAction] = []
        self._logger = None
    
    @abstractmethod
    def build_actions(self) -> List[BaseAction]:
        """
        Build the list of actions for this workflow.
        
        Returns:
            List of actions to execute in order
        """
        pass
    
    def execute(self, config: Dict[str, Any], tools: Dict[str, Any], 
                initial_data: Dict[str, Any] = None) -> str:
        """
        Execute the workflow with given configuration and tools.
        
        Args:
            config: Configuration dictionary
            tools: Available tools dictionary  
            initial_data: Initial data for the workflow
            
        Returns:
            Final workflow output (typically a report)
            
        Raises:
            WorkflowError: If workflow execution fails
        """
        try:
            # Initialize context
            context = ActionContext(
                data=initial_data or {},
                config=config,
                tools=tools,
                metadata={'workflow_name': self.name}
            )
            
            # Build actions if not already built
            if not self.actions:
                self.actions = self.build_actions()
            
            # Execute each action in sequence
            for i, action in enumerate(self.actions):
                print(f"Executing action {i+1}/{len(self.actions)}: {action.name}")
                
                # Check if action can execute
                if not action.can_execute(context):
                    print(f"Warning: Skipping action '{action.name}' - requirements not met")
                    continue
                
                try:
                    context = action.execute(context)
                except ActionError as e:
                    error_msg = f"Action '{action.name}' failed: {e}"
                    if self.should_continue_on_error(action, e):
                        print(f"Warning: {error_msg} - continuing workflow")
                        continue
                    else:
                        raise WorkflowError(self.name, error_msg, e)
                except Exception as e:
                    error_msg = f"Unexpected error in action '{action.name}': {e}"
                    raise WorkflowError(self.name, error_msg, e)
            
            # Get final output
            final_output = self.get_final_output(context)
            
            return final_output
            
        except WorkflowError:
            raise
        except Exception as e:
            raise WorkflowError(self.name, f"Workflow execution failed: {e}", e)
    
    def should_continue_on_error(self, action: BaseAction, error: ActionError) -> bool:
        """
        Determine if workflow should continue when an action fails.
        
        Args:
            action: The action that failed
            error: The error that occurred
            
        Returns:
            True if workflow should continue, False to stop
        """
        return False  # By default, stop on any error
    
    def get_final_output(self, context: ActionContext) -> str:
        """
        Extract final output from the workflow context.
        
        Args:
            context: Final workflow context
            
        Returns:
            Final workflow output
        """
        return context.get('final_report', 'No output generated')
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate workflow configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        return True
    
    def get_required_tools(self) -> List[str]:
        """
        Get list of all tools required by this workflow.
        
        Returns:
            List of required tool names
        """
        if not self.actions:
            self.actions = self.build_actions()
        
        required_tools = set()
        for action in self.actions:
            required_tools.update(action.get_required_tools())
        
        return list(required_tools)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', actions={len(self.actions)})"


class WorkflowError(Exception):
    """Exception raised when a workflow fails to execute."""
    
    def __init__(self, workflow_name: str, message: str, original_error: Exception = None):
        self.workflow_name = workflow_name
        self.original_error = original_error
        super().__init__(f"Workflow '{workflow_name}' failed: {message}")


class SequentialWorkflow(BaseWorkflow):
    """Workflow that executes actions in sequence."""
    
    def __init__(self, name: str, actions: List[BaseAction], description: str = ""):
        super().__init__(name, description)
        self.actions = actions
    
    def build_actions(self) -> List[BaseAction]:
        """Return the predefined list of actions."""
        return self.actions


class ConditionalWorkflow(BaseWorkflow):
    """Workflow that executes actions based on conditions."""
    
    def __init__(self, name: str, action_conditions: List[tuple], description: str = ""):
        """
        Initialize conditional workflow.
        
        Args:
            name: Workflow name
            action_conditions: List of (condition_func, action) tuples
            description: Workflow description
        """
        super().__init__(name, description)
        self.action_conditions = action_conditions
    
    def build_actions(self) -> List[BaseAction]:
        """Build actions with conditions."""
        try:
            from ..actions.base_action import ConditionalAction
        except ImportError:
            from actions.base_action import ConditionalAction
        
        actions = []
        for condition_func, action in self.action_conditions:
            conditional_action = ConditionalAction(
                name=f"conditional_{action.name}",
                condition_func=condition_func,
                action=action,
                description=f"Conditional execution of {action.name}"
            )
            actions.append(conditional_action)
        
        return actions


class ParallelWorkflow(BaseWorkflow):
    """Workflow that can execute some actions in parallel."""
    
    def __init__(self, name: str, parallel_groups: List[List[BaseAction]], description: str = ""):
        """
        Initialize parallel workflow.
        
        Args:
            name: Workflow name
            parallel_groups: List of action groups, each group executes in parallel
            description: Workflow description
        """
        super().__init__(name, description)
        self.parallel_groups = parallel_groups
    
    def build_actions(self) -> List[BaseAction]:
        """Build actions with parallel groups."""
        try:
            from ..actions.base_action import ParallelAction
        except ImportError:
            from actions.base_action import ParallelAction
        
        actions = []
        for i, group in enumerate(self.parallel_groups):
            if len(group) == 1:
                # Single action, no need for parallel wrapper
                actions.append(group[0])
            else:
                # Multiple actions, wrap in parallel action
                parallel_action = ParallelAction(
                    name=f"parallel_group_{i}",
                    actions=group,
                    description=f"Parallel execution of {len(group)} actions"
                )
                actions.append(parallel_action)
        
        return actions