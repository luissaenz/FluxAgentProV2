# Sugerencias — Post-Validación Paso 1 y 3

## 🔴 Críticos (Paso 03 — Templates)
- **ID-C01:** ~~Tests unitarios ausentes~~ → ✅ Creado `tests/unit/test_templates.py` con 7 tests.
- **ID-C02:** Seed idempotencia rota — `upsert(on_conflict="name")` no resuelve contra índice parcial `UNIQUE(name) WHERE is_system = TRUE`. PostgreSQL exige `WHERE is_system = TRUE` en `ON CONFLICT`. Re-ejecución de seed falla. → Fix: cambiar upsert por SELECT+INSERT o usar índice UNIQUE(name) completo.

## 🟡 Importantes
- **ID-001:** Dogfooding no verificado — `fap tools list` no se usó para tareas 1..N. Usar herramienta para validación E2E del endpoint. Registrar uso en próxima iteración.

## 🟡 Importantes (Paso 03 — Templates)
- **ID-005:** ~~Sin tests unitarios para templates.~~ → Ascendido a 🔴 ID-C01
- **ID-006:** ~~Contenido seed en español.~~ → ✅ Traducido a inglés en `templates_seed.py`.
- **ID-007:** Dogfooding documentado — flujo de uso incluido en docstring de `templates_seed.py`. Ejecutar contra Supabase dev para verificar.

## 🟡 Importantes (Paso 03 — Templates) — Nuevos
- **ID-008:** ~~Posible fallo idempotencia seed~~ → Ascendido a 🔴 ID-C02
- **ID-009:** Dogfooding no verificado para Step 03. Sin evidencia de ejecución de `fap templates seed` contra Supabase. Ejecutar seed real y validar flujo E2E: seed → GET /api/templates → detail → filter.

## 🔵 Mejoras
- **ID-002:** Crear `tests/unit/test_tools_endpoint.py` para endpoint, filtros, degradado MCP.
- **ID-003:** Refactorizar CLI `_fetch_mcp_tools` para no crear nuevo event loop por llamada.
- **ID-004:** En `_fetch_mcp_tools` usar `s.get("name")` en vez de `s["name"]` para evitar KeyError si campo falta.
- **ID-010:** Añadir `try/except` explícito con `logger.exception` + `HTTPException(503)` en handlers de templates para fallos de conexión DB. Consistencia con edge case "DB inaccesible: 500 con logger.exception" del análisis.
- **ID-011:** `seed_templates` usa `typer.Option` con valor posicional `False` en vez de `default=False`. Refactor post-MVP por claridad API Typer.
- **ID-012:** Seed command usa emojis (✓ ✗) en `console.print()`. En terminales sin UTF-8 se renderizan mal. Usar `[green]OK[/green]` / `[red]FAIL[/red]` de Rich o aplicar `force_terminal=True`.
