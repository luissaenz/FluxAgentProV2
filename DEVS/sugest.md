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

---

## 🟡 Importantes (Paso 06 — Agent Playground)

- **ID-028:** Dogfooding no verificado (T0-C) — Sin evidencia de que `fap agent run` se usara para validar el flujo POST/GET antes de construir AgentPlayground. Ejecutar `fap agent run --role "test" --message "verify" --org-id <uuid>` contra backend live y documentar resultado.

- **ID-029:** ~~Tests unitarios del CLI no implementados.~~ → ✅ Corregido: `tests/unit/test_agent_run.py` con 3 tests (success, role not found, connection error). 3/3 pasan (4.31s).

## 🔵 Mejoras (Paso 06 — Agent Playground)

- **ID-030:** ~~`ToolCallInfo` definido pero no usado.~~ → ✅ Documentado con comentario `// Post-MVP: tool calls interface para cuando tool_calls se persistan`. Aceptable.

- **ID-031:** ~~`agent_run.py` usa `.replace(" ", "%20")`~~ → ✅ Corregido: `urllib.parse.quote(role, safe='')` en `agent_run.py:84`.

- **ID-032:** ~~Timeout redundante en AgentPlayground.~~ → ✅ Corregido: `isTimedOut` state + segundo useEffect eliminados. Solo queda el mecanismo en `useEffect([taskData])` con verificación `elapsed > POLLING_TIMEOUT`.

- **ID-033:** `agent_run.py` usa `httpx.Client` síncrono con `time.sleep(2)` para polling. Aceptable para CLI mono-usuario. Migrar a `httpx.AsyncClient` + `asyncio.sleep()` post-MVP.

- **ID-034:** `AgentForm.onRoleChange` dispara en cada keystroke del campo role. Debounce 300ms o usar `onBlur` post-MVP.

- **ID-035:** `ScrollArea` ref `scrollRef` apunta a `<div>` interno, no al viewport de Radix. Verificar scroll auto funcional en navegador real.

---

## 🟡 Importantes (Paso 07 — Canvas visual)

- **ID-036:** ~~Tests unitarios no ejecutables.~~ → ✅ Verificado en validación Paso 08: `uv run pytest tests/unit/` → 382/382 pasan (incluye 6 test_canvas_serialize + 8 test_crew_endpoints = 14 tests relevantes). Sin fallos.

- **ID-037:** ~~CLI `fap crew` no verificable en ejecución.~~ → ✅ Verificado en validación Paso 08: `uv run pytest tests/unit/test_crew_endpoints.py -v` → 8/8 pasan. Ruff lint limpio. Estructura correcta.

## 🔵 Mejoras (Paso 07 — Canvas visual)

- **ID-038:** `AgentPlayground.tsx:147` — warning preexistente de Paso 06 (`useEffect` missing dep `startTime`). No introducido por Paso 07 pero persiste en el proyecto. → Recomendación: Corregir en paso separado o añadir eslint-disable con comentario.

- **ID-039:** `crew.py` usa `httpx.Client` síncrono. El resto del backend es async (FastAPI, BaseCrew, `asyncio.create_task`). → Recomendación: Post-MVP migrar a `httpx.AsyncClient` + `asyncio.sleep()` para polling. Consistente con ID-033 (mismo patrón en `agent_run.py`).

- **ID-040:** ~~`CrewCanvas.tsx:226-260` — `confirmExport()` duplica lógica de auth de `fapFetch`.~~ → ✅ Corregido en Paso 08: `fapDownload()` implementado en `api.ts:54-94` como helper dedicado para descargas binarias con auth headers automáticos. `confirmExport()` eliminado de CrewCanvas. `ExportDialog.tsx:120` usa `fapDownload()`.

---

## 🟡 Importantes (Paso 08 — ExportDialog + exportación)

- **ID-041:** Dogfooding no verificado (T0-C) — Sin evidencia de que `fap bundle validate-payload` se usara para validar el contrato de payload antes de construir ExportDialog. La herramienta funciona y está registrada en CLI, pero no se puede confirmar que el implementador la usara como parte del flujo de desarrollo. → Recomendación: Ejecutar `fap bundle validate-payload --file <payload.json>` para payloads de prueba TP-10/TP-11 del FINAL y documentar resultado.

- **ID-042:** `fapDownload()` hardcodea método POST — `api.ts:73` usa `method: 'POST'` fijo. Si en el futuro se necesita GET para descarga binaria, no servirá. → Recomendación: Añadir parámetro opcional `method` con default `'POST'` en `fapDownload()`. No bloquea MVP.

- **ID-043:** `ExportDialog.tsx:112` — `agents.slice(0, 15)` hardcodeado como protección adicional al `max_length=15` de Pydantic. Duplica validación pero introduce divergencia potencial si el límite cambia en backend. → Recomendación: Extraer `MAX_EXPORT_AGENTS = 15` como constante en `constants.ts` compartida con frontend.

## 🔵 Mejoras (Paso 08 — ExportDialog + exportación)

- **ID-044:** `ExportDialog.tsx:116` — `payload.skills = []` cuando `includeSkills && enableSkills`. El array vacío no incluye skills reales (sin endpoint `GET /api/skills/available`). Correcto para MVP, pero el código sugiere funcionalidad no implementada. → Recomendación: Añadir comentario `// Post-MVP: populate from skill_catalog via GET /api/skills/available`.

- **ID-045:** `ExportDialog.tsx:92-99` — fallback de clipboard truncado a 500 chars en toast, sin textarea para copia manual completa. → Recomendación: Si `navigator.clipboard` falla, mostrar `<Textarea>` con JSON completo + botón "Copy" dentro del diálogo.

- **ID-046:** `AgentForm.tsx:399,401` — `buildSingleAgentPayload()` llamada dos veces (una para `agents`, otra para `fullGraphJson`). → Recomendación: Usar `useMemo` para calcular el payload una sola vez.

- **ID-047:** `bundle_validate_payload.py:81-91` — validación goal/backstory ≥10 chars duplica lógica del handler `bundles.py:215-238`. Riesgo de desincronización si backend cambia. → Recomendación: Importar constantes desde `bundle_schemas.py` en lugar de hardcodear.

- **ID-048:** `CrewCanvas.tsx:211-218` — `exportAgents` useMemo mapea `exportPayload.agents` sin transformación real (mismos campos). Redundante. → Recomendación: Usar `exportPayload.agents` directamente o eliminar el useMemo intermedio.
