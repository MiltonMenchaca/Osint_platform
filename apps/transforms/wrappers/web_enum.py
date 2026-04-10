import json
import logging
import re
import shutil
import base64
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class DnsTwistWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "dnstwist"

    def get_supported_input_types(self) -> List[str]:
        return ["domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))

        # Output as JSON
        command = [self.tool_path, "--format", "json", input_value]

        result = self._run_command(command, timeout=timeout)

        domains: List[Dict[str, Any]] = []
        try:
            raw_output = result.get("stdout") or "[]"
            # Some versions might output header text, so find first [
            json_start = raw_output.find("[")
            if json_start != -1:
                # Find the last ] to ensure we only parse the JSON list
                json_end = raw_output.rfind("]") + 1
                if json_end > json_start:
                    data = json.loads(raw_output[json_start:json_end])
                    for item in data:
                        domain = item.get("domain")
                        if domain and domain != input_value:
                            domains.append({
                                "type": "domain",
                                "value": domain,
                                "source": "dnstwist",
                                "confidence": 0.6,
                                "properties": {
                                    "fuzzer": item.get("fuzzer"),
                                    "dns_a": item.get("dns_a"),
                                    "dns_mx": item.get("dns_mx"),
                                    "dns_ns": item.get("dns_ns"),
                                }
                            })
                else:
                    logger.warning(f"Could not find valid JSON end in dnstwist output: {raw_output[:100]}...")
            else:
                 logger.warning(f"Could not find JSON start in dnstwist output: {raw_output[:100]}...")
        except Exception as e:
            logger.error(f"Failed to parse dnstwist output: {e}. Raw output snippet: {raw_output[:200]}")

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(domains, execution_info)


class WhoisWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "whois"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "ip", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 60))
        command = [self.tool_path, input_value]
        result = self._run_command(command, timeout=timeout)
        raw = (result.get("stdout") or "").strip()

        results = []
        if raw:
            results.append(
                {
                    "type": "other",
                    "value": input_value,
                    "source": "whois",
                    "confidence": 0.6,
                    "properties": {"raw": raw[:8000]},
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


class HttpxWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "httpx"

    def _find_tool_path(self) -> Optional[str]:
        # Check for renamed binary first (to avoid conflict with python-httpx)
        path = shutil.which("httpx-pd")
        if path:
            return path

        candidate = super()._find_tool_path() or shutil.which("httpx")
        if not candidate:
            return None

        def looks_like_projectdiscovery(path: str) -> bool:
            try:
                proc = subprocess.run(
                    [path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                return "projectdiscovery" in (proc.stderr or "").lower() or \
                       "httpx" in (proc.stderr or "").lower()
            except Exception:
                return False

        if looks_like_projectdiscovery(candidate):
            return candidate
        return None

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname", "ip", "url"]

    def get_supported_output_types(self) -> List[str]:
        return ["url", "service"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 120))

        command = [
            self.tool_path,
            "-u", input_value,
            "-json",
            "-silent",
            "-tech-detect",
            "-status-code",
            "-title",
            "-ip",
        ]

        result = self._run_command(command, timeout=timeout)

        results: List[Dict[str, Any]] = []
        for line in (result.get("stdout") or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                url = data.get("url")
                if url:
                    props = {
                        "status_code": data.get("status_code"),
                        "title": data.get("title"),
                        "webserver": data.get("webserver"),
                        "tech": data.get("tech"),
                        "host": data.get("host"),
                        "port": data.get("port"),
                    }
                    results.append({
                        "type": "url",
                        "value": url,
                        "source": "httpx",
                        "confidence": 1.0,
                        "properties": props
                    })
            except json.JSONDecodeError:
                pass

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(results, execution_info)


class WaybackUrlsWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "waybackurls"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "hostname"]

    def get_supported_output_types(self) -> List[str]:
        return ["url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))

        command = [self.tool_path, input_value]

        result = self._run_command(command, timeout=timeout)

        urls = []
        for line in (result.get("stdout") or "").splitlines():
            line = line.strip()
            if line:
                urls.append(line)

        unique_urls = sorted(set(urls))
        results: List[Dict[str, Any]] = [
            {"type": "url", "value": url, "source": "waybackurls", "confidence": 0.7}
            for url in unique_urls
        ]

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(results, execution_info)


class GobusterWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "gobuster"

    def get_supported_input_types(self) -> List[str]:
        return ["url", "domain", "hostname", "ip"]

    def get_supported_output_types(self) -> List[str]:
        return ["url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))
        mode = str(kwargs.get("mode", "dir"))
        wordlist = str(
            kwargs.get("wordlist") or "/usr/share/wordlists/dirb/common.txt"
        )
        threads = int(kwargs.get("threads", 30))
        extensions = kwargs.get("extensions")

        if not input_value.startswith(("http://", "https://")):
            input_value = f"http://{input_value}"

        command = [
            self.tool_path,
            mode,
            "-u",
            input_value,
            "-w",
            wordlist,
            "-q",
            "-t",
            str(threads),
            "-k", # Skip SSL verification
        ]
        if extensions:
            command.extend(["-x", str(extensions)])

        result = self._run_command(command, timeout=timeout)

        discovered: List[Dict[str, Any]] = []
        pattern = re.compile(r"^(?P<path>/\S+)\s+\(Status:\s+(?P<status>\d+)\)")
        for raw_line in (result.get("stdout") or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("Progress:"):
                continue
            match = pattern.search(line)
            if not match:
                continue
            path = match.group("path")
            url = urljoin(input_value.rstrip("/") + "/", path.lstrip("/"))
            discovered.append(
                {
                    "type": "url",
                    "value": url,
                    "source": "gobuster",
                    "confidence": 0.8,
                    "properties": {
                        "path": path,
                        "status": int(match.group("status")),
                    },
                }
            )

        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()
        for d in discovered:
            url = d["value"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(d)

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


class CrtShWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "crtsh"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain", "url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        url = f"https://crt.sh/?q={input_value}&output=json"

        domains: List[Dict[str, Any]] = []
        try:
            response = requests.get(url, timeout=kwargs.get("timeout", 60))
            if response.status_code == 200:
                data = response.json()
                seen = set()
                for entry in data:
                    name_value = entry.get("name_value")
                    if name_value:
                        for domain in name_value.split("\n"):
                            domain = domain.strip()
                            if domain and domain != input_value and domain not in seen:
                                seen.add(domain)
                                domains.append({
                                    "type": "domain",
                                    "value": domain,
                                    "source": "crtsh",
                                    "confidence": 0.9,
                                    "properties": {
                                        "id": entry.get("id"),
                                        "issuer_name": entry.get("issuer_name")
                                    }
                                })
        except Exception as e:
            logger.error(f"crt.sh request failed: {e}")

        end_time = time.time()
        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": end_time - start_time,
            "start_time": start_time,
            "end_time": end_time,
            "command": ["curl", url],
        }
        return self._format_output(domains, execution_info)


class CensysWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "censys"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["ip", "domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})


class DirbWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "dirb"

    def is_tool_available(self) -> bool:
        import os
        from shutil import which
        # Default path in our docker container
        if os.path.exists("/usr/local/bin/dirb"):
             return True
        return which("dirb") is not None

    def get_supported_input_types(self) -> List[str]:
        return ["url"]

    def get_supported_output_types(self) -> List[str]:
        return ["url"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()
        if not input_value.startswith("http"):
             input_value = f"http://{input_value}"

        timeout = int(kwargs.get("timeout", 600))

        # Wordlist
        wordlist = kwargs.get("wordlist")
        if not wordlist:
            wordlist = "/usr/share/dirb/wordlists/common.txt"
            if not os.path.exists(wordlist):
                 wordlist = "/usr/share/wordlists/dirb/common.txt"
            if not os.path.exists(wordlist):
                 wordlist = "/tools/dirb/wordlists/common.txt"

        temp_dir = self._create_temp_dir()
        output_file = os.path.join(temp_dir, "dirb_output.txt")

        try:
            # dirb <url> <wordlist> -o <output>
            cmd = ["dirb", input_value, wordlist, "-o", output_file, "-S", "-r"] # -S: silent, -r: non-recursive (faster for test)
            result = self._run_command(cmd, timeout=timeout)

            discovered_urls = []

            # Parse output file
            if os.path.exists(output_file):
                 with open(output_file, "r") as f:
                      content = f.read()

                 # DIRB output format:
                 # + http://example.com/admin (CODE:200|SIZE:123)
                 # + http://example.com/robot.txt (CODE:200|SIZE:456)

                 for line in content.splitlines():
                      line = line.strip()
                      if line.startswith("+"):
                           parts = line.split()
                           if len(parts) >= 2:
                                url = parts[1]
                                # Extract code if present
                                code = 0
                                if "(CODE:" in line:
                                     try:
                                          code_str = line.split("(CODE:")[1].split("|")[0]
                                          code = int(code_str)
                                     except:
                                          pass

                                discovered_urls.append({
                                     "type": "url",
                                     "value": url,
                                     "source": "dirb",
                                     "confidence": 1.0,
                                     "properties": {
                                          "status_code": code
                                     }
                                })

            # Also parse stdout if file failed for some reason
            if not discovered_urls and result.get("stdout"):
                 for line in result["stdout"].splitlines():
                      line = line.strip()
                      if line.startswith("+"):
                           parts = line.split()
                           if len(parts) >= 2:
                                url = parts[1]
                                discovered_urls.append({
                                     "type": "url",
                                     "value": url,
                                     "source": "dirb",
                                     "confidence": 1.0,
                                     "properties": {}
                                })

        finally:
            self._cleanup_temp_dir()

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result.get("execution_time", 0),
            "command": result.get("command"),
        }
        return self._format_output(discovered_urls, execution_info)


class NiktoWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "nikto"

    def is_tool_available(self) -> bool:
        import os
        from shutil import which
        if os.path.exists("/usr/local/bin/nikto"):
            return True
        return which("nikto") is not None

    def get_supported_input_types(self) -> List[str]:
        return ["url", "domain", "ip"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        # Nikto needs host (IP or domain) usually, or URL
        # If URL, stripped protocol often preferred but -h handles url too.

        timeout = int(kwargs.get("timeout", 1200)) # Nikto is slow

        temp_dir = self._create_temp_dir()
        output_file = os.path.join(temp_dir, "nikto_results.json")

        try:
            # nikto -h <target> -Format json -o <output>
            # -Tuning x (optional)
            cmd = ["nikto", "-h", input_value, "-Format", "json", "-o", output_file]

            # Nikto might fail if it takes too long, but let's try
            result = self._run_command(cmd, timeout=timeout)

            findings = []

            if os.path.exists(output_file):
                 try:
                      with open(output_file, "r") as f:
                           data = json.load(f)

                      # Nikto JSON format: { "vulnerabilities": [ { "id": "...", "msg": "..." } ], ... }
                      # Or list of scans?
                      # Standard Nikto JSON usually has a root key or list.

                      # Assuming standard structure
                      vulnerabilities = data.get("vulnerabilities", [])
                      for vuln in vulnerabilities:
                           findings.append({
                                "type": "other", # vulnerability
                                "value": vuln.get("msg", "Unknown vulnerability"),
                                "source": "nikto",
                                "confidence": 0.9,
                                "properties": {
                                     "id": vuln.get("id"),
                                     "method": vuln.get("method"),
                                     "url": vuln.get("url"),
                                     "osvdb": vuln.get("osvdb")
                                }
                           })

                      if not vulnerabilities and "nikto_scan_details" in data:
                           # Sometimes it's wrapped
                           pass

                 except Exception as e:
                      logger.error(f"Failed to parse nikto json: {e}")

        finally:
            self._cleanup_temp_dir()

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result.get("execution_time", 0),
            "command": result.get("command"),
        }
        return self._format_output(findings, execution_info)


class WhatwebWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "whatweb"

    def is_tool_available(self) -> bool:
        import os
        from shutil import which
        if os.path.exists("/usr/local/bin/whatweb"):
            return True
        return which("whatweb") is not None

    def get_supported_input_types(self) -> List[str]:
        return ["url", "domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["technology"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 300))

        # Determine if we should use HTTP or HTTPS
        # If input is a domain, try both or prefer https.
        # For whatweb, it handles it, but let's default to http:// if no protocol
        target = input_value
        if not target.startswith(("http://", "https://")):
             target = f"http://{target}"

        command = [self.tool_path, "--log-json=/dev/stdout", target]

        result = self._run_command(command, timeout=timeout)

        technologies: List[Dict[str, Any]] = []
        try:
            raw_output = result.get("stdout") or "[]"
            # WhatWeb JSON output is a list of objects
            # Sometimes it outputs multiple JSON objects if redirects happen?
            # Usually it's a valid JSON array.
            data = json.loads(raw_output)

            for entry in data:
                # entry is like {"target":..., "plugins": {...}}
                plugins = entry.get("plugins", {})
                for plugin_name, plugin_data in plugins.items():
                    # plugin_data is like {"string": ["..."], "version": ["..."]}
                    version = ""
                    if "version" in plugin_data and plugin_data["version"]:
                         version = plugin_data["version"][0]

                    technologies.append({
                        "type": "technology",
                        "value": plugin_name,
                        "source": "whatweb",
                        "confidence": 1.0,
                        "properties": {
                            "version": version,
                            "modules": plugin_data.get("module", []),
                            "string": plugin_data.get("string", [])
                        }
                    })

        except Exception as e:
            logger.error(f"Failed to parse whatweb output: {e}. Raw output: {result.get('stdout')[:200]}")

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(technologies, execution_info)


class WappalyzerWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "wappalyzer"

    def is_tool_available(self) -> bool:
        return True

    def _find_tool_path(self) -> Optional[str]:
        return "python-library"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "url"]

    def get_supported_output_types(self) -> List[str]:
        return ["technology", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        target = input_value
        if not target.startswith(("http://", "https://")):
             target = f"https://{target}"

        start_time = time.time()

        technologies_found: List[Dict[str, Any]] = []
        error = None

        try:
            # Import here to avoid import errors if not installed in backend
            from Wappalyzer import Wappalyzer, WebPage

            wappalyzer = Wappalyzer.latest()
            try:
                webpage = WebPage.new_from_url(target)
            except requests.exceptions.SSLError:
                webpage = WebPage.new_from_url(target, verify=False)
            # Analyze returns a set of technology names
            # Some versions return a dict with confidence, versions, etc.
            # python-Wappalyzer usually returns a set of strings or dict depending on method.
            # analyze_with_versions_and_categories() is available in newer versions

            # Try to get detailed info if available
            if hasattr(wappalyzer, 'analyze_with_versions_and_categories'):
                results = wappalyzer.analyze_with_versions_and_categories(webpage)
                # Format: {'Tech Name': {'versions': ['1.0'], 'categories': ['CMS']}}
                for tech_name, tech_data in results.items():
                    versions = tech_data.get('versions', [])
                    categories = tech_data.get('categories', [])

                    technologies_found.append({
                        "type": "technology",
                        "value": tech_name,
                        "source": "wappalyzer",
                        "confidence": 1.0,
                        "properties": {
                            "versions": versions,
                            "categories": categories
                        }
                    })
            else:
                # Fallback to simple analyze
                results = wappalyzer.analyze(webpage)
                for tech_name in results:
                    technologies_found.append({
                        "type": "technology",
                        "value": tech_name,
                        "source": "wappalyzer",
                        "confidence": 1.0,
                        "properties": {}
                    })

        except ImportError:
            error = "python-Wappalyzer not installed"
            logger.error(error)
        except Exception as e:
            error = str(e)
            logger.error(f"Wappalyzer failed: {e}")

        end_time = time.time()
        execution_time = end_time - start_time

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "command": "python-Wappalyzer library",
            "error": error
        }

        return self._format_output(technologies_found, execution_info)


class UrlScanWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "urlscan"

    def is_tool_available(self) -> bool:
        return True

    def _find_tool_path(self) -> Optional[str]:
        return "python-library"

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "url"]

    def get_supported_output_types(self) -> List[str]:
        return ["url", "ip", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        api_key = os.environ.get("URLSCAN_API_KEY")
        if not api_key:
             raise ValueError("URLSCAN_API_KEY not configured")

        target = input_value
        # UrlScan prefers URLs or domains.

        start_time = time.time()
        results: List[Dict[str, Any]] = []
        error = None

        try:
            headers = {
                'API-Key': api_key,
                'Content-Type': 'application/json'
            }
            data = {
                "url": target,
                "visibility": "public"
            }

            # 1. Submit Scan
            submit_resp = requests.post(
                'https://urlscan.io/api/v1/scan/',
                headers=headers,
                json=data,
                timeout=30
            )

            if submit_resp.status_code != 200:
                raise Exception(f"Submission failed: {submit_resp.text}")

            submit_data = submit_resp.json()
            uuid = submit_data.get("uuid")
            result_url = submit_data.get("result")
            api_url = submit_data.get("api")

            logger.info(f"UrlScan submitted. UUID: {uuid}. Waiting for results...")

            # 2. Poll for results
            # Wait a bit before first check
            time.sleep(10)

            max_retries = 20
            for i in range(max_retries):
                poll_resp = requests.get(api_url, timeout=30)

                if poll_resp.status_code == 200:
                    scan_data = poll_resp.json()

                    # Extract Page Info
                    page = scan_data.get("page", {})
                    task = scan_data.get("task", {})
                    lists = scan_data.get("lists", {})

                    # Add Result URL
                    results.append({
                        "type": "url",
                        "value": result_url,
                        "source": "urlscan",
                        "confidence": 1.0,
                        "properties": {
                            "type": "report",
                            "screenshot": task.get("screenshotURL")
                        }
                    })

                    # Add IP
                    if page.get("ip"):
                        results.append({
                            "type": "ip",
                            "value": page.get("ip"),
                            "source": "urlscan",
                            "confidence": 1.0,
                            "properties": {
                                "asn": page.get("asn"),
                                "asnname": page.get("asnname"),
                                "country": page.get("country")
                            }
                        })

                    # Add Screenshot URL as a special entity or property?
                    # We already added it to the report URL properties.

                    break
                elif poll_resp.status_code == 404:
                    # Still scanning
                    time.sleep(5)
                else:
                    logger.warning(f"UrlScan poll error: {poll_resp.status_code}")
                    time.sleep(5)
            else:
                 error = "Timeout waiting for UrlScan results"

        except Exception as e:
            error = str(e)
            logger.error(f"UrlScan failed: {e}")

        end_time = time.time()
        execution_time = end_time - start_time

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": execution_time,
            "start_time": start_time,
            "end_time": end_time,
            "command": "urlscan API",
            "error": error
        }

        return self._format_output(results, execution_info)


class VirusTotalWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "virustotal"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "ip", "hash", "url"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})


class SecurityTrailsWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "securitytrails"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain", "ip"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})


class HIBPWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "hibp"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["email"]

    def get_supported_output_types(self) -> List[str]:
        return ["leak"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})


class DehashedWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "dehashed"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["email", "domain", "ip", "username"]

    def get_supported_output_types(self) -> List[str]:
        return ["leak"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})


class ReconNgWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "recon-ng"

    def is_tool_available(self) -> bool:
        import os
        from shutil import which
        if os.path.exists("/tools/recon-ng/recon-ng"):
            return True
        return which("recon-ng") is not None

    def get_supported_input_types(self) -> List[str]:
        return ["domain"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain", "ip", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        target = input_data["value"]

        # Use a temporary workspace and file for results
        import uuid
        import os
        import json

        workspace_name = f"ws_{uuid.uuid4().hex[:8]}"
        temp_dir = self._create_temp_dir()
        output_file = os.path.join(temp_dir, "results.json")
        rc_file = os.path.join(temp_dir, "scan.rc")

        # Recon-ng path
        recon_ng_path = "/tools/recon-ng/recon-ng"
        if not os.path.exists(recon_ng_path):
            recon_ng_path = "recon-ng" # Fallback to PATH

        # Build resource file content
        # Note: recon-ng commands vary by version. Assuming v5+.
        # We include marketplace install commands to ensure modules exist at runtime
        rc_content = [
            f"workspaces create {workspace_name}",
            f"workspaces load {workspace_name}",
            "marketplace refresh",
            "marketplace install recon/domains-hosts/hackertarget",
            "marketplace install reporting/json",
            f"db insert domains domain {target}",
            "modules load recon/domains-hosts/hackertarget",
            "run",
            "modules load reporting/json",
            f"options set FILENAME {output_file}",
            "run",
            "workspaces remove", # Removes current workspace
            "exit"
        ]

        with open(rc_file, "w") as f:
            f.write("\n".join(rc_content))

        # Execute
        try:
            # We must NOT use --no-marketplace if we want to install modules via RC file
            cmd = [recon_ng_path, "-r", rc_file, "--no-analytics", "--no-version"]
            timeout = int(kwargs.get("timeout", 300))
            result = self._run_command(cmd, timeout=timeout)

            # Parse results
            entities = []
            if os.path.exists(output_file):
                try:
                    with open(output_file, "r") as f:
                        data = json.load(f)

                    # Recon-ng JSON output structure:
                    # {"hosts": [...], "domains": [...], ...} or list of tables?
                    # Usually it exports the tables.
                    # Let's assume standard reporting/json output which is usually a dict with table names as keys.

                    if isinstance(data, dict):
                        for table, rows in data.items():
                            if table == "hosts":
                                for row in rows:
                                    host = row.get("host")
                                    ip = row.get("ip_address")
                                    if host:
                                        entities.append({
                                            "type": "domain",
                                            "value": host,
                                            "source": "recon-ng",
                                            "confidence": 0.9,
                                            "properties": row
                                        })
                                    if ip:
                                        entities.append({
                                            "type": "ip",
                                            "value": ip,
                                            "source": "recon-ng",
                                            "confidence": 0.9,
                                            "properties": row
                                        })
                            elif table == "domains":
                                for row in rows:
                                    domain = row.get("domain")
                                    if domain and domain != target:
                                        entities.append({
                                            "type": "domain",
                                            "value": domain,
                                            "source": "recon-ng",
                                            "confidence": 0.9,
                                            "properties": row
                                        })
                except Exception as e:
                     # Log error but return what we have (or empty)
                     # We can't log easily here without self.logger if not set, but BaseWrapper has logger?
                     # BaseWrapper uses 'import logging; logger = ...' at module level usually.
                     pass
        finally:
            self._cleanup_temp_dir()

        return self._format_output(entities, {"raw_output": result["stdout"]})


class SpiderFootWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "spiderfoot"

    def is_tool_available(self) -> bool:
        from shutil import which
        return which("sf.py") is not None

    def get_supported_input_types(self) -> List[str]:
        return ["domain", "ip", "username", "email", "phone"]

    def get_supported_output_types(self) -> List[str]:
        return ["domain", "ip", "url", "email", "other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        target = input_data["value"]

        # Resolve sf.py path
        from shutil import which
        import os
        sf_path = which("sf.py")
        if not sf_path:
            # Try common locations
            if os.path.exists("/tools/spiderfoot/sf.py"):
                sf_path = "/tools/spiderfoot/sf.py"
            elif os.path.exists("/app/spiderfoot/sf.py"):
                sf_path = "/app/spiderfoot/sf.py"
            else:
                # Fallback to just sf.py and hope it's in PATH (which failed before)
                sf_path = "sf.py"

        # Build command
        cmd = [sf_path, "-s", target, "-o", "json", "-q"]

        # Optional parameters
        # Use case: all, footprint, investigate, passive (default: passive)
        use_case = kwargs.get("use_case", "passive")
        if use_case:
            cmd.extend(["-u", use_case])

        # Specific modules
        modules = kwargs.get("modules")
        if modules:
            cmd.extend(["-m", modules])

        # Execute
        timeout = int(kwargs.get("timeout", 300))
        result = self._run_command(cmd, timeout=timeout)
        if result["return_code"] != 0:
            raise Exception(f"SpiderFoot execution failed: {result['stderr']}")

        # Parse JSON
        # SpiderFoot CLI with -o json outputs a stream of JSON objects (NDJSON)
        raw_output = result["stdout"]
        data = []
        try:
            # Try standard JSON first (just in case it returns a list)
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            # Try NDJSON (Newlines Delimited JSON)
            lines = raw_output.strip().split('\n')
            for line in lines:
                line = line.strip()
                # Remove trailing comma if present (sometimes tools output [ {...}, {...} ] but split by lines)
                if line.endswith(','):
                    line = line[:-1]

                if not line:
                    continue

                try:
                    obj = json.loads(line)
                    data.append(obj)
                except json.JSONDecodeError:
                    # Could be just a log line, ignore
                    pass

            if not data and raw_output:
                # If still no data but we have output, maybe return raw error
                return self._format_output([], {"raw": raw_output, "error": "JSON parse error or no data"})

        # Map results to entities
        # SpiderFoot data structure (from documentation/experience):
        # [ [event_type, event_data, source_module, ...], ... ]
        # or dicts?
        # Let's assume it returns a list of events.

        entities = []
        # We need to inspect the data structure.
        # If it's a list:
        if isinstance(data, list):
            for event in data:
                # event might be a dict or list
                # Usually: [generated_date, event_type, event_data, module, source_event, ...]
                # Or dict: {"type": ..., "data": ...}
                # Let's try to handle both or generic.

                # Check if it's the expected list format from SF 4.0 CLI
                # CLI output with -o json is often a list of dicts or list of lists.
                # Let's be safe and inspect first item if possible during dev,
                # but here we must implement.

                evt_type = None
                evt_data = None

                if isinstance(event, list) and len(event) >= 3:
                    evt_type = event[1]
                    evt_data = event[2]
                elif isinstance(event, dict):
                    evt_type = event.get("type")
                    evt_data = event.get("data")

                if evt_type and evt_data:
                    # Map SF types to our types
                    entity_type = "other"
                    if "DOMAIN" in evt_type or "HOSTNAME" in evt_type:
                        entity_type = "domain"
                    elif "IP_ADDRESS" in evt_type:
                        entity_type = "ip"
                    elif "URL" in evt_type:
                        entity_type = "url"
                    elif "EMAIL" in evt_type:
                        entity_type = "email"

                    if evt_data != target:  # Exclude self if needed, but SF often returns self as first event
                        entities.append({
                            "type": entity_type,
                            "value": evt_data,
                            "source": "spiderfoot",
                            "confidence": 1.0,  # SF doesn't provide confidence easily in CLI
                            "properties": {"sf_type": evt_type}
                        })

        return self._format_output(entities, {"raw_count": len(entities)})


class MaltegoWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "maltego"

    def is_tool_available(self) -> bool:
        return True

    def get_supported_input_types(self) -> List[str]:
        return ["any"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        return self._format_output([], {})
