import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.agent import FunctionCallingAgentWorker, AgentRunner

from .xml_parser import ReportDefinition, parse_report_definition
from .tool_manager import ToolManager

class XMLReportGenerator:
    """Generates reports based on XML configuration."""
    
    def __init__(self, report_xml_path: str, config: Dict[str, Any]):
        self.config = config
        self.report_definition = parse_report_definition(report_xml_path)
        self.tool_manager = ToolManager()
        
        self._setup_llm_and_embedding_model()
        self._load_tools()
    
    def _setup_llm_and_embedding_model(self):
        """Setup LLM and embedding models."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")

        if self.config["provider"] == "openai":
            Settings.llm = OpenAI(
                model=self.config["llm_model"],
                api_key=api_key,
                temperature=self.report_definition.agent_configuration.temperature
            )
        else:
            raise ValueError(f"Provider '{self.config['provider']}' not supported in XML reports yet.")

        Settings.embed_model = HuggingFaceEmbedding(
            model_name=self.config["embedding_model"]
        )
    
    def _load_tools(self):
        """Load and validate tools for this report."""
        # Load report-specific tools
        self.tool_manager.load_report_tools(self.report_definition)
        
        # Validate dependencies
        validation = self.tool_manager.validate_tool_dependencies(self.report_definition)
        if not validation['valid']:
            print("Warning: Tool dependency issues found:")
            for tool, missing_deps in validation['missing_dependencies'].items():
                print(f"  - {tool}: missing {missing_deps}")
    
    def _execute_data_collection(self) -> Dict[str, Any]:
        """Execute data collection phase."""
        collection_results = {
            'bash_commands': {},
            'file_analysis': {},
            'errors': []
        }
        
        # Execute bash commands
        for bash_cmd in self.report_definition.data_collection.bash_commands:
            print(f"Executing bash command: {bash_cmd.name}")
            
            try:
                result = self.tool_manager.execute_bash_command(
                    bash_cmd.command, 
                    {'timeout': bash_cmd.timeout}
                )
                collection_results['bash_commands'][bash_cmd.name] = result
                
                if not result['success']:
                    collection_results['errors'].append(f"Bash command '{bash_cmd.name}' failed: {result['error']}")
                    
            except Exception as e:
                error_msg = f"Error executing bash command '{bash_cmd.name}': {e}"
                collection_results['errors'].append(error_msg)
                print(f"Error: {error_msg}")
        
        # Execute file analysis
        file_analysis_config = self.report_definition.data_collection.file_analysis
        if file_analysis_config:
            file_tool = self.tool_manager.get_tool('file_analyzer')
            if file_tool:
                try:
                    # List files matching pattern
                    files_result = file_tool.list_files('.', file_analysis_config.get('pattern'))
                    collection_results['file_analysis']['files_found'] = files_result
                    
                    # Analyze subset of files
                    max_files = file_analysis_config.get('max_files', 10)
                    if files_result['success'] and files_result['files']:
                        analyzed_files = []
                        for file_info in files_result['files'][:max_files]:
                            file_content = file_tool.read_file(file_info['path'])
                            if file_content['success']:
                                analyzed_files.append({
                                    'path': file_info['path'],
                                    'size': file_info['size_bytes'],
                                    'content_preview': file_content['content'][:500] + '...' if len(file_content['content']) > 500 else file_content['content']
                                })
                        collection_results['file_analysis']['analyzed_files'] = analyzed_files
                
                except Exception as e:
                    error_msg = f"Error in file analysis: {e}"
                    collection_results['errors'].append(error_msg)
                    print(f"Error: {error_msg}")
        
        return collection_results
    
    def _execute_analysis_tasks(self, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis tasks using the agent."""
        analysis_results = {}
        
        # Create LlamaIndex tools
        llama_tools = self.tool_manager.create_llama_index_tools(self.report_definition)
        
        # Create agent
        agent_worker = FunctionCallingAgentWorker.from_tools(
            tools=llama_tools,
            llm=Settings.llm,
            verbose=True,
            max_function_calls=self.report_definition.agent_configuration.max_iterations
        )
        agent = AgentRunner(agent_worker)
        
        # Execute each analysis task
        for task in self.report_definition.analysis_tasks:
            print(f"Executing analysis task: {task.name}")
            
            try:
                # Build task prompt
                task_prompt = f"""
                Task: {task.description}
                Priority: {task.priority}
                
                Available data from collection phase:
                {json.dumps(collection_data, indent=2)}
                
                Please analyze this data and provide structured results according to the task requirements.
                Focus on: {task.description}
                
                Tool sequence to follow:
                {json.dumps(task.tool_sequence, indent=2)}
                """
                
                # Execute with agent
                response = agent.query(task_prompt)
                
                analysis_results[task.name] = {
                    'success': True,
                    'result': response.response,
                    'priority': task.priority,
                    'description': task.description
                }
                
            except Exception as e:
                error_msg = f"Error executing analysis task '{task.name}': {e}"
                print(f"Error: {error_msg}")
                analysis_results[task.name] = {
                    'success': False,
                    'error': error_msg,
                    'priority': task.priority,
                    'description': task.description
                }
        
        return analysis_results
    
    def _format_xml_output(self, collection_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> str:
        """Format results as XML output."""
        # Create root element
        root = ET.Element('report')
        
        # Add metadata
        metadata = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata, 'name').text = self.report_definition.metadata.name
        ET.SubElement(metadata, 'version').text = self.report_definition.metadata.version
        ET.SubElement(metadata, 'generated_at').text = datetime.now().isoformat()
        ET.SubElement(metadata, 'description').text = self.report_definition.metadata.description
        
        # Add data collection results
        data_section = ET.SubElement(root, 'data_collection')
        
        # Bash commands results
        bash_section = ET.SubElement(data_section, 'bash_commands')
        for cmd_name, result in collection_data['bash_commands'].items():
            cmd_element = ET.SubElement(bash_section, 'command')
            cmd_element.set('name', cmd_name)
            cmd_element.set('success', str(result['success']).lower())
            
            if result['success']:
                ET.SubElement(cmd_element, 'output').text = result.get('output', '')
                ET.SubElement(cmd_element, 'execution_time').text = str(result.get('execution_time', 0))
            else:
                ET.SubElement(cmd_element, 'error').text = result.get('error', '')
        
        # File analysis results
        if collection_data['file_analysis']:
            file_section = ET.SubElement(data_section, 'file_analysis')
            files_found = collection_data['file_analysis'].get('files_found', {})
            if files_found.get('success'):
                ET.SubElement(file_section, 'files_count').text = str(files_found.get('count', 0))
                
                analyzed_files = collection_data['file_analysis'].get('analyzed_files', [])
                for file_info in analyzed_files:
                    file_element = ET.SubElement(file_section, 'analyzed_file')
                    file_element.set('path', file_info['path'])
                    file_element.set('size', str(file_info['size']))
                    ET.SubElement(file_element, 'content_preview').text = file_info['content_preview']
        
        # Add analysis results
        analysis_section = ET.SubElement(root, 'analysis_results')
        
        for task_name, task_result in analysis_results.items():
            task_element = ET.SubElement(analysis_section, 'task')
            task_element.set('name', task_name)
            task_element.set('priority', task_result['priority'])
            task_element.set('success', str(task_result['success']).lower())
            
            ET.SubElement(task_element, 'description').text = task_result['description']
            
            if task_result['success']:
                ET.SubElement(task_element, 'result').text = task_result['result']
            else:
                ET.SubElement(task_element, 'error').text = task_result.get('error', '')
        
        # Add errors section if any
        if collection_data['errors']:
            errors_section = ET.SubElement(root, 'errors')
            for error in collection_data['errors']:
                ET.SubElement(errors_section, 'error').text = error
        
        # Add tool information
        tools_section = ET.SubElement(root, 'tools_used')
        tool_status = self.tool_manager.get_tool_status()
        
        global_tools = ET.SubElement(tools_section, 'global_tools')
        global_tools.set('count', str(tool_status['global_tools']['count']))
        for tool_name in tool_status['global_tools']['tools']:
            ET.SubElement(global_tools, 'tool').text = tool_name
        
        report_tools = ET.SubElement(tools_section, 'report_tools')
        report_tools.set('count', str(tool_status['report_tools']['count']))
        for tool_name in tool_status['report_tools']['tools']:
            ET.SubElement(report_tools, 'tool').text = tool_name
        
        # Format XML with pretty printing
        self._indent_xml(root)
        return ET.tostring(root, encoding='unicode')
    
    def _indent_xml(self, elem, level=0):
        """Add pretty printing indentation to XML."""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def generate_report(self) -> str:
        """Generate the complete report."""
        print(f"Generating XML report: {self.report_definition.metadata.name}")
        print(f"Using {len(self.tool_manager.global_tools)} global tools and {len(self.tool_manager.report_tools)} report tools")
        
        try:
            # Execute data collection
            print("Phase 1: Data Collection")
            collection_data = self._execute_data_collection()
            
            # Execute analysis tasks
            print("Phase 2: Analysis")
            analysis_results = self._execute_analysis_tasks(collection_data)
            
            # Format output
            print("Phase 3: Formatting Output")
            if self.report_definition.output_format.format.lower() == 'xml':
                output = self._format_xml_output(collection_data, analysis_results)
            else:
                # Fallback to JSON if XML formatting fails
                output = json.dumps({
                    'metadata': {
                        'name': self.report_definition.metadata.name,
                        'generated_at': datetime.now().isoformat()
                    },
                    'data_collection': collection_data,
                    'analysis_results': analysis_results
                }, indent=2)
            
            print("Report generation completed successfully")
            return output
            
        except Exception as e:
            error_msg = f"Report generation failed: {e}"
            print(f"Error: {error_msg}")
            
            # Return error XML
            root = ET.Element('report_error')
            ET.SubElement(root, 'message').text = error_msg
            ET.SubElement(root, 'timestamp').text = datetime.now().isoformat()
            ET.SubElement(root, 'report_name').text = self.report_definition.metadata.name
            
            return ET.tostring(root, encoding='unicode')