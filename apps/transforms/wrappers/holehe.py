"""Holehe wrapper for email account enumeration"""

import json
import logging
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class HoleheWrapper(BaseWrapper):
    """Wrapper for Holehe tool - Email account enumeration"""

    def get_tool_name(self) -> str:
        return "holehe"

    def get_supported_input_types(self) -> List[str]:
        return ["email"]

    def get_supported_output_types(self) -> List[str]:
        return ["account", "profile", "social_media"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute holehe to find accounts associated with an email"""

        # Validate input
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Get configuration options
        timeout = kwargs.get("timeout", 180)  # Holehe can take some time
        output_format = kwargs.get("format", "json")
        only_used = kwargs.get("only_used", True)  # Only show accounts that exist

        # Build command
        command = [self.tool_path]

        # Add output format
        if output_format == "json":
            command.extend(["--output", "json"])

        # Only show used accounts
        if only_used:
            command.append("--only-used")

        # Add email
        command.append(input_value)

        try:
            # Execute command
            result = self._run_command(command, timeout=timeout)

            # Parse output based on format
            if output_format == "json":
                accounts = self._parse_holehe_json_output(result["stdout"])
            else:
                accounts = self._parse_holehe_text_output(result["stdout"])

            # Format results
            results = []
            for account in accounts:
                if account.get("exists", False):  # Only include existing accounts
                    results.append(
                        {
                            "type": "account",
                            "value": f"{account['name']}:{input_value}",
                            "source": "holehe",
                            "confidence": self._calculate_confidence(account),
                            "properties": {
                                "platform": account["name"],
                                "email": input_value,
                                "url": account.get("url", ""),
                                "exists": account.get("exists", False),
                                "rate_limited": account.get("rateLimit", False),
                                "error": account.get("error", ""),
                                "response_time": account.get("responseTime", 0),
                            },
                        }
                    )

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "total_platforms_checked": len(accounts),
                "accounts_found": len(results),
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Holehe execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _parse_holehe_json_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse JSON output from Holehe"""
        try:
            # Holehe outputs JSON array
            data = json.loads(output)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Holehe JSON output: {e}")
            return []

    def _parse_holehe_text_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse text output from Holehe"""
        accounts = []
        lines = output.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("["):
                continue

            # Parse format: "[+] Platform: email found"
            if "[+]" in line:
                parts = line.split(": ")
                if len(parts) >= 2:
                    platform = parts[0].replace("[+]", "").strip()
                    accounts.append(
                        {
                            "name": platform,
                            "exists": True,
                            "url": "",
                            "rateLimit": False,
                        }
                    )

        return accounts

    def _calculate_confidence(self, account: Dict[str, Any]) -> float:
        """Calculate confidence score for an account"""
        confidence = 0.5  # Base confidence

        # Increase confidence if account exists
        if account.get("exists", False):
            confidence += 0.3

        # Decrease confidence if rate limited
        if account.get("rateLimit", False):
            confidence -= 0.2

        # Decrease confidence if there was an error
        if account.get("error"):
            confidence -= 0.1

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re

        # Basic email validation regex
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        return bool(email_pattern.match(email))

    def execute_with_validation(
        self, input_data: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """Execute with additional email validation"""

        input_value = input_data.get("value", "")

        # Validate email format
        if not self.validate_email(input_value):
            raise ValueError(f"Invalid email format: {input_value}")

        return self.execute(input_data, **kwargs)

    def get_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics from results"""
        if not results:
            return {}

        total_accounts = len(results)
        platforms = set()
        rate_limited_count = 0
        error_count = 0

        for result in results:
            properties = result.get("properties", {})
            platform = properties.get("platform", "")
            if platform:
                platforms.add(platform)

            if properties.get("rate_limited", False):
                rate_limited_count += 1

            if properties.get("error"):
                error_count += 1

        return {
            "total_accounts_found": total_accounts,
            "unique_platforms": len(platforms),
            "platforms": list(platforms),
            "rate_limited_count": rate_limited_count,
            "error_count": error_count,
            "success_rate": (total_accounts - error_count) / total_accounts
            if total_accounts > 0
            else 0,
        }

    def filter_results(
        self,
        results: List[Dict[str, Any]],
        min_confidence: float = 0.0,
        exclude_rate_limited: bool = True,
        exclude_errors: bool = True,
        platforms: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter results based on criteria"""

        filtered = []

        for result in results:
            # Filter by confidence
            if result.get("confidence", 0) < min_confidence:
                continue

            properties = result.get("properties", {})

            # Filter rate limited
            if exclude_rate_limited and properties.get("rate_limited", False):
                continue

            # Filter errors
            if exclude_errors and properties.get("error"):
                continue

            # Filter by platforms
            if platforms:
                platform = properties.get("platform", "")
                if platform not in platforms:
                    continue

            filtered.append(result)

        return filtered

    def get_help(self) -> str:
        """Get tool help information"""
        try:
            result = self._run_command([self.tool_path, "--help"], timeout=10)
            return result.get("stdout", "") + result.get("stderr", "")
        except Exception:
            return "Help information not available"
