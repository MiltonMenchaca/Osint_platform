import logging
from typing import Dict, Any
from urllib.parse import urlparse

from apps.transforms.wrappers.base import ToolNotFoundError
from apps.transforms.wrappers.network_tools import PingWrapper
from apps.transforms.wrappers.nmap import NmapWrapper
from apps.transforms.wrappers.web_enum import WappalyzerWrapper, DnsTwistWrapper, HttpxWrapper

logger = logging.getLogger(__name__)


class AutoReconService:
    """
    Service for Automated Reconnaissance
    Executes a sequence of OSINT tools against a target URL/Domain.
    """

    def __init__(self):
        self.ping = self._safe_wrapper(PingWrapper, "ping")
        self.nmap = self._safe_wrapper(NmapWrapper, "nmap")
        self.wappalyzer = self._safe_wrapper(WappalyzerWrapper, "wappalyzer")
        self.dnstwist = self._safe_wrapper(DnsTwistWrapper, "dnstwist")
        self.httpx = self._safe_wrapper(HttpxWrapper, "httpx")

        try:
            from apps.transforms.wrappers.web_enum import WhoisWrapper
            self.whois = self._safe_wrapper(WhoisWrapper, "whois")
        except ImportError:
            self.whois = None
            logger.warning("WhoisWrapper not found, skipping Whois.")

    def _safe_wrapper(self, wrapper_cls, name: str):
        try:
            return wrapper_cls()
        except ToolNotFoundError as e:
            logger.warning(f"{name} not available: {e}")
            return None
        except Exception as e:
            logger.error(f"{name} init failed: {e}")
            return None

    def _normalize_target(self, target: str) -> Dict[str, str]:
        cleaned = (target or "").strip().strip("`").strip("\"'").strip()
        parsed = urlparse(cleaned if "://" in cleaned else f"http://{cleaned}")
        domain = (parsed.hostname or "").strip()
        return {"cleaned": cleaned, "domain": domain}

    def run_scan(self, target: str) -> Dict[str, Any]:
        """
        Run the full reconnaissance suite
        """
        normalized = self._normalize_target(target)
        results = {
            "target": normalized["cleaned"] or target,
            "status": "completed",
            "tools": {},
        }

        logger.info(f"Starting Auto Recon Service on: {results['target']}")
        domain = normalized["domain"]
        if not domain:
            results["status"] = "failed"
            results["error"] = "Target inválido"
            return results

        # 1. Ping (Availability)
        logger.info("[+] Running Ping...")
        if self.ping:
            try:
                ping_res = self.ping.execute({"type": "domain", "value": domain}, count=3)
                results["tools"]["ping"] = ping_res
            except Exception as e:
                logger.error(f"Ping failed: {e}")
                results["tools"]["ping"] = {"error": str(e)}
        else:
            results["tools"]["ping"] = {"error": "Herramienta no disponible"}

        # 2. Whois (Registration Info)
        if self.whois:
            logger.info("[+] Running Whois...")
            try:
                whois_res = self.whois.execute({"type": "domain", "value": domain})
                results['tools']['whois'] = whois_res
            except Exception as e:
                logger.error(f"Whois failed: {e}")
                results['tools']['whois'] = {"error": str(e)}
        else:
            results["tools"]["whois"] = {"error": "Herramienta no disponible"}

        # 3. DNS / DNSTwist (Permutations/Info)
        logger.info("[+] Running DNS Analysis...")
        if self.dnstwist:
            try:
                dns_res = self.dnstwist.execute({"type": "domain", "value": domain})
                results["tools"]["dns"] = dns_res
            except Exception as e:
                logger.error(f"DNS Analysis failed: {e}")
                results["tools"]["dns"] = {"error": str(e)}
        else:
            results["tools"]["dns"] = {"error": "Herramienta no disponible"}

        # 4. Wappalyzer (Tech Stack)
        logger.info("[+] Running Wappalyzer...")
        if self.wappalyzer:
            try:
                web_res = self.wappalyzer.execute({"type": "domain", "value": results["target"]})
                results["tools"]["wappalyzer"] = web_res
            except Exception as e:
                logger.error(f"Wappalyzer failed: {e}")
                results["tools"]["wappalyzer"] = {"error": str(e)}
        else:
            results["tools"]["wappalyzer"] = {"error": "Herramienta no disponible"}

        # 5. Nmap (Port Scan - Quick)
        logger.info("[+] Running Nmap...")
        if self.nmap:
            try:
                nmap_res = self.nmap.execute(
                    {"type": "domain", "value": domain},
                    ports="top-100",
                    timing=4,
                    scan_type="tcp_connect",
                )
                results["tools"]["nmap"] = nmap_res
            except Exception as e:
                logger.error(f"Nmap failed: {e}")
                results["tools"]["nmap"] = {"error": str(e)}
        else:
            results["tools"]["nmap"] = {"error": "Herramienta no disponible"}

        return results
