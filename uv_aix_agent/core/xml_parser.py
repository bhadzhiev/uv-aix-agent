import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

@dataclass
class ToolConfig:
    name: str
    scope: str  # 'global' or 'report'
    priority: str
    class_name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, bool] = field(default_factory=dict)
    error_handling: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

@dataclass
class GlobalToolsConfig:
    version: str
    description: str
    tools: List[ToolConfig] = field(default_factory=list)

@dataclass
class ReportMetadata:
    name: str
    version: str
    description: str
    inherit_global_tools: bool
    output_format: str
    author: Optional[str] = None

@dataclass
class AgentConfiguration:
    prompt_template: str
    max_iterations: int
    temperature: float
    response_format: str = "structured"

@dataclass
class BashCommand:
    name: str
    command: str
    tool: str
    timeout: int = 60

@dataclass
class DataCollection:
    bash_commands: List[BashCommand] = field(default_factory=list)
    file_analysis: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisTask:
    name: str
    priority: str
    description: str
    tool_sequence: List[Dict[str, str]] = field(default_factory=list)
    output_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OutputFormat:
    format: str
    structure: Dict[str, Any] = field(default_factory=dict)
    styling: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorHandling:
    bash_command_failures: Dict[str, str] = field(default_factory=dict)
    tool_failures: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 300
    fallback_output: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReportDefinition:
    metadata: ReportMetadata
    agent_configuration: AgentConfiguration
    data_collection: DataCollection
    analysis_tasks: List[AnalysisTask]
    output_format: OutputFormat
    error_handling: ErrorHandling
    tools: List[ToolConfig] = field(default_factory=list)

def parse_tool_config(tool_element: ET.Element) -> ToolConfig:
    """Parse a tool XML element into a ToolConfig object."""
    name = tool_element.get('name', '')
    scope = tool_element.get('scope', 'global')
    priority = tool_element.get('priority', 'medium')
    
    class_element = tool_element.find('class')
    class_name = class_element.text if class_element is not None else ''
    
    description_element = tool_element.find('description')
    description = description_element.text if description_element is not None else ''
    
    # Parse config
    config = {}
    config_element = tool_element.find('config')
    if config_element is not None:
        for child in config_element:
            if child.tag == 'allowed_commands':
                allowed_commands = []
                for cmd in child.findall('command'):
                    allowed_commands.append({
                        'pattern': cmd.get('pattern', ''),
                        'description': cmd.get('description', '')
                    })
                config['allowed_commands'] = allowed_commands
            elif child.tag == 'blocked_commands':
                blocked_commands = []
                for cmd in child.findall('command'):
                    blocked_commands.append({
                        'pattern': cmd.get('pattern', ''),
                        'reason': cmd.get('reason', '')
                    })
                config['blocked_commands'] = blocked_commands
            elif child.tag == 'allowed_extensions':
                # Parse list format like [".py", ".js", ".ts"]
                text = child.text.strip('[]')
                config['allowed_extensions'] = [ext.strip('"') for ext in text.split(',')]
            else:
                config[child.tag] = child.text
    
    # Parse permissions
    permissions = {}
    permissions_element = tool_element.find('permissions')
    if permissions_element is not None:
        for perm in permissions_element:
            permissions[perm.tag] = perm.text.lower() == 'true'
    
    # Parse error handling
    error_handling = {}
    error_element = tool_element.find('error_handling')
    if error_element is not None:
        for error in error_element:
            error_handling[error.tag] = error.get('action', error.text)
    
    # Parse dependencies
    dependencies = []
    deps_element = tool_element.find('dependencies')
    if deps_element is not None:
        for dep in deps_element.findall('requires_tool'):
            dependencies.append(dep.text)
    
    return ToolConfig(
        name=name,
        scope=scope,
        priority=priority,
        class_name=class_name,
        description=description,
        config=config,
        permissions=permissions,
        error_handling=error_handling,
        dependencies=dependencies
    )

def parse_global_tools(xml_path: str) -> GlobalToolsConfig:
    """Parse global tools XML configuration."""
    if not Path(xml_path).exists():
        raise FileNotFoundError(f"Global tools configuration not found: {xml_path}")
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Parse metadata
    metadata = root.find('metadata')
    version = metadata.find('version').text if metadata and metadata.find('version') is not None else '1.0'
    description = metadata.find('description').text if metadata and metadata.find('description') is not None else ''
    
    # Parse tools
    tools = []
    tools_element = root.find('tools')
    if tools_element is not None:
        for tool_element in tools_element.findall('tool'):
            tools.append(parse_tool_config(tool_element))
    
    return GlobalToolsConfig(
        version=version,
        description=description,
        tools=tools
    )

def parse_bash_commands(data_collection_element: ET.Element) -> List[BashCommand]:
    """Parse bash commands from data collection."""
    bash_commands = []
    bash_commands_element = data_collection_element.find('bash_commands')
    if bash_commands_element is not None:
        for cmd_element in bash_commands_element.findall('command'):
            name = cmd_element.get('name', '')
            tool = cmd_element.get('tool', 'bash_executor')
            command = cmd_element.text.strip() if cmd_element.text else ''
            timeout = int(cmd_element.get('timeout', '60'))
            
            bash_commands.append(BashCommand(
                name=name,
                command=command,
                tool=tool,
                timeout=timeout
            ))
    
    return bash_commands

