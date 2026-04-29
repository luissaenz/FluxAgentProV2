from src.mcp.exceptions import (
    AuthError,
    InternalError,
    InvalidParams,
    MCPError,
    MethodNotFound,
    NotFound,
    mcp_error_to_response,
)


def test_mcp_error_properties():
    """Verify that MCPError and subclasses have correct JSON-RPC codes."""
    assert MCPError.code == -32603
    assert AuthError.code == -32001
    assert NotFound.code == -32004
    assert MethodNotFound.code == -32601
    assert InvalidParams.code == -32602
    assert InternalError.code == -32603

def test_mcp_error_to_response_custom_error():
    """Verify helper with custom MCPError."""
    exc = AuthError("Token expired", data={"reason": "expired"})
    resp = mcp_error_to_response(exc, request_id=123)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 123
    assert resp["error"]["code"] == -32001
    assert resp["error"]["message"] == "Token expired"
    assert resp["error"]["data"] == {"reason": "expired"}

def test_mcp_error_to_response_generic_exception():
    """Verify helper with non-MCP exception (should sanitize and log)."""
    exc = ValueError("Secret leakage or raw error")
    resp = mcp_error_to_response(exc, request_id="abc")

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "abc"
    assert resp["error"]["code"] == -32603
    assert resp["error"]["message"] == "Internal error"  # Sanitized
    assert resp["error"]["data"] is None

def test_mcp_error_to_response_internal_error_explicit():
    """Verify helper with explicit InternalError (should keep message)."""
    exc = InternalError("Database is down")
    resp = mcp_error_to_response(exc, request_id=1)

    assert resp["error"]["code"] == -32603
    assert resp["error"]["message"] == "Database is down"  # Not sanitized because it's MCPError
