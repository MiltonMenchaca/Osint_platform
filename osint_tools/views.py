import re

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.authentication.permissions import HasAPIAccess
from apps.transforms.wrappers.base import ToolNotFoundError
from apps.transforms.wrappers.holehe import HoleheWrapper
from apps.transforms.wrappers.network_tools import PingWrapper
from apps.transforms.wrappers.nmap import NmapWrapper
from apps.transforms.wrappers.web_enum import DnsTwistWrapper, HttpxWrapper, WappalyzerWrapper, WhoisWrapper


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def holehe_search(request):
    email = request.data.get("email")
    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return Response(
            {"error": "Invalid email format"}, status=status.HTTP_400_BAD_REQUEST
        )

    timeout = request.data.get("timeout", 300)
    only_used = request.data.get("only_used", True)

    wrapper = HoleheWrapper()
    result = wrapper.execute(
        {"type": "email", "value": email}, timeout=timeout, only_used=only_used
    )

    results = result.get("results", [])
    metadata = result.get("metadata", {})

    return Response(
        {
            "success": True,
            "email": email,
            "tool": result.get("tool"),
            "input_type": result.get("input_type"),
            "input_value": result.get("input_value"),
            "results": results,
            "metadata": metadata,
            "accounts_found": metadata.get("accounts_found", len(results)),
            "execution_time": metadata.get("execution_time", 0) or 0,
            "total_platforms_checked": metadata.get("total_platforms_checked", 0) or 0,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def holehe_status(request):
    try:
        wrapper = HoleheWrapper()
    except ToolNotFoundError:
        return Response(
            {
                "success": True,
                "data": {"installed": False, "version": None, "status": "missing"},
            }
        )

    tool_info = wrapper.get_tool_info()
    return Response(
        {
            "success": True,
            "data": {
                "installed": bool(tool_info.get("available")),
                "version": tool_info.get("version"),
                "status": "ready" if tool_info.get("available") else "missing",
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def tools_status(request):
    tools = {
        "ping": PingWrapper,
        "whois": WhoisWrapper,
        "dnstwist": DnsTwistWrapper,
        "httpx": HttpxWrapper,
        "wappalyzer": WappalyzerWrapper,
        "nmap": NmapWrapper,
    }

    data = {}
    for name, wrapper_cls in tools.items():
        try:
            wrapper = wrapper_cls()
            info = wrapper.get_tool_info()
            data[name] = {
                "installed": bool(info.get("available")),
                "version": info.get("version"),
                "status": "ready" if info.get("available") else "missing",
            }
        except ToolNotFoundError:
            data[name] = {"installed": False, "version": None, "status": "missing"}
        except Exception as e:
            data[name] = {"installed": False, "version": None, "status": f"error: {e}"}

    return Response({"success": True, "data": data})
