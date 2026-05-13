# Sugerencias — Post-Validación Paso 1

## 🟡 Importantes
- **ID-001:** Dogfooding no verificado — `fap tools list` no se usó para tareas 1..N. Usar herramienta para validación E2E del endpoint. Registrar uso en próxima iteración.

## 🔵 Mejoras
- **ID-002:** Crear `tests/unit/test_tools_endpoint.py` para endpoint, filtros, degradado MCP.
- **ID-003:** Refactorizar CLI `_fetch_mcp_tools` para no crear nuevo event loop por llamada.
- **ID-004:** En `_fetch_mcp_tools` usar `s.get("name")` en vez de `s["name"]` para evitar KeyError si campo falta.
