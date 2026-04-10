"""Nmap wrapper for network scanning"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class NmapWrapper(BaseWrapper):
    """Wrapper for Nmap network scanner"""

    def get_tool_name(self) -> str:
        return "nmap"

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "hostname", "cidr", "ip_range", "domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["port", "service", "os", "vulnerability", "script_result"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute nmap scan"""

        # Validate input
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Get configuration options
        scan_type = kwargs.get("scan_type", "tcp_connect")  # tcp_connect, tcp_syn, udp, ping
        ports = kwargs.get("ports", "top-1000")  # port specification
        timing = kwargs.get("timing", 3)  # 0-5 timing template
        scripts = kwargs.get("scripts", None)  # NSE scripts
        os_detection = kwargs.get("os_detection", False)
        service_detection = kwargs.get("service_detection", True)
        aggressive = kwargs.get("aggressive", False)
        timeout = kwargs.get("timeout", 300)

        try:
            # Create temp directory for XML output
            temp_dir = self._create_temp_dir()
            xml_output = f"{temp_dir}/nmap_output.xml"

            # Build command
            command = self._build_nmap_command(
                input_value,
                scan_type=scan_type,
                ports=ports,
                timing=timing,
                scripts=scripts,
                os_detection=os_detection,
                service_detection=service_detection,
                aggressive=aggressive,
                xml_output=xml_output,
            )

            # Execute command
            result = self._run_command(command, timeout=timeout)

            # Parse XML output
            results = self._parse_nmap_xml(xml_output)

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
            logger.error(f"Nmap execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _build_nmap_command(
        self,
        target: str,
        scan_type: str = "tcp_connect",
        ports: str = "top-1000",
        timing: int = 3,
        scripts: Optional[str] = None,
        os_detection: bool = False,
        service_detection: bool = True,
        aggressive: bool = False,
        xml_output: str = None,
    ) -> List[str]:
        """Build nmap command with specified options"""

        command = [self.tool_path]

        # Scan type
        if scan_type == "tcp_syn":
            command.append("-sS")
        elif scan_type == "tcp_connect":
            command.append("-sT")
        elif scan_type == "udp":
            command.append("-sU")
        elif scan_type == "ping":
            command.append("-sn")
        elif scan_type == "tcp_ack":
            command.append("-sA")
        elif scan_type == "tcp_window":
            command.append("-sW")

        # Port specification
        if ports and scan_type != "ping":
            normalized_ports = str(ports).strip().lower()
            if normalized_ports in {"top-1000", "top1000"}:
                command.extend(["--top-ports", "1000"])
            elif normalized_ports in {"top-100", "top100"}:
                command.extend(["--top-ports", "100"])
            elif normalized_ports == "all":
                command.extend(["-p", "1-65535"])
            else:
                command.extend(["-p", ports])

        # Timing template
        command.append(f"-T{timing}")

        # Service detection
        if service_detection and scan_type not in ["ping"]:
            command.append("-sV")

        # OS detection
        if os_detection:
            command.append("-O")

        # Aggressive scan
        if aggressive:
            command.append("-A")

        # NSE scripts
        if scripts:
            command.extend(["--script", scripts])

        # Output format
        if xml_output:
            command.extend(["-oX", xml_output])

        # Disable ping (assume host is up)
        command.append("-Pn")

        # Target
        command.append(target)

        return command

    def _parse_nmap_xml(self, xml_file: str) -> List[Dict[str, Any]]:
        """Parse Nmap XML output"""

        results = []

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Parse each host
            for host in root.findall("host"):
                host_results = self._parse_host(host)
                results.extend(host_results)

        except ET.ParseError as e:
            logger.error(f"Failed to parse Nmap XML: {e}")
        except FileNotFoundError:
            logger.error(f"Nmap XML output file not found: {xml_file}")

        return results

    def _parse_host(self, host_elem) -> List[Dict[str, Any]]:
        """Parse individual host from XML"""

        results = []

        # Get host address
        address_elem = host_elem.find("address")
        if address_elem is None:
            return results

        host_ip = address_elem.get("addr")

        # Get hostnames
        hostnames = []
        hostnames_elem = host_elem.find("hostnames")
        if hostnames_elem is not None:
            for hostname in hostnames_elem.findall("hostname"):
                hostnames.append(hostname.get("name"))

        # Get host status
        status_elem = host_elem.find("status")
        host_state = status_elem.get("state") if status_elem is not None else "unknown"

        # Parse ports
        ports_elem = host_elem.find("ports")
        if ports_elem is not None:
            for port in ports_elem.findall("port"):
                port_results = self._parse_port(port, host_ip, hostnames)
                results.extend(port_results)

        # Parse OS detection
        os_elem = host_elem.find("os")
        if os_elem is not None:
            os_results = self._parse_os(os_elem, host_ip)
            results.extend(os_results)

        # Parse host scripts
        hostscript_elem = host_elem.find("hostscript")
        if hostscript_elem is not None:
            script_results = self._parse_scripts(hostscript_elem, host_ip)
            results.extend(script_results)

        # Add basic host info if no ports found
        if not results and host_state == "up":
            results.append(
                {
                    "type": "host",
                    "value": host_ip,
                    "source": "nmap",
                    "confidence": 0.9,
                    "properties": {"state": host_state, "hostnames": hostnames},
                }
            )

        return results

    def _parse_port(self, port_elem, host_ip: str, hostnames: List[str]) -> List[Dict[str, Any]]:
        """Parse port information"""

        results = []

        port_id = port_elem.get("portid")
        protocol = port_elem.get("protocol")

        # Get port state
        state_elem = port_elem.find("state")
        if state_elem is None:
            return results

        port_state = state_elem.get("state")

        if port_state in ["open", "open|filtered"]:
            # Basic port info
            port_result = {
                "type": "port",
                "value": f"{host_ip}:{port_id}/{protocol}",
                "source": "nmap",
                "confidence": 0.9,
                "properties": {
                    "ip": host_ip,
                    "port": int(port_id),
                    "protocol": protocol,
                    "state": port_state,
                    "hostnames": hostnames,
                },
            }

            # Get service information
            service_elem = port_elem.find("service")
            if service_elem is not None:
                service_name = service_elem.get("name")
                service_product = service_elem.get("product")
                service_version = service_elem.get("version")
                service_extrainfo = service_elem.get("extrainfo")

                port_result["properties"].update(
                    {
                        "service_name": service_name,
                        "service_product": service_product,
                        "service_version": service_version,
                        "service_extrainfo": service_extrainfo,
                    }
                )

                # Create separate service result
                if service_name:
                    service_result = {
                        "type": "service",
                        "value": f"{service_name}://{host_ip}:{port_id}",
                        "source": "nmap",
                        "confidence": 0.8,
                        "properties": {
                            "ip": host_ip,
                            "port": int(port_id),
                            "protocol": protocol,
                            "service_name": service_name,
                            "product": service_product,
                            "version": service_version,
                            "extrainfo": service_extrainfo,
                            "hostnames": hostnames,
                        },
                    }
                    results.append(service_result)

            results.append(port_result)

            # Parse port scripts
            script_elem = port_elem.find("script")
            if script_elem is not None:
                script_results = self._parse_scripts(script_elem, host_ip, port_id)
                results.extend(script_results)

        return results

    def _parse_os(self, os_elem, host_ip: str) -> List[Dict[str, Any]]:
        """Parse OS detection results"""

        results = []

        # Parse OS matches
        for osmatch in os_elem.findall("osmatch"):
            name = osmatch.get("name")
            accuracy = osmatch.get("accuracy")

            if name and accuracy:
                results.append(
                    {
                        "type": "os",
                        "value": name,
                        "source": "nmap",
                        "confidence": float(accuracy) / 100.0,
                        "properties": {
                            "ip": host_ip,
                            "accuracy": accuracy,
                            "line": osmatch.get("line"),
                        },
                    }
                )

        return results

    def _parse_scripts(self, script_elem, host_ip: str, port_id: str = None) -> List[Dict[str, Any]]:
        """Parse NSE script results"""

        results = []

        # Handle both single script and script container
        scripts = script_elem.findall("script") if script_elem.tag != "script" else [script_elem]

        for script in scripts:
            script_id = script.get("id")
            script_output = script.get("output")

            if script_id and script_output:
                result = {
                    "type": "script_result",
                    "value": f"{script_id}: {script_output[:100]}...",  # Truncate for display
                    "source": "nmap",
                    "confidence": 0.7,
                    "properties": {
                        "ip": host_ip,
                        "script_id": script_id,
                        "output": script_output,
                    },
                }

                if port_id:
                    result["properties"]["port"] = port_id

                # Check for vulnerabilities
                if "vuln" in script_id.lower() or "cve" in script_output.lower():
                    result["type"] = "vulnerability"
                    result["confidence"] = 0.8

                results.append(result)

        return results

    def quick_scan(self, target: str, **kwargs) -> Dict[str, Any]:
        """Perform a quick TCP connect scan"""
        input_data = {"type": self._detect_input_type(target), "value": target}

        return self.execute(
            input_data,
            scan_type="tcp_connect",
            ports="top-100",
            timing=4,
            service_detection=True,
            **kwargs,
        )

    def stealth_scan(self, target: str, **kwargs) -> Dict[str, Any]:
        """Perform a stealth SYN scan"""
        input_data = {"type": self._detect_input_type(target), "value": target}

        return self.execute(
            input_data,
            scan_type="tcp_syn",
            ports="top-1000",
            timing=2,
            service_detection=True,
            **kwargs,
        )

    def vulnerability_scan(self, target: str, **kwargs) -> Dict[str, Any]:
        """Perform vulnerability scan with NSE scripts"""
        input_data = {"type": self._detect_input_type(target), "value": target}

        return self.execute(
            input_data,
            scan_type="tcp_connect",
            ports="top-1000",
            timing=3,
            service_detection=True,
            scripts="vuln",
            **kwargs,
        )

    def _detect_input_type(self, target: str) -> str:
        """Detect input type from target string"""
        import ipaddress
        import re

        # Check if it's an IP address
        try:
            ipaddress.ip_address(target)
            return "ip"
        except ValueError:
            pass

        # Check if it's a CIDR
        try:
            ipaddress.ip_network(target, strict=False)
            return "cidr"
        except ValueError:
            pass

        # Check if it's an IP range
        if "-" in target and re.match(r"^\d+\.\d+\.\d+\.\d+-\d+$", target):
            return "ip_range"

        # Default to hostname
        return "hostname"

    def get_common_ports(self) -> Dict[str, List[int]]:
        """Get common ports by service type"""
        return {
            "web": [80, 443, 8080, 8443, 8000, 8888],
            "mail": [25, 110, 143, 993, 995, 587],
            "ftp": [21, 22],
            "database": [3306, 5432, 1433, 1521, 27017],
            "remote": [22, 23, 3389, 5900],
            "dns": [53],
            "dhcp": [67, 68],
            "snmp": [161, 162],
            "ldap": [389, 636],
        }

    def test_tool(self) -> Dict[str, Any]:
        """Test nmap with localhost scan"""
        try:
            # Test with localhost ping scan
            test_input = {"type": "ip", "value": "127.0.0.1"}

            result = self.execute(test_input, scan_type="ping", timeout=30)

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
