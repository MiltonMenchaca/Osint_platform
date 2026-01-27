"""Shodan wrapper for network reconnaissance"""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class ShodanWrapper(BaseWrapper):
    """Wrapper for Shodan CLI tool"""

    def get_tool_name(self) -> str:
        return "shodan"

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "domain", "hostname", "cidr", "asn"]

    def get_supported_output_types(self) -> List[str]:
        return ["ip", "port", "service", "vulnerability", "certificate", "location"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key") or self._get_api_key_from_env()

        if not self.api_key:
            logger.warning("No Shodan API key configured. Some features may not work.")

    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables"""
        import os

        return os.getenv("SHODAN_API_KEY")

    def _setup_api_key(self):
        """Setup API key for shodan CLI"""
        if self.api_key:
            try:
                self._run_command([self.tool_path, "init", self.api_key], timeout=30)
                logger.info("Shodan API key configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Shodan API key: {e}")
                raise

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute shodan search"""

        # Validate input
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Get configuration options
        search_type = kwargs.get("search_type", "host")  # host, search, count
        limit = kwargs.get("limit", 100)
        timeout = kwargs.get("timeout", 180)

        # Setup API key if needed
        if self.api_key and search_type in ["host", "search", "count"]:
            self._setup_api_key()

        try:
            if search_type == "host" and input_type == "ip":
                return self._execute_host_lookup(input_value, timeout)
            elif search_type == "search":
                return self._execute_search(input_value, limit, timeout)
            elif search_type == "count":
                return self._execute_count(input_value, timeout)
            elif search_type == "scan":
                return self._execute_scan(input_value, timeout)
            else:
                raise ValueError(f"Unsupported search type: {search_type}")

        except Exception as e:
            logger.error(f"Shodan execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _execute_host_lookup(self, ip: str, timeout: int) -> Dict[str, Any]:
        """Execute host lookup for specific IP"""

        command = [self.tool_path, "host", ip]
        result = self._run_command(command, timeout=timeout)

        try:
            # Parse JSON output
            host_data = json.loads(result["stdout"])

            # Extract information
            results = []

            # Basic host info
            results.append(
                {
                    "type": "ip",
                    "value": host_data.get("ip_str", ip),
                    "source": "shodan",
                    "confidence": 1.0,
                    "properties": {
                        "country": host_data.get("country_name"),
                        "city": host_data.get("city"),
                        "org": host_data.get("org"),
                        "isp": host_data.get("isp"),
                        "asn": host_data.get("asn"),
                        "hostnames": host_data.get("hostnames", []),
                        "last_update": host_data.get("last_update"),
                    },
                }
            )

            # Services/ports
            for service in host_data.get("data", []):
                port = service.get("port")
                transport = service.get("transport", "tcp")

                results.append(
                    {
                        "type": "service",
                        "value": f"{ip}:{port}/{transport}",
                        "source": "shodan",
                        "confidence": 0.9,
                        "properties": {
                            "ip": ip,
                            "port": port,
                            "transport": transport,
                            "product": service.get("product"),
                            "version": service.get("version"),
                            "banner": service.get("data", "").strip()[
                                :500
                            ],  # Limit banner size
                            "timestamp": service.get("timestamp"),
                            "ssl": service.get("ssl", {}),
                            "location": {
                                "country": service.get("location", {}).get(
                                    "country_name"
                                ),
                                "city": service.get("location", {}).get("city"),
                            },
                        },
                    }
                )

            # Vulnerabilities
            for vuln in host_data.get("vulns", []):
                results.append(
                    {
                        "type": "vulnerability",
                        "value": vuln,
                        "source": "shodan",
                        "confidence": 0.8,
                        "properties": {
                            "ip": ip,
                            "cve": vuln,
                            "verified": host_data.get("vulns", {})
                            .get(vuln, {})
                            .get("verified", False),
                        },
                    }
                )

            execution_info = {
                "input_type": "ip",
                "input_value": ip,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
            }

            return self._format_output(results, execution_info)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Shodan JSON output: {e}")
            raise

    def _execute_search(self, query: str, limit: int, timeout: int) -> Dict[str, Any]:
        """Execute search query"""

        command = [self.tool_path, "search", "--limit", str(limit), query]
        result = self._run_command(command, timeout=timeout)

        # Parse line-based output
        lines = self._parse_line_output(result["stdout"])

        results = []
        for line in lines:
            try:
                # Each line should be JSON
                data = json.loads(line)

                ip = data.get("ip_str")
                port = data.get("port")
                transport = data.get("transport", "tcp")

                results.append(
                    {
                        "type": "service",
                        "value": f"{ip}:{port}/{transport}",
                        "source": "shodan",
                        "confidence": 0.8,
                        "properties": {
                            "ip": ip,
                            "port": port,
                            "transport": transport,
                            "product": data.get("product"),
                            "version": data.get("version"),
                            "banner": data.get("data", "").strip()[:500],
                            "timestamp": data.get("timestamp"),
                            "org": data.get("org"),
                            "location": {
                                "country": data.get("location", {}).get("country_name"),
                                "city": data.get("location", {}).get("city"),
                            },
                        },
                    }
                )

            except json.JSONDecodeError:
                # Skip non-JSON lines
                continue

        execution_info = {
            "input_type": "query",
            "input_value": query,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }

        return self._format_output(results, execution_info)

    def _execute_count(self, query: str, timeout: int) -> Dict[str, Any]:
        """Execute count query"""

        command = [self.tool_path, "count", query]
        result = self._run_command(command, timeout=timeout)

        try:
            count_data = json.loads(result["stdout"])

            results = [
                {
                    "type": "count",
                    "value": str(count_data.get("total", 0)),
                    "source": "shodan",
                    "confidence": 1.0,
                    "properties": {
                        "query": query,
                        "total": count_data.get("total", 0),
                        "facets": count_data.get("facets", {}),
                    },
                }
            ]

            execution_info = {
                "input_type": "query",
                "input_value": query,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
            }

            return self._format_output(results, execution_info)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Shodan count output: {e}")
            raise

    def _execute_scan(self, targets: str, timeout: int) -> Dict[str, Any]:
        """Execute scan (requires API credits)"""

        command = [self.tool_path, "scan", "submit"] + targets.split(",")
        result = self._run_command(command, timeout=timeout)

        # Parse scan submission result
        lines = self._parse_line_output(result["stdout"])

        results = []
        for line in lines:
            if "Scan ID:" in line:
                scan_id = line.split("Scan ID:")[1].strip()
                results.append(
                    {
                        "type": "scan_id",
                        "value": scan_id,
                        "source": "shodan",
                        "confidence": 1.0,
                        "properties": {"targets": targets, "status": "submitted"},
                    }
                )

        execution_info = {
            "input_type": "targets",
            "input_value": targets,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }

        return self._format_output(results, execution_info)

    def get_account_info(self) -> Dict[str, Any]:
        """Get Shodan account information"""
        try:
            if not self.api_key:
                return {"error": "No API key configured"}

            self._setup_api_key()
            result = self._run_command([self.tool_path, "info"], timeout=30)

            # Parse account info
            info = {}
            for line in result["stdout"].split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip().lower().replace(" ", "_")] = value.strip()

            return info

        except Exception as e:
            logger.error(f"Failed to get Shodan account info: {e}")
            return {"error": str(e)}

    def validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        import ipaddress

        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def build_search_query(
        self,
        product: str = None,
        port: int = None,
        country: str = None,
        city: str = None,
        org: str = None,
        hostname: str = None,
        **kwargs,
    ) -> str:
        """Build Shodan search query"""

        query_parts = []

        if product:
            query_parts.append(f'product:"{product}"')

        if port:
            query_parts.append(f"port:{port}")

        if country:
            query_parts.append(f'country:"{country}"')

        if city:
            query_parts.append(f'city:"{city}"')

        if org:
            query_parts.append(f'org:"{org}"')

        if hostname:
            query_parts.append(f'hostname:"{hostname}"')

        # Add any additional filters
        for key, value in kwargs.items():
            if value:
                query_parts.append(f'{key}:"{value}"')

        return " ".join(query_parts)

    def test_tool(self) -> Dict[str, Any]:
        """Test Shodan CLI"""
        try:
            # Test basic functionality
            self._run_command([self.tool_path, "--help"], timeout=10)

            # Test API key if available
            api_test = None
            if self.api_key:
                try:
                    api_test = self.get_account_info()
                except Exception as e:
                    api_test = {"error": str(e)}

            return {
                "tool": self.tool_name,
                "available": True,
                "version": self.get_version(),
                "test_passed": True,
                "message": f"Tool {self.tool_name} is working correctly",
                "api_key_configured": bool(self.api_key),
                "api_test": api_test,
            }
        except Exception as e:
            return {
                "tool": self.tool_name,
                "available": False,
                "version": None,
                "test_passed": False,
                "message": f"Tool test failed: {str(e)}",
            }
