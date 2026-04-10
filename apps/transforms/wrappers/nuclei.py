"""Nuclei wrapper for vulnerability scanning"""

import json
import logging
import os
import tempfile
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class NucleiWrapper(BaseWrapper):
    """Wrapper for Nuclei vulnerability scanner"""

    def get_tool_name(self) -> str:
        return "nuclei"

    def get_supported_input_types(self) -> List[str]:
        return ["url", "domain", "ip"]

    def get_supported_output_types(self) -> List[str]:
        return ["vulnerability", "finding", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 600))
        templates = kwargs.get("templates", [])  # List of templates or categories
        severity = kwargs.get("severity", "")  # critical,high,medium,low,info

        # Create temp file for output
        fd, output_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        # Nuclei v3 changed -json to -j or -json-export
        # For headless/automation, we want to write to a file.
        # -json-export FILE writes the JSON output to the specified file.
        command = [self.tool_path, "-u", input_value, "-json-export", output_path]

        if templates:
            for t in templates:
                command.extend(["-t", str(t)])

        if severity:
            command.extend(["-severity", severity])

        # Add some default optimizations
        # -rate-limit 150: Limit requests per second
        # -bulk-size 25: Number of hosts to scan in parallel
        # -concurrency 25: Number of templates to run in parallel
        # -disable-update-check: Don't check for updates
        # -ni: Non-interactive mode (good for automation)
        command.extend(["-rate-limit", "150", "-bulk-size", "25", "-concurrency", "25", "-disable-update-check", "-ni"])

        try:
            result = self._run_command(command, timeout=timeout)

            # Parse JSON output (NDJSON format - newline delimited JSON)
            results = []
            if os.path.exists(output_path):
                with open(output_path, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            finding = json.loads(line)
                            # Sometimes finding can be a list if -json-export behavior varies, but usually NDJSON
                            if isinstance(finding, list):
                                for f in finding:
                                    results.append(self._parse_nuclei_finding(f))
                            else:
                                results.append(self._parse_nuclei_finding(finding))
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse nuclei output line: {line}")

            # If no results file but we have stdout, maybe check if it failed silently or just no results
            # Exit code 0 means success (even if no findings)

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "findings_count": len(results),
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Nuclei execution failed: {e}")
            raise
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def _parse_nuclei_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Nuclei finding to internal format"""
        info = finding.get("info", {})

        return {
            "type": "vulnerability",
            "value": info.get("name", "Unknown Vulnerability"),
            "source": "nuclei",
            "confidence": 0.9,  # Nuclei is generally accurate
            "properties": {
                "template_id": finding.get("template-id"),
                "severity": info.get("severity"),
                "description": info.get("description"),
                "matcher_name": finding.get("matcher-name"),
                "extracted_results": finding.get("extracted-results"),
                "host": finding.get("host"),
                "matched_at": finding.get("matched-at"),
                "timestamp": finding.get("timestamp"),
                "tags": info.get("tags", []),
                "reference": info.get("reference", []),
            },
        }
