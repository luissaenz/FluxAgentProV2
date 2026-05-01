"""Unit tests: sanitize_output — Paso 1, Gap 4.

Tests U4.1-U4.11: 7 patrones de secreto + dict anidado + lista +
primitivos passthrough + string limpio + manejo de errores.
Función pura sin IO — sin mocking.
"""

from __future__ import annotations

from unittest.mock import patch

from src.mcp.sanitizer import sanitize_output

# ── U4.1-U4.7: 7 patrones de secreto ────────────────────────────


def test_sanitize_stripe_live_key():
    """U4.1: Stripe live key → [REDACTED]."""
    result = sanitize_output("sk_live_abc123xyz")
    assert result == "[REDACTED]"


def test_sanitize_stripe_test_key():
    """U4.2: Stripe test key → [REDACTED]."""
    result = sanitize_output("sk_test_abc123xyz")
    assert result == "[REDACTED]"


def test_sanitize_bearer_token():
    """U4.3: Bearer token → [REDACTED]."""
    result = sanitize_output("Bearer abc123def456ghi789jkl012mno345pqr678+=")
    assert result == "[REDACTED]"


def test_sanitize_basic_auth():
    """U4.4: Basic auth token → [REDACTED]."""
    result = sanitize_output("Basic abc123def456ghi789+/=")
    assert result == "[REDACTED]"


def test_sanitize_slack_token():
    """U4.5: Slack token → [REDACTED]."""
    result = sanitize_output("xoxb-1234567890-abcdef")
    assert result == "[REDACTED]"


def test_sanitize_github_pat():
    """U4.6: GitHub PAT → [REDACTED]."""
    result = sanitize_output("ghp_abc123def456ghi789")
    assert result == "[REDACTED]"


def test_sanitize_google_api_key():
    """U4.7: Google API key → [REDACTED]."""
    result = sanitize_output("AIzaSyAbc123Def456Ghi789Jkl")
    assert result == "[REDACTED]"


# ── U4.8: Dict anidado — estructura preservada, secreto redactado


def test_sanitize_nested_dict():
    """U4.8: Dict anidado → estructura preservada, secretos redactados."""
    data = {
        "auth": "sk_test_abc123",
        "meta": {
            "token": "sk_live_def456",
        },
        "safe": "just some text",
    }
    result = sanitize_output(data)

    assert result["auth"] == "[REDACTED]"
    assert result["meta"]["token"] == "[REDACTED]"
    assert result["safe"] == "just some text"


# ── U4.9: Lista — secreto redactado en cada elemento ───────────


def test_sanitize_list_with_secrets():
    """U4.9: Lista con secretos → cada elemento redactado."""
    data = ["sk_live_abc", "texto normal", "ghp_123def"]
    result = sanitize_output(data)

    assert result[0] == "[REDACTED]"
    assert result[1] == "texto normal"
    assert result[2] == "[REDACTED]"


# ── U4.10: Primitivos passthrough ──────────────────────────────


def test_sanitize_int_passthrough():
    """U4.10a: int → passthrough sin cambios."""
    assert sanitize_output(42) == 42


def test_sanitize_none_passthrough():
    """U4.10b: None → passthrough sin cambios."""
    assert sanitize_output(None) is None


def test_sanitize_bool_passthrough():
    """U4.10c: bool → passthrough sin cambios."""
    assert sanitize_output(True) is True


# ── U4.11: String sin secretos → sin cambio ────────────────────


def test_sanitize_clean_string():
    """U4.11: String sin secretos → retorna sin cambios."""
    result = sanitize_output("Esto es un texto seguro sin credenciales")
    assert result == "Esto es un texto seguro sin credenciales"


# ── U4.12 (edge): Excepción → "[ERROR: output no pudo ser procesado]"


def test_sanitize_error_handling():
    """Edge: Excepción en procesamiento → mensaje de error genérico."""
    with patch("src.mcp.sanitizer.SECRET_PATTERNS", [r"("]):
        result = sanitize_output("cualquier texto")

    assert "[ERROR: output no pudo ser procesado]" in result
