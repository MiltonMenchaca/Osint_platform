"""Assetfinder wrapper for subdomain enumeration"""

import logging
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class AssetfinderWrapper(BaseWrapper):
    """Wrapper for Assetfinder tool"""

    def get_tool_name(self) -> str:
        return "assetfinder"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["subdomain", "hostname"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute assetfinder to find subdomains"""

        # Validate input
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Get configuration options
        use_subs_only = kwargs.get("subs_only", True)
        timeout = kwargs.get("timeout", 120)

        # Build command
        command = [self.tool_path]

        if use_subs_only:
            command.append("--subs-only")

        command.append(input_value)

        try:
            # Execute command
            result = self._run_command(command, timeout=timeout)

            # Parse output
            subdomains = self._parse_line_output(result["stdout"])

            # Format results
            results = []
            for subdomain in subdomains:
                if subdomain and subdomain != input_value:
                    results.append(
                        {
                            "type": "subdomain",
                            "value": subdomain,
                            "source": "assetfinder",
                            "confidence": 0.8,  # Assetfinder is generally reliable
                            "properties": {
                                "parent_domain": input_value,
                                "discovery_method": "passive_dns",
                            },
                        }
                    )

            # Remove duplicates while preserving order
            seen = set()
            unique_results = []
            for result in results:
                if result["value"] not in seen:
                    seen.add(result["value"])
                    unique_results.append(result)

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
            }

            return self._format_output(unique_results, execution_info)

        except Exception as e:
            logger.error(f"Assetfinder execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def get_help(self) -> str:
        """Get tool help information"""
        try:
            result = self._run_command([self.tool_path, "-h"], timeout=10)
            return result.get("stdout", "") + result.get("stderr", "")
        except Exception:
            return "Help information not available"

    def validate_domain(self, domain: str) -> bool:
        """Validate domain format"""
        import re

        # Basic domain validation regex
        domain_pattern = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"  # subdomains
            r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"  # main domain
        )

        return bool(domain_pattern.match(domain))

    def execute_with_validation(
        self, input_data: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """Execute with additional domain validation"""

        input_value = input_data.get("value", "")

        # Validate domain format
        if not self.validate_domain(input_value):
            raise ValueError(f"Invalid domain format: {input_value}")

        # Check if domain is too short or too long
        if len(input_value) < 3:
            raise ValueError("Domain too short")

        if len(input_value) > 253:
            raise ValueError("Domain too long")

        return self.execute(input_data, **kwargs)

    def get_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics from results"""
        if not results:
            return {}

        total_subdomains = len(results)
        unique_tlds = set()
        subdomain_levels = {}

        for result in results:
            subdomain = result.get("value", "")

            # Extract TLD
            parts = subdomain.split(".")
            if len(parts) >= 2:
                tld = parts[-1]
                unique_tlds.add(tld)

            # Count subdomain levels
            level = len(parts) - 2  # Subtract domain and TLD
            if level > 0:
                subdomain_levels[level] = subdomain_levels.get(level, 0) + 1

        return {
            "total_subdomains": total_subdomains,
            "unique_tlds": len(unique_tlds),
            "tlds": list(unique_tlds),
            "subdomain_levels": subdomain_levels,
            "max_subdomain_level": max(subdomain_levels.keys())
            if subdomain_levels
            else 0,
        }

    def filter_results(
        self,
        results: List[Dict[str, Any]],
        min_confidence: float = 0.0,
        exclude_wildcards: bool = True,
        max_subdomain_level: int = None,
    ) -> List[Dict[str, Any]]:
        """Filter results based on criteria"""

        filtered = []

        for result in results:
            # Filter by confidence
            if result.get("confidence", 0) < min_confidence:
                continue

            subdomain = result.get("value", "")

            # Filter wildcards
            if exclude_wildcards and "*" in subdomain:
                continue

            # Filter by subdomain level
            if max_subdomain_level is not None:
                parts = subdomain.split(".")
                level = len(parts) - 2
                if level > max_subdomain_level:
                    continue

            filtered.append(result)

        return filtered

    def export_results(
        self,
        results: List[Dict[str, Any]],
        format_type: str = "txt",
        output_file: str = None,
    ) -> str:
        """Export results to different formats"""

        if format_type == "txt":
            output = "\n".join([result.get("value", "") for result in results])
        elif format_type == "csv":
            import csv
            import io

            output_buffer = io.StringIO()
            writer = csv.writer(output_buffer)
            writer.writerow(["subdomain", "confidence", "source"])

            for result in results:
                writer.writerow(
                    [
                        result.get("value", ""),
                        result.get("confidence", ""),
                        result.get("source", ""),
                    ]
                )

            output = output_buffer.getvalue()
        elif format_type == "json":
            import json

            output = json.dumps(results, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        if output_file:
            with open(output_file, "w") as f:
                f.write(output)
            return f"Results exported to {output_file}"

        return output

    def test_tool(self) -> Dict[str, Any]:
        """Test assetfinder with a known domain"""
        try:
            # Test with a well-known domain
            test_input = {"type": "domain", "value": "example.com"}

            result = self.execute(test_input, timeout=30)

            return {
                "tool": self.tool_name,
                "available": True,
                "version": self.get_version(),
                "test_passed": True,
                "message": f"Tool {self.tool_name} is working correctly",
                "test_results": len(result.get("results", [])),
                "execution_time": result.get("metadata", {}).get("execution_time"),
            }
        except Exception as e:
            return {
                "tool": self.tool_name,
                "available": False,
                "version": None,
                "test_passed": False,
                "message": f"Tool test failed: {str(e)}",
            }
