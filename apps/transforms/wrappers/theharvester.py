"""TheHarvester wrapper for email/host collection"""

import json
import logging
import os
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class TheHarvesterWrapper(BaseWrapper):
    """Wrapper for theHarvester"""

    def get_tool_name(self) -> str:
        return "theHarvester"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["email", "domain", "ip"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        timeout = int(kwargs.get("timeout", 180))
        source = str(kwargs.get("source", "all") or "all").strip()
        limit = kwargs.get("limit")

        command = [self.tool_path, "-d", input_value, "-b", source]

        if limit is not None and str(limit).strip() != "":
            command.extend(["-l", str(limit).strip()])

        temp_dir = self._create_temp_dir()
        output_base = os.path.join(temp_dir, "theharvester_output")
        command.extend(["-f", output_base])

        try:
            result = self._run_command(command, timeout=timeout)

            parsed = self._parse_output_files(output_base=output_base, fallback_text=result["stdout"])

            results: List[Dict[str, Any]] = []
            seen = set()

            for email in parsed.get("emails", []):
                email = str(email).strip()
                if not email:
                    continue
                key = ("email", email.lower())
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "type": "email",
                        "value": email,
                        "source": "theharvester",
                        "confidence": 0.7,
                        "properties": {"domain": input_value, "source_engine": source},
                    }
                )

            for host in parsed.get("hosts", []):
                host = str(host).strip().strip(".")
                if not host:
                    continue
                key = ("domain", host.lower())
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "type": "domain",
                        "value": host,
                        "source": "theharvester",
                        "confidence": 0.65,
                        "properties": {"domain": input_value, "source_engine": source},
                    }
                )

            for ip in parsed.get("ips", []):
                ip = str(ip).strip()
                if not ip:
                    continue
                key = ("ip", ip)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "type": "ip",
                        "value": ip,
                        "source": "theharvester",
                        "confidence": 0.65,
                        "properties": {"domain": input_value, "source_engine": source},
                    }
                )

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "engine": source,
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"TheHarvester execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _parse_output_files(self, output_base: str, fallback_text: str) -> Dict[str, List[str]]:
        json_path = f"{output_base}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "emails": list(data.get("emails") or []),
                    "hosts": list(data.get("hosts") or []),
                    "ips": list(data.get("ips") or []),
                }
            except Exception:
                pass

        return self._parse_text_fallback(fallback_text)

    def _parse_text_fallback(self, output: str) -> Dict[str, List[str]]:
        import re

        emails = set(
            re.findall(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                output or "",
            )
        )

        ips = set(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", output or ""))

        domains = set(
            re.findall(
                r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
                output or "",
            )
        )

        return {"emails": sorted(emails), "hosts": sorted(domains), "ips": sorted(ips)}
