"""OSINT Tools Wrappers

This package contains wrappers for various OSINT tools to standardize
their usage within the platform.
"""

from .amass import AmassWrapper
from .assetfinder import AssetfinderWrapper
from .base import BaseWrapper, OSINTToolError, ToolNotFoundError, ToolTimeoutError
from .holehe import HoleheWrapper
from .nmap import NmapWrapper
from .nuclei import NucleiWrapper
from .dmitry import DmitryWrapper
from .sherlock import SherlockWrapper
from .shodan import ShodanWrapper
from .subfinder import SubfinderWrapper
from .theharvester import TheHarvesterWrapper
from .network_tools import MasscanWrapper, PingWrapper, TracerouteWrapper, ZmapWrapper
from .web_enum import (
    CensysWrapper,
    CrtShWrapper,
    DirbWrapper,
    DehashedWrapper,
    GobusterWrapper,
    HIBPWrapper,
    HttpxWrapper,
    MaltegoWrapper,
    NiktoWrapper,
    ReconNgWrapper,
    SpiderFootWrapper,
    WappalyzerWrapper,
    SecurityTrailsWrapper,
    VirusTotalWrapper,
    WaybackUrlsWrapper,
    WhatwebWrapper,
    DnsTwistWrapper,
    WhoisWrapper,
    UrlScanWrapper,
)
from .metadata import ExifToolWrapper
from .google_search import GoogleSearchWrapper

__all__ = [
    "BaseWrapper",
    "OSINTToolError",
    "ToolNotFoundError",
    "ToolTimeoutError",
    "AssetfinderWrapper",
    "GoogleSearchWrapper",
    "ShodanWrapper",
    "NmapWrapper",
    "NucleiWrapper",
    "DmitryWrapper",
    "AmassWrapper",
    "HoleheWrapper",
    "SubfinderWrapper",
    "TheHarvesterWrapper",
    "SherlockWrapper",
    "PingWrapper",
    "TracerouteWrapper",
    "MasscanWrapper",
    "ZmapWrapper",
    "HttpxWrapper",
    "WaybackUrlsWrapper",
    "GobusterWrapper",
    "DirbWrapper",
    "NiktoWrapper",
    "WhatwebWrapper",
    "WappalyzerWrapper",
    "UrlScanWrapper",
    "VirusTotalWrapper",
    "SecurityTrailsWrapper",
    "CensysWrapper",
    "HIBPWrapper",
    "DehashedWrapper",
    "CrtShWrapper",
    "ReconNgWrapper",
    "SpiderFootWrapper",
    "MaltegoWrapper",
    "DnsTwistWrapper",
    "WhoisWrapper",
    "ExifToolWrapper",
    "GoogleSearchWrapper",
]

# Registry of available wrappers
WRAPPER_REGISTRY = {
    "google_search": GoogleSearchWrapper,
    "assetfinder": AssetfinderWrapper,
    "shodan": ShodanWrapper,
    "nmap": NmapWrapper,
    "nuclei": NucleiWrapper,
    "dmitry": DmitryWrapper,
    "amass": AmassWrapper,
    "holehe": HoleheWrapper,
    "subfinder": SubfinderWrapper,
    "theharvester": TheHarvesterWrapper,
    "theHarvester": TheHarvesterWrapper,
    "sherlock": SherlockWrapper,
    "ping": PingWrapper,
    "traceroute": TracerouteWrapper,
    "masscan": MasscanWrapper,
    "zmap": ZmapWrapper,
    "httpx": HttpxWrapper,
    "waybackurls": WaybackUrlsWrapper,
    "wayback": WaybackUrlsWrapper,
    "gobuster": GobusterWrapper,
    "dirb": DirbWrapper,
    "nikto": NiktoWrapper,
    "whatweb": WhatwebWrapper,
    "wappalyzer": WappalyzerWrapper,
    "virustotal": VirusTotalWrapper,
    "securitytrails": SecurityTrailsWrapper,
    "censys": CensysWrapper,
    "hibp": HIBPWrapper,
    "dehashed": DehashedWrapper,
    "crtsh": CrtShWrapper,
    "recon-ng": ReconNgWrapper,
    "spiderfoot": SpiderFootWrapper,
    "maltego": MaltegoWrapper,
    "dnstwist": DnsTwistWrapper,
    "whois": WhoisWrapper,
    "exiftool": ExifToolWrapper,
    "urlscan": UrlScanWrapper,
}


def get_wrapper(tool_name):
    """Get wrapper class by tool name"""
    if tool_name not in WRAPPER_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")
    return WRAPPER_REGISTRY[tool_name]


def list_available_tools():
    """List all available OSINT tools"""
    return list(WRAPPER_REGISTRY.keys())
