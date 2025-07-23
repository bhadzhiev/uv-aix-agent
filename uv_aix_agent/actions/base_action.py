"""Base action class for UV AI Agent workflows."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ActionContext:
    """Context passed between actions in a workflow."""
    data: Dict[str, Any]
    config: Dict[str, Any]
    tools: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context data."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in context data."""
        self.data[key] = value
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update context data with new values."""
        self.data.update(data)


class BaseAction(ABC):
    """Abstract base class for all actions."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._logger = None
    
    @abstractmethod
    def execute(self, context: ActionContext) -> ActionContext:
        """
        Execute the action with the given context.
        
        Args:
            context: ActionContext containing data, config, tools, and metadata
            
        Returns:
            Updated ActionContext with results
            
        Raises:
            ActionError: If execution fails
        """
        pass
    
    def validate_inputs(self, context: ActionContext) -> bool:
        """
        Validate that the context contains required inputs.
        
        Args:
            context: ActionContext to validate
            
        Returns:
            True if inputs are valid, False otherwise
        """
        return True
    
    def get_required_tools(self) -> List[str]:
        """
        Get list of tool names required by this action.
        
        Returns:
            List of required tool names
        """
        return []
    
    def can_execute(self, context: ActionContext) -> bool:
        """
        Check if this action can execute with the given context.
        
        Args:
            context: ActionContext to check
            
        Returns:
            True if action can execute, False otherwise
        """
        # Check if required tools are available
        required_tools = self.get_required_tools()
        for tool_name in required_tools:
            if tool_name not in context.tools:
                return False
        
        # Validate inputs
        return self.validate_inputs(context)
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"


class ActionError(Exception):
    """Exception raised when an action fails to execute."""
    
    def __init__(self, action_name: str, message: str, original_error: Optional[Exception] = None):
        self.action_name = action_name
        self.original_error = original_error
        super().__init__(f"Action '{action_name}' failed: {message}")


class ConditionalAction(BaseAction):
    """Action that executes conditionally based on context."""
    
    def __init__(self, name: str, condition_func: callable, action: BaseAction, description: str = ""):
        super().__init__(name, description)
        self.condition_func = condition_func
        self.action = action
    
    def execute(self, context: ActionContext) -> ActionContext:
        """Execute the wrapped action if condition is met."""
        if self.condition_func(context):
            return self.action.execute(context)
        else:
            # Condition not met, return context unchanged
            return context
    
    def validate_inputs(self, context: ActionContext) -> bool:
        """Validate inputs for the wrapped action."""
        return self.action.validate_inputs(context)
    
    def get_required_tools(self) -> List[str]:
        """Get required tools from wrapped action."""
        return self.action.get_required_tools()


class ParallelAction(BaseAction):
    """Action that executes multiple actions in parallel."""
    
    def __init__(self, name: str, actions: List[BaseAction], description: str = ""):
        super().__init__(name, description)
        self.actions = actions
    
    def execute(self, context: ActionContext) -> ActionContext:
        """Execute all actions in parallel and merge results."""
        # For now, execute sequentially (parallel execution would require threading/async)
        # This is a placeholder for future parallel implementation
        for action in self.actions:
            if action.can_execute(context):
                context = action.execute(context)
        return context
    
    def validate_inputs(self, context: ActionContext) -> bool:
        """Validate inputs for all actions."""
        return all(action.validate_inputs(context) for action in self.actions)
    
    def get_required_tools(self) -> List[str]:
        """Get required tools from all actions."""
        tools = set()
        for action in self.actions:
            tools.update(action.get_required_tools())
        return list(tools)