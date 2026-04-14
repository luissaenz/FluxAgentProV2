# 🗺️ Plan de Implementación MCP — FluxAgentPro v2

> Última actualización: 2026-04-13 (post-implementación Sprint 1 + Sprint 2)

## Estado General

| Sprint | Descripción | Esfuerzo | Estado |
|--------|-------------|----------|--------|
| Sprint 1 | Prerrequisitos + MCP Server básico | 8-10h | ✅ COMPLETADO |
| Sprint 2 | Service Catalog TIPO C completo | 12-14h | ✅ COMPLETADO |
| Sprint 3 | Handlers productivos (execute_flow) | 8-10h | ⏳ SIGUIENTE |
| Sprint 4 | HITL completo + SSE | 8-10h | ⏳ PENDIENTE |
| Sprint 5 | Expansión a ~226 tools (NotebookLM) | 4-6h | ⏳ PARALELO |

**Total estimado:** 40-50h (~4-5 semanas).  
**Camino crítico:** Sprint 1 → 2 → 3 → 4. Sprint 5 es independiente.

---

## ✅ Sprint 1 — Prerrequisitos + MCP Server Básico (COMPLETADO)

**Resultado:** Claude Desktop conecta a FAP vía Stdio y ve flows + agentes.

### Implementado:
- `mcp>=1.0.0,<2.0.0` como dependencia directa en `pyproject.toml`
- `get_secret_async()` wrapper async en `src/db/vault.py` (usa `asyncio.to_thread`)
- `src/mcp/server.py` — Servidor MCP Stdio con `python -m src.mcp.server --org-id <UUID>`
- `src/mcp/config.py` — `MCPConfig` con Pydantic BaseSettings (prefijo `MCP_`)
- `src/mcp/tools.py` — 5 tools estáticas: `list_flows`, `list_agents`, `get_agent_detail`, `get_server_time`, `list_capabilities`
- `src/mcp/flow_to_tool.py` — Genera un Tool MCP por cada flow registrado (FlowRegistry + FLOW_INPUT_SCHEMAS)
- `supabase/migrations/025_agent_catalog_rls_update.sql` — RLS moderno con `service_role` bypass
- `claude_desktop_config.json` — Template de configuración (requiere valores reales)

### Pendiente de verificación:
- [ ] Arranque del servidor MCP localmente
- [ ] Conexión desde Claude Desktop con `claude_desktop_config.json` configurado
- [ ] Migración 025 aplicada en Supabase

---

## ✅ Sprint 2 — Service Catalog TIPO C (COMPLETADO Y VALIDADO)

**Resultado:** 50 tools TIPO C en DB, ServiceConnectorTool ejecutando dinámicamente, 18/18 criterios de aceptación cumplidos.

### Implementado:
- `supabase/migrations/024_service_catalog.sql` — 3 tablas (`service_catalog`, `org_service_integrations`, `service_tools`)
- `data/service_catalog_seed.json` — ~50 tools, ~20 proveedores
- `scripts/import_service_catalog.py` — Import con corrección de schemas + verificación de integridad
- `src/mcp/sanitizer.py` — Output sanitizer (Regla R3), 7 patrones regex
- `src/tools/service_connector.py` — Tool genérica TIPO C con httpx, Vault, auditoría en `domain_events`
- `src/scheduler/health_check.py` — Health check async (⚠️ no conectado a lifespan del scheduler)
- `src/api/routes/integrations.py` — 3 endpoints REST
- 6 correcciones al plan original aplicadas (RLS, httpx, decorador, domain_events, middleware, ubicación)

### Documentación:
- `docs/MCP Fase 1/analisis-FINAL.md` — Análisis unificado de 4 agentes con 7 discrepancias resueltas
- `docs/MCP Fase 1/validacion.md` — Validación 18/18 CA aprobada

---

## ⏳ Sprint 3 — Handlers Productivos (SIGUIENTE)

**Objetivo:** Claude ejecuta flows reales, consulta tareas, crea workflows vía ArchitectFlow. FAP se vuelve genuinamente útil.

### Por implementar:
- `src/mcp/handlers.py` — Lógica de ejecución real de flows (reemplaza placeholder actual)
- `src/mcp/auth.py` — Auth Bridge con PyJWT (reutiliza `_get_jwks_client()` del middleware)
- `src/mcp/exceptions.py` — Mapeo de errores internos a códigos JSON-RPC estándar
- Tools nuevas: `execute_flow`, `get_task`, `approve_task`, `reject_task`, `create_workflow`

### Dependencias:
- Requiere Sprint 1 ✅ (servidor MCP funcional)
- Se beneficia de Sprint 2 ✅ (ServiceConnectorTool disponible para ArchitectFlow)

### Prerrequisito:
- Requiere pasar por pipeline de análisis (4 agentes → unificación → FINAL) antes de implementar

---

## ⏳ Sprint 4 — HITL Completo + SSE

**Objetivo:** Aprobaciones desde Claude, agentes remotos vía SSE. El ecosistema queda cerrado.

### Por implementar:
- Servidor SSE (transporte alternativo a Stdio)
- HITL end-to-end: flujo de aprobación desde Claude con feedback en Dashboard
- MCPConfig panel en Dashboard (UI para gestionar conexiones)

### Dependencias:
- Requiere Sprint 3 (handlers de ejecución)

---

## ⏳ Sprint 5 — Expansión de Catálogo (~226 tools)

**Objetivo:** Expandir de ~50 a ~226 tools con 3 rondas de investigación NotebookLM.

### Por implementar:
- Ronda 2: ~88 tools adicionales (subcategorías existentes)
- Ronda 3: ~88 tools adicionales (nuevos proveedores)
- Re-ejecutar `scripts/import_service_catalog.py` con seed expandido

### Dependencias:
- Puede correr en paralelo desde Sprint 2 porque solo usa el import script existente
- Solo requiere investigación/prompts, no código nuevo

---

## Arquitectura y Archivos del Módulo MCP

```
src/mcp/
├── __init__.py         # ✅ Sprint 2
├── sanitizer.py        # ✅ Sprint 2 — Output sanitizer (Regla R3)
├── config.py           # ✅ Sprint 1 — MCPConfig BaseSettings
├── server.py           # ✅ Sprint 1 — Entry point Stdio
├── tools.py            # ✅ Sprint 1 — 5 tools estáticas + handler dispatch
├── flow_to_tool.py     # ✅ Sprint 1 — Flow-to-Tool translator
├── handlers.py         # ⏳ Sprint 3 — Execute flow / get task / approve
├── auth.py             # ⏳ Sprint 3 — Auth Bridge (PyJWT)
└── exceptions.py       # ⏳ Sprint 3 — Error mapping → JSON-RPC
```