def parse_analysis_tasks(tasks_element: ET.Element) -> List[AnalysisTask]:
    """Parse analysis tasks."""
    tasks = []
    if tasks_element is not None:
        for task_element in tasks_element.findall('task'):
            name = task_element.get('name', '')
            priority = task_element.get('priority', 'medium')
            
            description_element = task_element.find('description')
            description = description_element.text if description_element is not None else ''
            
            # Parse tool sequence
            tool_sequence = []
            sequence_element = task_element.find('tool_sequence')
            if sequence_element is not None:
                for step in sequence_element.findall('step'):
                    tool_sequence.append({
                        'tool': step.get('tool', ''),
                        'method': step.get('method', ''),
                        'command': step.get('command', '')
                    })
            
            # Parse output schema
            output_schema = {}
            schema_element = task_element.find('output_schema')
            if schema_element is not None:
                for field in schema_element.findall('field'):
                    field_name = field.get('name', '')
                    field_type = field.get('type', 'string')
                    output_schema[field_name] = {'type': field_type}
                    
                    # Add additional constraints
                    if field.get('max_items'):
                        output_schema[field_name]['max_items'] = int(field.get('max_items'))
                    if field.get('values'):
                        output_schema[field_name]['values'] = field.get('values').split(',')
            
            tasks.append(AnalysisTask(
                name=name,
                priority=priority,
                description=description,
                tool_sequence=tool_sequence,
                output_schema=output_schema
            ))
    
    return tasks

def parse_report_definition(xml_path: str) -> ReportDefinition:
    """Parse report definition XML configuration."""
    if not Path(xml_path).exists():
        raise FileNotFoundError(f"Report definition not found: {xml_path}")
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Parse metadata
    metadata_element = root.find('metadata')
    metadata = ReportMetadata(
        name=metadata_element.find('name').text if metadata_element.find('name') is not None else '',
        version=metadata_element.find('version').text if metadata_element.find('version') is not None else '1.0',
        description=metadata_element.find('description').text if metadata_element.find('description') is not None else '',
        inherit_global_tools=metadata_element.find('inherit_global_tools').text.lower() == 'true' if metadata_element.find('inherit_global_tools') is not None else True,
        output_format=metadata_element.find('output_format').text if metadata_element.find('output_format') is not None else 'xml',
        author=metadata_element.find('author').text if metadata_element.find('author') is not None else None
    )
    
    # Parse agent configuration
    agent_element = root.find('agent_configuration')
    agent_config = AgentConfiguration(
        prompt_template=agent_element.find('prompt_template').text if agent_element.find('prompt_template') is not None else '',
        max_iterations=int(agent_element.find('max_iterations').text) if agent_element.find('max_iterations') is not None else 3,
        temperature=float(agent_element.find('temperature').text) if agent_element.find('temperature') is not None else 0.3,
        response_format=agent_element.find('response_format').text if agent_element.find('response_format') is not None else 'structured'
    )
    
    # Parse data collection
    data_collection_element = root.find('data_collection')
    bash_commands = parse_bash_commands(data_collection_element) if data_collection_element is not None else []
    
    file_analysis = {}
    if data_collection_element is not None:
        file_analysis_element = data_collection_element.find('file_analysis')
        if file_analysis_element is not None:
            analyze_files = file_analysis_element.find('analyze_files')
            if analyze_files is not None:
                file_analysis = {
                    'tool': analyze_files.get('tool', ''),
                    'pattern': analyze_files.get('pattern', ''),
                    'check_for': analyze_files.find('check_for').text if analyze_files.find('check_for') is not None else '',
                    'max_files': int(analyze_files.find('max_files').text) if analyze_files.find('max_files') is not None else 50
                }
    
    data_collection = DataCollection(
        bash_commands=bash_commands,
        file_analysis=file_analysis
    )
    
    # Parse analysis tasks
    tasks_element = root.find('analysis_tasks')
    analysis_tasks = parse_analysis_tasks(tasks_element)
    
    # Parse output format
    output_element = root.find('output_format')
    output_format = OutputFormat(
        format=output_element.find('format').text if output_element and output_element.find('format') is not None else 'xml'
    )
    
    # Parse error handling
    error_element = root.find('error_handling')
    error_handling = ErrorHandling()
    if error_element is not None:
        timeout_element = error_element.find('timeout_seconds')
        if timeout_element is not None:
            error_handling.timeout_seconds = int(timeout_element.text)
    
    # Parse report-specific tools
    tools = []
    tools_element = root.find('tools')
    if tools_element is not None:
        for tool_element in tools_element.findall('tool'):
            tools.append(parse_tool_config(tool_element))
    
    return ReportDefinition(
        metadata=metadata,
        agent_configuration=agent_config,
        data_collection=data_collection,
        analysis_tasks=analysis_tasks,
        output_format=output_format,
        error_handling=error_handling,
        tools=tools
    )