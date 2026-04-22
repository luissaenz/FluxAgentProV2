"""MCP Exceptions — Hierarchy of JSON-RPC compatible errors."""

from typing import Any, Optional


class MCPError(Exception):
    """Base category for MCP/JSON-RPC errors."""
    code: int = -32603  # Internal error by default
    message: str = "Internal error"
    data: Optional[Any] = None

    def __init__(self, message: Optional[str] = None, data: Optional[Any] = None):
        if message:
            self.message = message
        self.data = data
        super().__init__(self.message)


class ParseError(MCPError):
    """Invalid JSON was received by the server."""
    code = -32700
    message = "Parse error"


class InvalidRequest(MCPError):
    """The JSON sent is not a valid Request object."""
    code = -32600
    message = "Invalid Request"


class MethodNotFound(MCPError):
    """The method does not exist / is not available."""
    code = -32601
    message = "Method not found"


class InvalidParams(MCPError):
    """Invalid method parameter(s)."""
    code = -32602
    message = "Invalid params"


class InternalError(MCPError):
    """Internal JSON-RPC error."""
    code = -32603
    message = "Internal error"


class AuthError(MCPError):
    """Authentication or authorization failed."""
    # Use -32000 for custom implementation errors
    code = -32001
    message = "Authentication or authorization failed"


class NotFound(MCPError):
    """Resource (flow, task, etc) not found."""
    code = -32004
    message = "Resource not found"


def mcp_error_to_response(error: Exception, request_id: Any = None) -> dict:
    """Convert an exception into a standard JSON-RPC error response.

    Args:
        error: The exception to convert.
        request_id: The ID of the request that caused the error.

    Returns:
        dict: Standard JSON-RPC error structure.
    """
    if isinstance(error, MCPError):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": error.code,
                "message": error.message,
                "data": error.data
            }
        }

    # Fallback for unexpected exceptions
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32603,
            "message": str(error)
        }
    }
