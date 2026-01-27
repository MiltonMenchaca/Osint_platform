"""OSINT Tools Wrappers

This package contains wrappers for various OSINT tools to standardize
their usage within the platform.
"""

from .amass import AmassWrapper
from .assetfinder import AssetfinderWrapper
from .base import BaseWrapper, OSINTToolError, ToolNotFoundError, ToolTimeoutError
from .holehe import HoleheWrapper
from .nmap import NmapWrapper
from .shodan import ShodanWrapper

__all__ = [
    "BaseWrapper",
    "OSINTToolError",
    "ToolNotFoundError",
    "ToolTimeoutError",
    "AssetfinderWrapper",
    "ShodanWrapper",
    "NmapWrapper",
    "AmassWrapper",
    "HoleheWrapper",
]

# Registry of available wrappers
WRAPPER_REGISTRY = {
    "assetfinder": AssetfinderWrapper,
    "shodan": ShodanWrapper,
    "nmap": NmapWrapper,
    "amass": AmassWrapper,
    "holehe": HoleheWrapper,
}


def get_wrapper(tool_name):
    """Get wrapper class by tool name"""
    if tool_name not in WRAPPER_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")
    return WRAPPER_REGISTRY[tool_name]


def list_available_tools():
    """List all available OSINT tools"""
    return list(WRAPPER_REGISTRY.keys())
