"""MCP-specific exceptions and error mapping.
"""

from typing import Any, Dict

class MCPError(Exception):
    """Base class for MCP errors with JSON-RPC codes."""
    def __init__(self, message: str, code: int = -32603, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        result = {"code": self.code, "message": str(self)}
        if self.data:
            result["data"] = self.data
        return result

class FlowNotFoundError(MCPError):
    """Raised when a requested flow_type is not registered."""
    def __init__(self, flow_type: str, available_flows: list[str]):
        super().__init__(
            f"Flow '{flow_type}' not found.",
            code=-32602,
            data={"available_flows": available_flows}
        )

class InvalidInputError(MCPError):
    """Raised when input_data is invalid."""
    def __init__(self, message: str):
        super().__init__(message, code=-32602)

def map_exception_to_mcp_error(exc: Exception) -> MCPError:
    """Maps standard Python exceptions to MCPError."""
    if isinstance(exc, MCPError):
        return exc
    
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return InvalidInputError(str(exc))
    
    if isinstance(exc, (LookupError)):
        return MCPError(str(exc), code=-32602)
        
    return MCPError(f"Internal error: {str(exc)}", code=-32603)
