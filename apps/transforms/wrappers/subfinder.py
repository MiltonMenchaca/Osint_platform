"""Subfinder wrapper for passive subdomain enumeration"""

import logging
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class SubfinderWrapper(BaseWrapper):
    """Wrapper for ProjectDiscovery Subfinder"""

    def get_tool_name(self) -> str:
        return "subfinder"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Configuration
        timeout = int(kwargs.get("timeout", 120)) # Increased default timeout
        threads = int(kwargs.get("threads", 10))  # Default to 10 threads to avoid blocking/rate limits
        silent = bool(kwargs.get("silent", True))
        include_all_sources = bool(kwargs.get("all", False))
        sources = kwargs.get("sources")

        command = [self.tool_path, "-d", input_value, "-silent", "-oJ", "-t", str(threads)]

        if include_all_sources:
            command.append("-all")

        if isinstance(sources, list) and sources:
            sources_csv = ",".join([str(s).strip() for s in sources if str(s).strip()])
            if sources_csv:
                command.extend(["-sources", sources_csv])

        try:
            result = self._run_command(command, timeout=timeout)
            subdomains = self._parse_line_output(result["stdout"])

            results: List[Dict[str, Any]] = []
            seen = set()
            for subdomain in subdomains:
                if not subdomain or subdomain == input_value:
                    continue
                if subdomain in seen:
                    continue
                seen.add(subdomain)
                results.append(
                    {
                        "type": "domain",
                        "value": subdomain,
                        "source": "subfinder",
                        "confidence": 0.75,
                        "properties": {"parent_domain": input_value},
                    }
                )

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Subfinder execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()
