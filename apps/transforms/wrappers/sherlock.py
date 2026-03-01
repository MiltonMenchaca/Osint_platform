"""Sherlock wrapper for username enumeration across sites"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class SherlockWrapper(BaseWrapper):
    """Wrapper for Sherlock username enumeration tool"""

    def get_tool_name(self) -> str:
        return "sherlock"

    def get_supported_input_types(self) -> List[str]:
        return ["username", "user", "social_media", "person", "other", "any"]

    def get_supported_output_types(self) -> List[str]:
        return ["social_media", "url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)

        input_type = input_data["type"]
        username = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 90))
        sites = kwargs.get("sites")
        proxy = kwargs.get("proxy")
        tor = bool(kwargs.get("tor", False))
        unique_tor = bool(kwargs.get("unique_tor", False))

        command = [self.tool_path, "--print-found", "--no-color"]

        if timeout:
            command.extend(["--timeout", str(timeout)])

        if proxy is not None and str(proxy).strip() != "":
            command.extend(["--proxy", str(proxy).strip()])

        if unique_tor:
            command.append("--unique-tor")
        elif tor:
            command.append("--tor")

        if isinstance(sites, list) and sites:
            for site in sites:
                site = str(site).strip()
                if site:
                    command.extend(["--site", site])

        command.append(username)

        try:
            result = self._run_command(command, timeout=max(timeout, 60) + 30)
            found = self._parse_found_results(result["stdout"], username=username)

            results: List[Dict[str, Any]] = []
            seen = set()
            for item in found:
                url = item.get("url")
                if not url:
                    continue
                key = url.lower()
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "type": "social_media",
                        "value": url,
                        "source": "sherlock",
                        "confidence": 0.6,
                        "properties": {
                            "username": username,
                            "platform": item.get("platform"),
                        },
                    }
                )

            execution_info = {
                "input_type": input_type,
                "input_value": username,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "profiles_found": len(results),
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Sherlock execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _parse_found_results(self, output: str, username: str) -> List[Dict[str, Optional[str]]]:
        results: List[Dict[str, Optional[str]]] = []
        for raw_line in (output or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "http://" not in line and "https://" not in line:
                continue

            platform, url = self._extract_platform_url(line)
            if not url:
                continue

            results.append({"platform": platform, "url": url, "username": username})
        return results

    def _extract_platform_url(self, line: str) -> (Optional[str], Optional[str]):
        cleaned = line.replace("[+]", "").replace("[*]", "").strip()

        if ": " in cleaned:
            left, right = cleaned.split(": ", 1)
            return left.strip() or None, right.strip() or None

        parts = cleaned.split()
        for part in parts:
            if part.startswith("http://") or part.startswith("https://"):
                return None, part.strip()

        return None, None
