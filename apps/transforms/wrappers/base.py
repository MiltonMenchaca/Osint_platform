"""Base wrapper class for OSINT tools"""

import json
import logging
import os
import shutil
import string
import subprocess
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OSINTToolError(Exception):
    """Base exception for OSINT tool errors"""

    pass


class ToolNotFoundError(OSINTToolError):
    """Raised when a tool is not found in the system"""

    pass


class ToolTimeoutError(OSINTToolError):
    """Raised when a tool execution times out"""

    pass


class ToolExecutionError(OSINTToolError):
    """Raised when a tool execution fails"""

    pass


class BaseWrapper(ABC):
    """Base class for all OSINT tool wrappers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tool_name = self.get_tool_name()
        self.tool_path = self._find_tool_path()
        self.temp_dir = None

        # Validate tool availability
        if not self.is_tool_available():
            raise ToolNotFoundError(f"Tool '{self.tool_name}' not found in system PATH")

    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the name of the tool"""
        pass

    @abstractmethod
    def get_supported_input_types(self) -> List[str]:
        """Return list of supported input entity types"""
        pass

    @abstractmethod
    def get_supported_output_types(self) -> List[str]:
        """Return list of supported output entity types"""
        pass

    @abstractmethod
    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute the tool with given input data"""
        pass

    def _find_tool_path(self) -> Optional[str]:
        """Find the tool in system PATH"""
        return shutil.which(self.tool_name)

    def is_tool_available(self) -> bool:
        """Check if the tool is available in the system"""
        return self.tool_path is not None

    def get_version(self) -> Optional[str]:
        """Get tool version"""
        try:
            result = self._run_command([self.tool_path, "--version"], timeout=10)
            return result.get("stdout", "").strip()
        except Exception as e:
            logger.warning(f"Could not get version for {self.tool_name}: {e}")
            return None

    def _run_command(
        self,
        command: List[str],
        timeout: int = 300,
        input_data: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Run a command and return the result"""

        start_time = datetime.now()

        try:
            safe_command = self._redact_command(command)
            safe_command_str = " ".join(safe_command)
            logger.info(f"Executing command: {safe_command_str}")

            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            # Execute command
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                text=True,
                cwd=cwd,
                env=exec_env,
            )

            try:
                stdout, stderr = process.communicate(input=input_data, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise ToolTimeoutError(
                    f"Command timed out after {timeout} seconds: {' '.join(command)}"
                )

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            result = {
                "command": safe_command_str,
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": execution_time,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }

            logger.info(
                f"Command completed in {execution_time:.2f}s with return code {process.returncode}"
            )

            if process.returncode != 0:
                logger.error(f"Command failed: {stderr}")
                raise ToolExecutionError(
                    f"Command failed with return code {process.returncode}: {stderr}"
                )

            return result

        except (OSError, FileNotFoundError) as e:
            raise ToolNotFoundError(f"Could not execute command: {e}")
        except Exception as e:
            if isinstance(e, (ToolTimeoutError, ToolExecutionError)):
                raise
            raise OSINTToolError(f"Unexpected error executing command: {e}")

    def _looks_like_secret(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        if len(value) < 28:
            return False
        if value.startswith("-"):
            return False
        if any(ch.isspace() for ch in value):
            return False
        if "/" in value or "\\" in value:
            return False
        allowed = set(string.ascii_letters + string.digits + "-_")
        return all(ch in allowed for ch in value)

    def _redact_command(self, command: List[str]) -> List[str]:
        if not command:
            return []

        redacted: List[str] = []
        redact_next = False

        for idx, part in enumerate(command):
            if redact_next:
                redacted.append("***")
                redact_next = False
                continue

            lower = part.lower() if isinstance(part, str) else ""
            if lower in {"--key", "--token", "--password", "--secret"}:
                redacted.append(part)
                redact_next = True
                continue

            prev = command[idx - 1].lower() if idx > 0 and isinstance(command[idx - 1], str) else ""
            if self.tool_name == "shodan" and prev == "init":
                redacted.append("***")
                continue

            if isinstance(part, str) and self._looks_like_secret(part):
                redacted.append("***")
                continue

            redacted.append(part)

        return redacted

    def _create_temp_dir(self) -> str:
        """Create a temporary directory for tool execution"""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix=f"{self.tool_name}_")
            logger.debug(f"Created temp directory: {self.temp_dir}")
        return self.temp_dir

    def _cleanup_temp_dir(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(
                    f"Could not clean up temp directory {self.temp_dir}: {e}"
                )
            finally:
                self.temp_dir = None

    def _parse_json_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse JSON output from tool"""
        try:
            # Handle multiple JSON objects separated by newlines
            results = []
            for line in output.strip().split("\n"):
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        continue
            return results
        except Exception as e:
            logger.error(f"Error parsing JSON output: {e}")
            return []

    def _parse_line_output(self, output: str) -> List[str]:
        """Parse line-based output from tool"""
        return [line.strip() for line in output.strip().split("\n") if line.strip()]

    def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")

        if "type" not in input_data:
            raise ValueError("Input data must contain 'type' field")

        if "value" not in input_data:
            raise ValueError("Input data must contain 'value' field")

        input_type = input_data["type"]
        supported_types = self.get_supported_input_types()

        if input_type not in supported_types:
            raise ValueError(
                f"Input type '{input_type}' not supported. "
                f"Supported types: {', '.join(supported_types)}"
            )

        return True

    def _format_output(
        self, results: List[Dict[str, Any]], execution_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format tool output in standard format"""
        metadata: Dict[str, Any] = {
            "execution_time": execution_info.get("execution_time"),
            "start_time": execution_info.get("start_time"),
            "end_time": execution_info.get("end_time"),
            "command": execution_info.get("command"),
            "tool_version": self.get_version(),
            "result_count": len(results),
        }

        for key, value in execution_info.items():
            if key in {
                "input_type",
                "input_value",
                "execution_time",
                "start_time",
                "end_time",
                "command",
            }:
                continue
            if key not in metadata:
                metadata[key] = value

        return {
            "tool": self.tool_name,
            "input_type": execution_info.get("input_type"),
            "input_value": execution_info.get("input_value"),
            "results": results,
            "metadata": metadata,
        }

    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about the tool"""
        return {
            "name": self.tool_name,
            "path": self.tool_path,
            "version": self.get_version(),
            "available": self.is_tool_available(),
            "supported_input_types": self.get_supported_input_types(),
            "supported_output_types": self.get_supported_output_types(),
            "config": self.config,
        }

    def test_tool(self) -> Dict[str, Any]:
        """Test if the tool is working correctly"""
        try:
            version = self.get_version()
            return {
                "tool": self.tool_name,
                "available": True,
                "version": version,
                "test_passed": True,
                "message": f"Tool {self.tool_name} is working correctly",
            }
        except Exception as e:
            return {
                "tool": self.tool_name,
                "available": False,
                "version": None,
                "test_passed": False,
                "message": f"Tool test failed: {str(e)}",
            }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self._cleanup_temp_dir()

    def __del__(self):
        """Destructor - cleanup resources"""
        self._cleanup_temp_dir()
