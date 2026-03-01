"""Dmitry wrapper for information gathering"""

import logging
import re
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class DmitryWrapper(BaseWrapper):
    """Wrapper for Dmitry information gathering tool"""

    def get_tool_name(self) -> str:
        return "dmitry"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "ip"]

    def get_supported_output_types(self) -> List[str]:
        return ["subdomain", "email", "ip", "port", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 120))
        # Default options: whois (-w), subdomains (-s), emails (-e), ports (-p)
        options = kwargs.get("options", "winse")
        
        command = [self.tool_path, "-" + options, input_value]
        
        try:
            result = self._run_command(command, timeout=timeout)
            
            # Parse output
            results = self._parse_dmitry_output(result["stdout"])
            
            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "items_found": len(results),
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Dmitry execution failed: {e}")
            raise

    def _parse_dmitry_output(self, stdout: str) -> List[Dict[str, Any]]:
        """Parse Dmitry stdout for findings"""
        results = []
        
        # Parse Subdomains
        subdomain_pattern = re.compile(r"HostName: ([a-zA-Z0-9\.\-]+)\s+IP: ([0-9\.]+)")
        for match in subdomain_pattern.finditer(stdout):
            hostname, ip = match.groups()
            results.append({
                "type": "subdomain",
                "value": hostname,
                "source": "dmitry",
                "confidence": 0.8,
                "properties": {"ip": ip},
            })
            results.append({
                "type": "ip",
                "value": ip,
                "source": "dmitry",
                "confidence": 0.8,
                "properties": {"hostname": hostname},
            })

        # Parse Emails
        email_pattern = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
        for match in email_pattern.finditer(stdout):
            email = match.group(1)
            # Filter out false positives (like example.com or specific internal strings if needed)
            if "dmitry" not in email.lower() and "example" not in email.lower():
                results.append({
                    "type": "email",
                    "value": email,
                    "source": "dmitry",
                    "confidence": 0.6,
                    "properties": {},
                })

        # Parse Ports
        port_pattern = re.compile(r"Port\s+(\d+)\s+:\s+(\w+)\s+:\s+(open|closed|filtered)")
        for match in port_pattern.finditer(stdout):
            port, proto, state = match.groups()
            if state.lower() == "open":
                results.append({
                    "type": "port",
                    "value": f"{port}/{proto}",
                    "source": "dmitry",
                    "confidence": 0.9,
                    "properties": {
                        "port": int(port),
                        "protocol": proto,
                        "state": state,
                    },
                })

        return results
