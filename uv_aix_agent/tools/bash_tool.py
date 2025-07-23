import subprocess
import re
import os
import signal
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time

class BashCommandTool:
    """Safe bash command execution tool with security restrictions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout_seconds = config.get('timeout_seconds', 60)
        self.working_directory = config.get('working_directory', 'auto_detect')
        self.allowed_commands = config.get('allowed_commands', [])
        self.blocked_commands = config.get('blocked_commands', [])
        
        # Set working directory
        if self.working_directory == 'auto_detect':
            self.working_directory = os.getcwd()
        
        # Compile regex patterns for performance
        self.allowed_patterns = [re.compile(cmd['pattern']) for cmd in self.allowed_commands]
        self.blocked_patterns = [(re.compile(cmd['pattern']), cmd['reason']) for cmd in self.blocked_commands]
    
    def is_command_allowed(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if a command is allowed to execute."""
        command = command.strip()
        
        # Check blocked commands first (security priority)
        for pattern, reason in self.blocked_patterns:
            if pattern.match(command):
                return False, f"Command blocked: {reason}"
        
        # Check allowed commands
        if self.allowed_patterns:
            for pattern in self.allowed_patterns:
                if pattern.match(command):
                    return True, None
            return False, "Command not in allowed list"
        
        # If no allowed patterns defined, allow by default (but still check blocked)
        return True, None
    
    def execute(self, command: str, additional_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a bash command with safety checks."""
        config = {**self.config, **(additional_config or {})}
        timeout = config.get('timeout', self.timeout_seconds)
        
        # Validate command
        is_allowed, reason = self.is_command_allowed(command)
        if not is_allowed:
            return {
                'success': False,
                'error': reason,
                'command': command,
                'output': '',
                'stderr': '',
                'execution_time': 0
            }
        
        start_time = time.time()
        
        try:
            # Execute command with timeout
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_directory,
                preexec_fn=os.setsid  # Create new process group for cleanup
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                execution_time = time.time() - start_time
                
                return {
                    'success': process.returncode == 0,
                    'return_code': process.returncode,
                    'command': command,
                    'output': stdout,
                    'stderr': stderr,
                    'execution_time': execution_time,
                    'working_directory': self.working_directory
                }
                
            except subprocess.TimeoutExpired:
                # Kill the entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.communicate()  # Clean up
                
                return {
                    'success': False,
                    'error': f'Command timed out after {timeout} seconds',
                    'command': command,
                    'output': '',
                    'stderr': '',
                    'execution_time': timeout,
                    'timeout': True
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'command': command,
                'output': '',
                'stderr': '',
                'execution_time': execution_time
            }
    
    def execute_multiple(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple commands in sequence."""
        results = []
        for command in commands:
            result = self.execute(command)
            results.append(result)
            
            # Stop on first failure if configured
            if not result['success'] and self.config.get('stop_on_failure', False):
                break
        
        return results
    
    def get_command_suggestions(self, blocked_command: str) -> List[str]:
        """Suggest alternative commands for blocked ones."""
        suggestions = []
        
        # Basic suggestions for common blocked patterns
        if 'rm ' in blocked_command:
            suggestions.append("Use 'ls' to list files instead of deleting")
            suggestions.append("Consider using 'mv' to move files to a backup location")
        
        elif 'sudo ' in blocked_command:
            suggestions.append("Try running without sudo if possible")
            suggestions.append("Check if the operation can be done with current permissions")
        
        elif 'chmod ' in blocked_command:
            suggestions.append("File permissions are managed by the system")
            suggestions.append("Use 'ls -la' to check current permissions")
        
        elif '>' in blocked_command or '>>' in blocked_command:
            suggestions.append("IO redirection is disabled for security")
            suggestions.append("Use command output directly in your analysis")
        
        return suggestions
    
    def validate_working_directory(self) -> bool:
        """Validate that the working directory is safe and accessible."""
        try:
            path = Path(self.working_directory)
            return path.exists() and path.is_dir() and os.access(path, os.R_OK)
        except Exception:
            return False
    
    def get_allowed_commands_help(self) -> List[str]:
        """Get help text for allowed commands."""
        help_text = []
        for cmd in self.allowed_commands:
            help_text.append(f"✓ {cmd['pattern']}: {cmd['description']}")
        return help_text
    
    def get_blocked_commands_help(self) -> List[str]:
        """Get help text for blocked commands."""
        help_text = []
        for cmd in self.blocked_commands:
            help_text.append(f"✗ {cmd['pattern']}: {cmd['reason']}")
        return help_text


class FileSystemTool:
    """Safe file system operations tool."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_file_size_mb = config.get('max_file_size_mb', 10)
        self.allowed_extensions = config.get('allowed_extensions', [])
        self.read_files = config.get('read_files', True)
        self.write_files = config.get('write_files', False)
    
    def is_file_allowed(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file operations are allowed on this file."""
        path = Path(file_path)
        
        # Check if file exists for read operations
        if not path.exists():
            return False, "File does not exist"
        
        # Check file size
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                return False, f"File too large: {size_mb:.1f}MB > {self.max_file_size_mb}MB"
        except Exception as e:
            return False, f"Cannot check file size: {e}"
        
        # Check extension if restricted
        if self.allowed_extensions and path.suffix not in self.allowed_extensions:
            return False, f"File extension {path.suffix} not allowed"
        
        return True, None
    
    def read_file(self, file_path: str, max_lines: Optional[int] = None) -> Dict[str, Any]:
        """Safely read a file."""
        if not self.read_files:
            return {
                'success': False,
                'error': 'File reading not permitted',
                'content': ''
            }
        
        is_allowed, reason = self.is_file_allowed(file_path)
        if not is_allowed:
            return {
                'success': False,
                'error': reason,
                'content': ''
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    content = ''.join(lines)
                else:
                    content = f.read()
                
                return {
                    'success': True,
                    'content': content,
                    'file_path': file_path,
                    'size_bytes': len(content.encode('utf-8'))
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read file: {e}',
                'content': ''
            }
    
    def list_files(self, directory: str, pattern: Optional[str] = None) -> Dict[str, Any]:
        """List files in a directory."""
        try:
            path = Path(directory)
            if not path.exists() or not path.is_dir():
                return {
                    'success': False,
                    'error': 'Directory does not exist or is not a directory',
                    'files': []
                }
            
            files = []
            for file_path in path.iterdir():
                if file_path.is_file():
                    # Apply pattern filter if provided
                    if pattern and not re.search(pattern, file_path.name):
                        continue
                    
                    # Check if file is allowed
                    is_allowed, _ = self.is_file_allowed(str(file_path))
                    if is_allowed:
                        files.append({
                            'name': file_path.name,
                            'path': str(file_path),
                            'size_bytes': file_path.stat().st_size,
                            'extension': file_path.suffix
                        })
            
            return {
                'success': True,
                'files': files,
                'directory': directory,
                'count': len(files)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list files: {e}',
                'files': []
            }


class LLMAnalysisTool:
    """General purpose LLM analysis tool."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_context_tokens = config.get('max_context_tokens', 4000)
        self.temperature = config.get('temperature', 0.3)
        self.response_format = config.get('response_format', 'structured')
    
    def analyze_text(self, text: str, analysis_prompt: str, llm_instance) -> Dict[str, Any]:
        """Analyze text using LLM."""
        try:
            # Truncate text if too long
            if len(text) > self.max_context_tokens * 4:  # Rough token estimation
                text = text[:self.max_context_tokens * 4]
                text += "\n\n[TEXT TRUNCATED FOR ANALYSIS]"
            
            full_prompt = f"{analysis_prompt}\n\nText to analyze:\n{text}"
            
            response = llm_instance.complete(full_prompt)
            
            return {
                'success': True,
                'analysis': response.text,
                'prompt_used': analysis_prompt,
                'text_length': len(text)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM analysis failed: {e}',
                'analysis': ''
            }
    
    def synthesize_findings(self, findings: List[Dict[str, Any]], synthesis_prompt: str, llm_instance) -> Dict[str, Any]:
        """Synthesize multiple findings into a cohesive analysis."""
        try:
            findings_text = ""
            for i, finding in enumerate(findings):
                findings_text += f"Finding {i+1}:\n{finding}\n\n"
            
            full_prompt = f"{synthesis_prompt}\n\nFindings to synthesize:\n{findings_text}"
            
            response = llm_instance.complete(full_prompt)
            
            return {
                'success': True,
                'synthesis': response.text,
                'findings_count': len(findings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Synthesis failed: {e}',
                'synthesis': ''
            }