"""Amass wrapper for subdomain enumeration"""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class AmassWrapper(BaseWrapper):
    """Wrapper for OWASP Amass subdomain enumeration tool"""

    def get_tool_name(self) -> str:
        return "amass"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["subdomain", "ip", "asn", "cidr"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute amass enumeration"""

        # Validate input
        self._validate_input(input_data)

        input_type = input_data["type"]
        input_value = input_data["value"]

        # Get configuration options
        mode = kwargs.get("mode", "enum")  # enum, intel, track, db
        passive = kwargs.get("passive", False)
        active = kwargs.get("active", False)
        brute = kwargs.get("brute", False)
        wordlist = kwargs.get("wordlist", None)
        resolvers = kwargs.get("resolvers", None)
        config_file = kwargs.get("config_file", None)
        timeout = kwargs.get("timeout", 600)  # 10 minutes default
        max_dns_queries = kwargs.get("max_dns_queries", 20000)

        try:
            # Create temp directory for output
            temp_dir = self._create_temp_dir()
            json_output = f"{temp_dir}/amass_output.json"

            # Build command based on mode
            if mode == "enum":
                command = self._build_enum_command(
                    input_value,
                    passive=passive,
                    active=active,
                    brute=brute,
                    wordlist=wordlist,
                    resolvers=resolvers,
                    config_file=config_file,
                    json_output=json_output,
                    max_dns_queries=max_dns_queries,
                )
            elif mode == "intel":
                command = self._build_intel_command(input_value, config_file=config_file, json_output=json_output)
            else:
                raise ValueError(f"Unsupported Amass mode: {mode}")

            # Execute command
            result = self._run_command(command, timeout=timeout)

            # Parse JSON output
            results = self._parse_amass_json(json_output)

            execution_info = {
                "input_type": input_type,
                "input_value": input_value,
                "execution_time": result["execution_time"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "command": result["command"],
                "mode": mode,
            }

            return self._format_output(results, execution_info)

        except Exception as e:
            logger.error(f"Amass execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_dir()

    def _build_enum_command(
        self,
        domain: str,
        passive: bool = False,
        active: bool = False,
        brute: bool = False,
        wordlist: Optional[str] = None,
        resolvers: Optional[str] = None,
        config_file: Optional[str] = None,
        json_output: str = None,
        max_dns_queries: int = 20000,
    ) -> List[str]:
        """Build amass enum command"""

        command = [self.tool_path, "enum"]

        # Domain
        command.extend(["-d", domain])

        # Enumeration options
        if passive:
            command.append("-passive")

        if active:
            command.append("-active")

        if brute:
            command.append("-brute")
            if wordlist:
                command.extend(["-w", wordlist])

        # DNS settings
        if resolvers:
            command.extend(["-rf", resolvers])

        command.extend(["-max-dns-queries", str(max_dns_queries)])

        # Configuration
        if config_file:
            command.extend(["-config", config_file])

        # Output format
        if json_output:
            command.extend(["-json", json_output])

        # Disable color output
        command.append("-nocolor")

        return command

    def _build_intel_command(
        self, target: str, config_file: Optional[str] = None, json_output: str = None
    ) -> List[str]:
        """Build amass intel command"""

        command = [self.tool_path, "intel"]

        # Target (can be domain, organization, or ASN)
        if target.startswith("AS"):
            command.extend(["-asn", target])
        elif "." in target:
            command.extend(["-d", target])
        else:
            command.extend(["-org", target])

        # Configuration
        if config_file:
            command.extend(["-config", config_file])

        # Output format
        if json_output:
            command.extend(["-json", json_output])

        # Disable color output
        command.append("-nocolor")

        return command

    def _parse_amass_json(self, json_file: str) -> List[Dict[str, Any]]:
        """Parse Amass JSON output"""

        results = []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            parsed_results = self._parse_amass_record(data)
                            results.extend(parsed_results)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON line: {e}")
                            continue

        except FileNotFoundError:
            logger.warning(f"Amass output file not found: {json_file}")
        except Exception as e:
            logger.error(f"Error parsing Amass output: {e}")

        return results

    def _parse_amass_record(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse individual Amass record"""

        results = []

        # Get basic information
        name = record.get("name", "")
        domain = record.get("domain", "")
        addresses = record.get("addresses", [])

        # Create subdomain result
        if name:
            subdomain_result = {
                "type": "subdomain",
                "value": name,
                "source": "amass",
                "confidence": 0.9,
                "properties": {
                    "domain": domain,
                    "sources": record.get("sources", []),
                    "tag": record.get("tag", ""),
                    "type": record.get("type", ""),
                },
            }

            # Add network information if available
            netblocks = record.get("netblocks", [])
            if netblocks:
                subdomain_result["properties"]["netblocks"] = netblocks

            results.append(subdomain_result)

        # Create IP address results
        for addr_info in addresses:
            if isinstance(addr_info, dict):
                ip = addr_info.get("ip", "")
                asn = addr_info.get("asn", 0)
                cidr = addr_info.get("cidr", "")
                desc = addr_info.get("desc", "")
            else:
                # Simple IP string
                ip = str(addr_info)
                asn = 0
                cidr = ""
                desc = ""

            if ip:
                ip_result = {
                    "type": "ip",
                    "value": ip,
                    "source": "amass",
                    "confidence": 0.9,
                    "properties": {"hostname": name, "domain": domain},
                }

                if asn:
                    ip_result["properties"]["asn"] = asn
                if cidr:
                    ip_result["properties"]["cidr"] = cidr
                if desc:
                    ip_result["properties"]["description"] = desc

                results.append(ip_result)

                # Create separate ASN result if available
                if asn:
                    asn_result = {
                        "type": "asn",
                        "value": f"AS{asn}",
                        "source": "amass",
                        "confidence": 0.8,
                        "properties": {
                            "asn_number": asn,
                            "description": desc,
                            "ip": ip,
                            "hostname": name,
                        },
                    }
                    results.append(asn_result)

                # Create CIDR result if available
                if cidr:
                    cidr_result = {
                        "type": "cidr",
                        "value": cidr,
                        "source": "amass",
                        "confidence": 0.8,
                        "properties": {
                            "asn": asn,
                            "description": desc,
                            "ip": ip,
                            "hostname": name,
                        },
                    }
                    results.append(cidr_result)

        return results

    def passive_enum(self, domain: str, **kwargs) -> Dict[str, Any]:
        """Perform passive subdomain enumeration"""
        input_data = {"type": "domain", "value": domain}

        return self.execute(input_data, mode="enum", passive=True, **kwargs)

    def active_enum(self, domain: str, **kwargs) -> Dict[str, Any]:
        """Perform active subdomain enumeration"""
        input_data = {"type": "domain", "value": domain}

        return self.execute(input_data, mode="enum", active=True, **kwargs)

    def brute_enum(self, domain: str, wordlist: str = None, **kwargs) -> Dict[str, Any]:
        """Perform brute force subdomain enumeration"""
        input_data = {"type": "domain", "value": domain}

        return self.execute(input_data, mode="enum", brute=True, wordlist=wordlist, **kwargs)

    def intel_enum(self, target: str, **kwargs) -> Dict[str, Any]:
        """Perform intelligence gathering"""
        # Detect target type
        if target.startswith("AS"):
            input_type = "asn"
        elif "." in target:
            input_type = "domain"
        else:
            input_type = "organization"

        input_data = {"type": input_type, "value": target}

        return self.execute(input_data, mode="intel", **kwargs)

    def comprehensive_enum(self, domain: str, **kwargs) -> Dict[str, Any]:
        """Perform comprehensive enumeration (passive + active + brute)"""
        input_data = {"type": "domain", "value": domain}

        return self.execute(input_data, mode="enum", passive=True, active=True, brute=True, **kwargs)

    def get_help(self) -> Dict[str, Any]:
        """Get Amass help information"""
        try:
            result = self._run_command([self.tool_path, "-h"], timeout=10)
            return {"tool": self.tool_name, "help": result["stdout"], "available": True}
        except Exception as e:
            return {
                "tool": self.tool_name,
                "help": f"Failed to get help: {e}",
                "available": False,
            }

    def get_data_sources(self) -> List[str]:
        """Get list of available data sources"""
        return [
            "AlienVault",
            "Baidu",
            "Bing",
            "BufferOver",
            "Censys",
            "CertSpotter",
            "CIRCL",
            "CommonCrawl",
            "Crtsh",
            "DNSDB",
            "DNSDumpster",
            "DNSTable",
            "Dogpile",
            "Entrust",
            "Facebook",
            "FindSubDomains",
            "Google",
            "HackerTarget",
            "IPv4Info",
            "Netcraft",
            "NetworksDB",
            "PassiveTotal",
            "Pastebin",
            "PTRArchive",
            "Riddler",
            "Robtex",
            "SecurityTrails",
            "Shodan",
            "SiteDossier",
            "Spyse",
            "Sublist3r",
            "ThreatCrowd",
            "ThreatMiner",
            "Twitter",
            "Umbrella",
            "URLScan",
            "VirusTotal",
            "WhoisXML",
            "Yahoo",
            "ZoomEye",
        ]

    def create_config_template(self) -> str:
        """Create Amass configuration file template"""
        config_template = """
# Amass Configuration File

# DNS resolvers
[resolvers]
resolvers = [
    "8.8.8.8",
    "8.8.4.4",
    "1.1.1.1",
    "1.0.0.1"
]

# Data source configurations
[data_sources]

# Shodan API
[data_sources.Shodan]
ttl = 4320
api_key = "your_shodan_api_key_here"

# Censys API
[data_sources.Censys]
ttl = 10080
api_id = "your_censys_api_id_here"
secret = "your_censys_secret_here"

# VirusTotal API
[data_sources.VirusTotal]
ttl = 10080
api_key = "your_virustotal_api_key_here"

# PassiveTotal API
[data_sources.PassiveTotal]
ttl = 10080
username = "your_passivetotal_username_here"
api_key = "your_passivetotal_api_key_here"

# SecurityTrails API
[data_sources.SecurityTrails]
ttl = 1440
api_key = "your_securitytrails_api_key_here"

# Spyse API
[data_sources.Spyse]
ttl = 4320
api_key = "your_spyse_api_key_here"

# Facebook API
[data_sources.Facebook]
ttl = 4320
app_id = "your_facebook_app_id_here"
app_secret = "your_facebook_app_secret_here"

# Twitter API
[data_sources.Twitter]
ttl = 4320
api_key = "your_twitter_api_key_here"
secret = "your_twitter_secret_here"
access_token = "your_twitter_access_token_here"
access_secret = "your_twitter_access_secret_here"
"""
        return config_template

    def test_tool(self) -> Dict[str, Any]:
        """Test amass with a simple domain"""
        try:
            # Test with a simple passive enumeration
            test_input = {"type": "domain", "value": "example.com"}

            result = self.execute(test_input, mode="enum", passive=True, timeout=60)

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
