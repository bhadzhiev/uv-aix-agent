from typing import Dict, Any, List, Optional, Type
from pathlib import Path
import importlib
from llama_index.core.tools import FunctionTool

from .xml_parser import parse_global_tools, parse_report_definition, ToolConfig, GlobalToolsConfig, ReportDefinition
try:
    from ..tools.bash_tool import BashCommandTool, FileSystemTool, LLMAnalysisTool
except ImportError:
    from tools.bash_tool import BashCommandTool, FileSystemTool, LLMAnalysisTool

class ToolManager:
    """Manages global and report-specific tools."""
    
    def __init__(self, global_tools_path: str = "config/global_tools.xml"):
        self.global_tools: Dict[str, Any] = {}
        self.report_tools: Dict[str, Any] = {}
        self.tool_classes: Dict[str, Type] = {
            'BashCommandTool': BashCommandTool,
            'FileSystemTool': FileSystemTool,
            'LLMAnalysisTool': LLMAnalysisTool,
        }
        self.global_tools_config: Optional[GlobalToolsConfig] = None
        
        # Load global tools if file exists
        if Path(global_tools_path).exists():
            self.load_global_tools(global_tools_path)
    
    def register_tool_class(self, name: str, tool_class: Type):
        """Register a custom tool class."""
        self.tool_classes[name] = tool_class
    
    def create_tool_instance(self, tool_config: ToolConfig) -> Any:
        """Create a tool instance from configuration."""
        tool_class = self.tool_classes.get(tool_config.class_name)
        if not tool_class:
            raise ValueError(f"Unknown tool class: {tool_config.class_name}")
        
        # Merge config with permissions and error handling
        full_config = {
            **tool_config.config,
            'permissions': tool_config.permissions,
            'error_handling': tool_config.error_handling,
            'name': tool_config.name,
            'scope': tool_config.scope,
            'priority': tool_config.priority
        }
        
        return tool_class(full_config)
    
    def load_global_tools(self, global_tools_path: str):
        """Load global tools from XML configuration."""
        try:
            self.global_tools_config = parse_global_tools(global_tools_path)
            
            for tool_config in self.global_tools_config.tools:
                tool_instance = self.create_tool_instance(tool_config)
                self.global_tools[tool_config.name] = {
                    'instance': tool_instance,
                    'config': tool_config
                }
                
            print(f"Loaded {len(self.global_tools)} global tools")
            
        except Exception as e:
            print(f"Warning: Could not load global tools: {e}")
            self.global_tools_config = None
    
    def load_report_tools(self, report_definition: ReportDefinition):
        """Load report-specific tools."""
        self.report_tools.clear()
        
        for tool_config in report_definition.tools:
            # Check dependencies
            missing_deps = []
            for dep in tool_config.dependencies:
                if dep not in self.global_tools and dep not in self.report_tools:
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"Warning: Tool {tool_config.name} missing dependencies: {missing_deps}")
                continue
            
            try:
                tool_instance = self.create_tool_instance(tool_config)
                self.report_tools[tool_config.name] = {
                    'instance': tool_instance,
                    'config': tool_config
                }
            except Exception as e:
                print(f"Error creating tool {tool_config.name}: {e}")
        
        print(f"Loaded {len(self.report_tools)} report-specific tools")
    
    def get_all_tools(self, report_definition: ReportDefinition) -> Dict[str, Any]:
        """Get all available tools (global + report-specific)."""
        all_tools = {}
        
        # Add global tools if inheritance is enabled
        if report_definition.metadata.inherit_global_tools:
            for name, tool_info in self.global_tools.items():
                all_tools[name] = tool_info['instance']
        
        # Add report-specific tools (can override global)
        for name, tool_info in self.report_tools.items():
            all_tools[name] = tool_info['instance']
        
        return all_tools
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Get a specific tool by name."""
        if name in self.report_tools:
            return self.report_tools[name]['instance']
        elif name in self.global_tools:
            return self.global_tools[name]['instance']
        return None
    
    def execute_bash_command(self, command: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a bash command using the global bash tool."""
        bash_tool = self.get_tool('bash_executor')
        if not bash_tool:
            return {
                'success': False,
                'error': 'Bash executor tool not available',
                'command': command,
                'output': '',
                'stderr': ''
            }
        
        return bash_tool.execute(command, config)
    
    def execute_bash_commands(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple bash commands."""
        bash_tool = self.get_tool('bash_executor')
        if not bash_tool:
            return [{
                'success': False,
                'error': 'Bash executor tool not available',
                'command': cmd,
                'output': '',
                'stderr': ''
            } for cmd in commands]
        
        return bash_tool.execute_multiple(commands)
    
    def create_llama_index_tools(self, report_definition: ReportDefinition) -> List[FunctionTool]:
        """Create LlamaIndex FunctionTool instances for agent use."""
        tools = []
        all_tools = self.get_all_tools(report_definition)
        
        # Create bash execution tool
        if 'bash_executor' in all_tools:
            bash_tool = all_tools['bash_executor']
            
            def execute_bash_wrapper(command: str) -> str:
                """Execute a bash command and return formatted results."""
                result = bash_tool.execute(command)
                if result['success']:
                    output = result['output']
                    if result['stderr']:
                        output += f"\nStderr: {result['stderr']}"
                    return f"Command: {command}\nOutput: {output}\nExecution time: {result['execution_time']:.2f}s"
                else:
                    return f"Command failed: {command}\nError: {result['error']}"
            
            bash_function_tool = FunctionTool.from_defaults(
                fn=execute_bash_wrapper,
                name="bash_executor",
                description="Execute bash commands safely with security restrictions. Returns command output and execution details."
            )
            tools.append(bash_function_tool)
        
        # Create file system tool
        if 'file_analyzer' in all_tools:
            file_tool = all_tools['file_analyzer']
            
            def read_file_wrapper(file_path: str, max_lines: Optional[int] = None) -> str:
                """Read a file safely and return its contents."""
                result = file_tool.read_file(file_path, max_lines)
                if result['success']:
                    return f"File: {file_path}\nSize: {result['size_bytes']} bytes\nContent:\n{result['content']}"
                else:
                    return f"Failed to read {file_path}: {result['error']}"
            
            def list_files_wrapper(directory: str, pattern: Optional[str] = None) -> str:
                """List files in a directory with optional pattern filtering."""
                result = file_tool.list_files(directory, pattern)
                if result['success']:
                    files_info = []
                    for file_info in result['files']:
                        files_info.append(f"{file_info['name']} ({file_info['size_bytes']} bytes)")
                    return f"Directory: {directory}\nFiles ({result['count']}):\n" + "\n".join(files_info)
                else:
                    return f"Failed to list files in {directory}: {result['error']}"
            
            file_read_tool = FunctionTool.from_defaults(
                fn=read_file_wrapper,
                name="read_file",
                description="Read file contents safely with size and extension restrictions."
            )
            
            file_list_tool = FunctionTool.from_defaults(
                fn=list_files_wrapper,
                name="list_files", 
                description="List files in a directory with optional pattern filtering."
            )
            
            tools.extend([file_read_tool, file_list_tool])
        
        # Create report-specific tools
        for tool_name, tool_instance in all_tools.items():
            if tool_name in ['bash_executor', 'file_analyzer', 'llm_analyzer']:
                continue  # Already handled above
            
            # Create generic wrapper for report-specific tools
            def create_tool_wrapper(tool_name: str, tool_instance: Any):
                def tool_wrapper(**kwargs) -> str:
                    """Generic wrapper for report-specific tools."""
                    try:
                        # Try to call a standard method if it exists
                        if hasattr(tool_instance, 'execute'):
                            result = tool_instance.execute(**kwargs)
                        elif hasattr(tool_instance, 'analyze'):
                            result = tool_instance.analyze(**kwargs)
                        else:
                            return f"Tool {tool_name} does not have a standard interface"
                        
                        if isinstance(result, dict) and 'success' in result:
                            if result['success']:
                                return str(result.get('output', result.get('result', 'Success')))
                            else:
                                return f"Tool {tool_name} failed: {result.get('error', 'Unknown error')}"
                        else:
                            return str(result)
                    except Exception as e:
                        return f"Tool {tool_name} error: {e}"
                
                return tool_wrapper
            
            # Get tool configuration for description
            tool_config = None
            for name, tool_info in self.report_tools.items():
                if name == tool_name:
                    tool_config = tool_info['config']
                    break
            if not tool_config:
                for name, tool_info in self.global_tools.items():
                    if name == tool_name:
                        tool_config = tool_info['config']
                        break
            
            description = tool_config.description if tool_config else f"Execute {tool_name} tool"
            
            tool_function = FunctionTool.from_defaults(
                fn=create_tool_wrapper(tool_name, tool_instance),
                name=tool_name,
                description=description
            )
            tools.append(tool_function)
        
        return tools
    
    def get_tool_status(self) -> Dict[str, Any]:
        """Get status information about loaded tools."""
        return {
            'global_tools': {
                'count': len(self.global_tools),
                'tools': list(self.global_tools.keys())
            },
            'report_tools': {
                'count': len(self.report_tools),
                'tools': list(self.report_tools.keys())
            },
            'registered_classes': list(self.tool_classes.keys())
        }
    
    def validate_tool_dependencies(self, report_definition: ReportDefinition) -> Dict[str, Any]:
        """Validate that all tool dependencies are satisfied."""
        validation_results = {
            'valid': True,
            'missing_dependencies': {},
            'warnings': []
        }
        
        all_available_tools = set(self.global_tools.keys()) | set(tool.name for tool in report_definition.tools)
        
        for tool_config in report_definition.tools:
            missing_deps = []
            for dep in tool_config.dependencies:
                if dep not in all_available_tools:
                    missing_deps.append(dep)
            
            if missing_deps:
                validation_results['valid'] = False
                validation_results['missing_dependencies'][tool_config.name] = missing_deps
        
        return validation_results