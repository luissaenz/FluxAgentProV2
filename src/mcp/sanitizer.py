"""Output sanitizer — última línea de defensa para Regla R3.

Escanea cualquier output antes de retornarlo al agente/LLM buscando
patrones de secretos conocidos. Si encuentra uno, lo reemplaza con
[REDACTED]. Si el propio sanitizer falla, retorna un error genérico
(NUNCA retorna output sin sanitizar).
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    r'sk_live_[a-zA-Z0-9]+',           # Stripe live keys
    r'sk_test_[a-zA-Z0-9]+',           # Stripe test keys
    r'Bearer [a-zA-Z0-9\-._~+/]+=*',  # Bearer tokens
    r'Basic [a-zA-Z0-9+/]+=*',         # Basic auth
    r'xox[bpsa]-[a-zA-Z0-9\-]+',       # Slack tokens
    r'ghp_[a-zA-Z0-9]+',               # GitHub PATs
    r'AIza[a-zA-Z0-9\-_]+',            # Google API keys
]


def sanitize_output(data: Any) -> Any:
    """Elimina cualquier secreto filtrado en el output. Regla R3.

    Args:
        data: Puede ser str, dict, list, o cualquier tipo primitivo.

    Returns:
        El dato con todos los patrones de secretos reemplazados por [REDACTED].
        Si ocurre un error interno, retorna un mensaje de error genérico.
    """
    try:
        if isinstance(data, str):
            for pattern in SECRET_PATTERNS:
                data = re.sub(pattern, '[REDACTED]', data)
            return data
        elif isinstance(data, dict):
            return {k: sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_output(item) for item in data]
        return data
    except Exception as e:
        logger.error("Sanitizer error: %s", e)
        return "[ERROR: output no pudo ser procesado]"
