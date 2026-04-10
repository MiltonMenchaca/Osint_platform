import logging
import re
import sys
import shutil
import os
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform.startswith("win")


class PingWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "ping"

    def _find_tool_path(self) -> str:
        """Find the tool in system PATH with fallbacks"""
        path = shutil.which(self.tool_name)
        if path:
            return path

        # Fallback for common locations
        common_paths = ["/bin/ping", "/usr/bin/ping", "/usr/sbin/ping", "/sbin/ping", "/usr/local/bin/ping"]

        if IS_WINDOWS:
            common_paths.extend(["C:\\Windows\\System32\\ping.exe", "C:\\Windows\\SysWOW64\\ping.exe"])

        for p in common_paths:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

        return None

    def get_version(self) -> str:
        """Get tool version"""
        try:
            # ping uses -V for version
            result = self._run_command([self.tool_path, "-V"], timeout=5)
            return result.get("stdout", "").strip()
        except Exception as e:
            logger.warning(f"Could not get version for {self.tool_name}: {e}")
            return None

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["ip", "domain", "hostname", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 30))
        count = int(kwargs.get("count", 1))
        wait = int(kwargs.get("wait", 2))

        if IS_WINDOWS:
            # Windows: -n count, -w wait_ms
            # ping expects wait in milliseconds
            wait_ms = wait * 1000
            command = [self.tool_path, "-n", str(count), "-w", str(wait_ms), input_value]
        else:
            # Linux: -c count, -W wait_s
            command = [self.tool_path, "-c", str(count), "-W", str(wait), input_value]

        result = self._run_command(command, timeout=timeout)

        ips = []
        for raw_line in (result.get("stdout") or "").splitlines():
            line = raw_line.strip()
            # Windows: Reply from 1.2.3.4: bytes=32 time=10ms TTL=128
            # Linux: 64 bytes from 1.2.3.4: icmp_seq=1 ttl=128 time=10.0 ms
            # Linux (with hostname): 64 bytes from dns.google (8.8.8.8): icmp_seq=1 ttl=118 time=13.7 ms

            # Robust regex for both: look for 'from' followed by IP or hostname(IP)
            # Match 1: "from 1.2.3.4"
            # Match 2: "from dns.google (8.8.8.8)" -> extract 8.8.8.8

            # Check for IP in parenthesis first (common in Linux with hostname)
            match_parens = re.search(r"(?:from|desde)\s+.*?\((?P<ip>(?:\d{1,3}\.){3}\d{1,3})\)", line, re.IGNORECASE)
            if match_parens:
                ips.append(match_parens.group("ip"))
                continue

            # Check for direct IP after 'from' or 'desde' (Spanish Windows)
            match_direct = re.search(r"(?:from|desde)\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})", line, re.IGNORECASE)
            if match_direct:
                ips.append(match_direct.group("ip"))

        results: List[Dict[str, Any]] = []
        for ip in sorted(set(ips)):
            results.append({"type": "ip", "value": ip, "source": "ping", "confidence": 0.6})

        if not results:
            results.append(
                {
                    "type": "other",
                    "value": f"No response from {input_value}",
                    "source": "ping",
                    "confidence": 0.4,
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


class TracerouteWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        if IS_WINDOWS:
            return "tracert"
        return "traceroute"

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["ip"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 120))
        max_hops = int(kwargs.get("max_hops", 30))

        if IS_WINDOWS:
            # Windows: tracert -d -h max_hops input_value
            # -d: Do not resolve addresses to hostnames
            command = [self.tool_path, "-d", "-h", str(max_hops), input_value]
        else:
            # Linux: traceroute -I -n -m max_hops -q 1 -w 2 input_value
            # -I: Use ICMP ECHO instead of UDP. Requires root.
            # -n: Do not resolve addresses to hostnames
            # -q 1: 1 query per hop (faster)
            # -w 2: 2 seconds wait
            command = [self.tool_path, "-I", "-n", "-m", str(max_hops), "-q", "1", "-w", "2", input_value]

        result = self._run_command(command, timeout=timeout)

        hops: List[Dict[str, Any]] = []

        # Windows:  1    <1 ms    <1 ms    <1 ms  192.168.1.1
        # Linux:    1  192.168.1.1  0.123 ms  0.123 ms  0.123 ms
        # Linux (ICMP/-q 1): 1  192.168.1.1  0.123 ms

        if IS_WINDOWS:
            hop_pattern = re.compile(r"^\s*(?P<hop>\d+)\s+.*\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})")
        else:
            # Match hop number, then IP anywhere on the line
            hop_pattern = re.compile(r"^\s*(?P<hop>\d+)\s+(?:.*?\s+)?(?P<ip>(?:\d{1,3}\.){3}\d{1,3})")

        for raw_line in (result.get("stdout") or "").splitlines():
            line = raw_line.strip()
            match = hop_pattern.search(line)
            if not match:
                continue
            hops.append(
                {
                    "type": "ip",
                    "value": match.group("ip"),
                    "source": "traceroute",
                    "confidence": 0.6,
                    "properties": {"hop": int(match.group("hop"))},
                }
            )

        seen: set[str] = set()
        results: List[Dict[str, Any]] = []
        for item in hops:
            if item["value"] in seen:
                continue
            seen.add(item["value"])
            results.append(item)

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(results, execution_info)


class MasscanWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "masscan"

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "cidr", "ip_range", "domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["ip"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))
        ports = str(kwargs.get("ports", "80,443"))
        rate = int(kwargs.get("rate", 1000))

        command = [self.tool_path, input_value, "-p", ports, "--rate", str(rate)]
        result = self._run_command(command, timeout=timeout)

        found = []
        pattern = re.compile(
            r"Discovered open port\s+(?P<port>\d+)\/(?P<proto>\w+)\s+on\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})"
        )
        for raw_line in (result.get("stdout") or "").splitlines():
            line = raw_line.strip()
            match = pattern.search(line)
            if not match:
                continue
            found.append(
                {
                    "type": "ip",
                    "value": match.group("ip"),
                    "source": "masscan",
                    "confidence": 0.7,
                    "properties": {
                        "port": int(match.group("port")),
                        "protocol": match.group("proto").lower(),
                    },
                }
            )

        results = found
        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
            "ports": ports,
            "rate": rate,
        }
        return self._format_output(results, execution_info)


class ZmapWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "zmap"

    def get_supported_input_types(self) -> List[str]:
        return ["cidr", "ip_range", "ip"]

    def get_supported_output_types(self) -> List[str]:
        return ["ip"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))
        port = int(kwargs.get("port", 80))

        # Zmap usage: zmap -p 80 <target>
        command = [self.tool_path, "-p", str(port), input_value]
        result = self._run_command(command, timeout=timeout)

        found = []
        # zmap outputs IPs to stdout by default
        for raw_line in (result.get("stdout") or "").splitlines():
            ip = raw_line.strip()
            # Simple IP validation regex
            if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip):
                found.append(
                    {"type": "ip", "value": ip, "source": "zmap", "confidence": 0.7, "properties": {"port": port}}
                )

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
            "port": port,
        }
        return self._format_output(found, execution_info)
