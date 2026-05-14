# Sugerencias — Post-Validación Pasos 1, 3 y 4

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

---

## 🟡 Importantes (Paso 04 — Builder)

- **ID-013:** Dogfooding no verificable — Sin evidencia de que `fap agent create` se usara para validar el endpoint antes de construir AgentForm. CLI y UI llaman al mismo endpoint (`/agents`). Documentar uso en desarrollo. Ejecutar `fap agent create --dry-run` contra Supabase dev.
- **ID-014:** Criterios FULLSTACK (#19-23) verificados solo estructuralmente — Requieren ejecución live del servidor backend (puerto 8000) + frontend (puerto 3000) para verificación end-to-end. Ejecutar flujo completo: CLI create → UI save → verificar en DB.
- **ID-015:** `created_at` en `AgentResponse` es `str | None` — `agents.py:35`. Supabase siempre retorna `created_at` (columna `DEFAULT now()`). Cambiar a `created_at: str` sin `| None`.
- **ID-016:** Router `agents.py` tiene ruta base `/agents`, no `/api/agents` — El analisis-FINAL.md §3 item 9 dice `POST /api/agents` pero el router usa `prefix="/agents"`. Frontend llama `api.post('/agents', ...)`. Corregir documentación en analisis-FINAL.md para reflejar ruta real.

## 🔵 Mejoras (Paso 04 — Builder)

- **ID-017:** `ToolMultiSelect` hook click-outside repetitivo — `useEffect` + `mousedown` en cada render. Extraer a `useClickOutside` hook reutilizable.
- **ID-018:** `AgentForm` useEffect llmModel tiene deps incompletas — Línea 171: `// eslint-disable-next-line react-hooks/exhaustive-deps`. Refactor a `onValueChange` del Select directamente.
- **ID-019:** CSS de reactflow cargado eager — Línea 32: `import 'reactflow/dist/style.css'` fuera de dynamic import. Mover dentro si CSS >10KB.
- **ID-020:** Sin test unitario para `AgentForm` o `POST /agents` — El análisis-FINAL §8 define 10 casos. Añadir TP-1, TP-2, TP-3 en `tests/unit/test_agents.py`.
- **ID-021:** `ToolMultiSelect` no usa `Command` (cmdk) — Implementación custom pura. Análisis sugería `Command` + `Popover`. Evaluar migración si UX actual es insuficiente.

---

## 🟡 Importantes (Paso 05 — Template Picker)

- **ID-022:** Dogfooding no verificado (T0-C) — Sin evidencia de que `fap templates use --dry-run` se usara para validar mapeos template→agent antes de construir TemplatePicker UI. Ejecutar `fap templates use --dry-run` para los 8 templates y documentar resultados.

- **ID-023:** TypeScript `tsc --noEmit` — 2 errores en `AgentForm.tsx` (líneas 75, 207) por zodResolver type mismatch entre schema con `.default()` y tipo esperado por `useForm`. Preexistentes al Paso 05. Criterio T3 del FINAL exige "TypeScript compila sin errores en AgentForm.tsx". Corregir en Paso 04 o 05.

- **ID-023b (NUEVO):** Tests de integración — 3 FAILED + 1 ERROR en `test_3_5_latency.py` por desconexión de Supabase (`RemoteProtocolError: Server disconnected`). Infraestructura, no código. Verificar conectividad Supabase para tests de latencia. No bloquea validación de templates.

## 🔵 Mejoras (Paso 05 — Template Picker)

- **ID-024:** ~~`TemplatePicker.tsx` — `staleTime: 5 * 60 * 1000` hardcodeado (línea 68). Extraer a constante `TEMPLATE_CACHE_MS` en `constants.ts`.~~ → ✅ Corregido: `TEMPLATE_CACHE_MS` importado desde `constants.ts:18` (TemplatePicker.tsx:14,69).

- **ID-025:** ~~`TemplatePicker.tsx:220` — texto "Loading..." en botón.~~ → ✅ Corregido: `<LoadingSpinner size="sm" />` implementado (línea 225).

- **ID-026:** `BuilderLayout.tsx` — `mapTemplateToFormValues` definida como función suelta en el módulo, no exportada ni testeable aisladamente. Extraer a `dashboard/lib/template-mapper.ts` con tests unitarios.

- **ID-027:** ~~`templates_use.py` — `import uuid as _uuid` dentro de la función (lazy import).~~ → ✅ Corregido: `import uuid as _uuid` movido al top del módulo (línea 11).
