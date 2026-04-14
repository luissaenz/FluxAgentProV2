# Análisis Sprint 5 — Expansión de Catálogo a ~226 Tools

**Agente:** qwen
**Paso:** Sprint 5 (Expansión de catálogo vía NotebookLM)
**Fecha:** 2026-04-14

---

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Seed file `data/service_catalog_seed.json` existe | `ls data/service_catalog_seed.json` → 12441 líneas | ✅ VERIFICADO | Archivo existe, 216 tools, 90 providers |
| 2 | Tabla `service_catalog` existe | `supabase/migrations/024_service_catalog.sql` L14-24 | ✅ VERIFICADO | CREATE TABLE con 12 columnas, SIN RLS |
| 3 | Tabla `service_tools` existe | `migr/024` L71-84 | ✅ VERIFICADO | CREATE TABLE con 8 columnas, SIN RLS |
| 4 | Tabla `org_service_integrations` existe | `migr/024` L27-53 | ✅ VERIFICADO | CREATE TABLE con RLS + policy `org_integration_access` |
| 5 | Import script `scripts/import_service_catalog.py` existe | `ls scripts/import_service_catalog.py` | ✅ VERIFICADO | 187 líneas, lee seed JSON, upserta providers + tools |
| 6 | Expand script `scripts/expand_catalog.py` existe | `ls scripts/expand_catalog.py` | ✅ VERIFICADO | Lee prompt1-5.txt de `docs/Sprint 2 - Expansion of Service Catalog/` |
| 7 | Prompt files 1-5 existen | `glob docs/**/prompt*.txt` → 5 archivos | ✅ VERIFICADO | En `docs/Sprint 2 - Expansion of Service Catalog/` |
| 8 | Herramienta `ServiceConnectorTool` existe | `src/tools/service_connector.py` completo | ✅ VERIFICADO | Tool genérica TIPO C con httpx, Vault, auditoría |
| 9 | Sanitizer `src/mcp/sanitizer.py` existe | `src/mcp/sanitizer.py` completo | ✅ VERIFICADO | 7 patrones regex, función `sanitize_output()` |
| 10 | `pyproject.toml` no requiere nueva dependencia para Sprint 5 | `cat pyproject.toml` → `httpx>=0.28.0` ya incluido | ✅ VERIFICADO | Sin dependencias nuevas necesarias |
| 11 | Conteo actual: 216 tools | Python one-liner sobre seed JSON | ✅ VERIFICADO | 216 tools, 90 providers únicos |
| 12 | Meta del plan: ~226 tools | `docs/plan.md` L97-105 | ✅ VERIFICADO | Ronda 2: ~88 + Ronda 3: ~88 adicionales |
| 13 | `FLOW_INPUT_SCHEMAS` en `src/api/routes/flows.py` | `grep -rn "FLOW_INPUT_SCHEMAS" src/` | ✅ VERIFICADO | Usado en `flow_to_tool.py` L35 |
| 14 | RLS pattern con `service_role` bypass | `migr/024` L45-48 | ✅ VERIFICADO | `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 15 | `src/mcp/sanitizer.py` output sanitizer | `src/mcp/sanitizer.py` L21-27 | ✅ VERIFICADO | 7 patrones: Stripe, Bearer, Basic, Slack, GitHub, Google |

**Discrepancias encontradas:**

1. ❌ **DISCREPANCIA: El plan dice "~50 tools → ~226 tools" pero el seed ya tiene 216 tools.**
   - **Evidencia:** `python3 -c "import json; data=json.load(open('data/service_catalog_seed.json')); print(len(data['tools']))"` → 216
   - **Resolución:** El catálogo ya está casi en la meta (216/226 = 96%). Sprint 5 como está definido es **casi completo**. Solo faltan ~10 tools para llegar a 226. Las rondas 2 y 3 de NotebookLM probablemente ya fueron ejecutadas (los prompt1-5.txt ya existen). **Confirmar si hay prompts adicionales o si la ronda final ya se corrió.**

2. ❌ **DISCREPANCIA: `expand_catalog.py` lee prompts de `docs/Sprint 2 - Expansion of Service Catalog/` pero el plan los menciona para Sprint 5.**
   - **Evidencia:** `expand_catalog.py` L44: `DOCS_DIR = BASE_DIR / "docs"` + busca `prompt{i}.txt` en root de docs, pero los archivos están en `docs/Sprint 2 - Expansion of Service Catalog/`
   - **Resolución:** El script tiene un bug de rutas. Busca `docs/prompt1.txt` pero los archivos están en `docs/Sprint 2 - Expansion of Service Catalog/prompt1.txt`. El script funciona porque el `DOCS_DIR` apunta a `docs/` y los prompts NO están en el root de docs. **Verificar si el script realmente funciona o si necesita corrección de ruta.**

3. ⚠️ **NO VERIFICABLE: Estado real de Supabase — no puedo verificar si las 216 tools están importadas en la DB.**
   - **Acción:** Ejecutar `python scripts/import_service_catalog.py` con `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` configurados para verificar.

---

## 1. Diseño Funcional

### Happy Path (Sprint 5 casi completo):
1. Seed file `service_catalog_seed.json` ya contiene 216 tools de 90 providers (estado actual).
2. Para llegar a ~226: investigación NotebookLM genera ~10 tools adicionales en nuevos prompts (o los prompts 1-5 ya cubren las 216).
3. `expand_catalog.py` lee prompt files, transforma tools al formato TIPO C nested, mergea con seed existente (deduplica por ID).
4. `import_service_catalog.py` inserta providers en `service_catalog` (upsert por `id`) y tools en `service_tools` (upsert por `id`).
5. Verificación de integridad confirma: ≥15 providers, tool count = expected, 0 orphan tools, 0 incomplete `tool_profile`s.
6. ServiceConnectorTool puede ejecutar cualquiera de las 216+ tools vía `tool_id`.

### Edge Cases:
- **Duplicate tool IDs:** `expand_catalog.py` usa dict con key = `tool_id.lower()` → overwrite silencioso del anterior. Si prompt5 define mismo ID que prompt1, gana prompt5.
- **Missing `tool_profile` fields:** `import_service_catalog.py` L73-80 rellena defaults (`description`, `risk_level`, `requires_approval`) si faltan.
- **Provider inconsistency:** Mismo provider con IDs diferentes (ej: `google_sheets` vs `google_sheets_api`) → se insertan como providers separados. No hay deduplicación de providers en `expand_catalog.py`.

### Manejo de Errores:
- Seed file no encontrado → `sys.exit(1)` con mensaje.
- SUPABASE_URL/SUPABASE_SERVICE_KEY no configurados → `sys.exit(1)`.
- Tool sin `tool_profile.description` → usa `tool.get("name", "")` como fallback.
- HTTP error en execution → ServiceConnectorTool retorna `Error HTTP: {status_code}`.

---

## 2. Diseño Técnico

### Componentes existentes (NO modificar):
- **`data/service_catalog_seed.json`**: Fuente de verdad del catálogo. 216 tools, 90 providers. Formato: `{"tools": [{id, name, provider, version, input_schema, output_schema, execution, tool_profile}, ...]}`.
- **`scripts/expand_catalog.py`**: Script de expansión. Lee prompts, transforma, mergea. Output: sobrescribe `service_catalog_seed.json`.
- **`scripts/import_service_catalog.py`**: Script de import. Lee seed, upserta en Supabase, verifica integridad.
- **`src/tools/service_connector.py`**: Tool runtime. Lee `service_tools` + `org_service_integrations` + Vault → ejecuta HTTP → sanitiza → audita.

### Schema de DB (verificado en migración 024):
- **`service_catalog`**: 12 columnas. `id TEXT PK`, `name`, `category`, `auth_type`, `auth_scopes JSONB`, `base_url`, `api_version`, `health_check_url`, `docs_url`, `logo_url`, `required_secrets TEXT[]`, `config_schema JSONB`. SIN RLS.
- **`service_tools`**: 8 columnas. `id TEXT PK`, `service_id TEXT FK`, `name`, `version`, `input_schema JSONB`, `output_schema JSONB`, `execution JSONB`, `tool_profile JSONB`. SIN RLS.
- **`org_service_integrations`**: 12 columnas. `id UUID PK`, `org_id UUID FK`, `service_id TEXT FK`, `status`, `secret_names JSONB`, `config JSONB`, `last_health_check`, `last_health_status`, `error_message`, `enabled_at`, `created_at`, `updated_at`. CON RLS + `UNIQUE(org_id, service_id)`.

### Transformación de tools (expand_catalog.py):
```
Raw tool (from prompt) → transform_tool() → TIPO C nested format
- tool_id/id → id (lowercase)
- provider → provider object {id, name, category, auth_type, base_url, required_secrets, auth_scopes}
- auth.type → mapped: none→api_key, api_key→{provider_id}_api_key, oauth2→{provider_id}_token, basic_auth→{provider_id}_auth_token
- execution.url → infer_base_url() → protocol + host
```

---

## 3. Decisiones

1. **No se requieren nuevas dependencias.** Sprint 5 es puramente datos (JSON + import script). `httpx` ya está en `pyproject.toml`.

2. **Corrección de ruta en `expand_catalog.py` necesaria.** El script busca `docs/prompt{i}.txt` pero los prompts están en `docs/Sprint 2 - Expansion of Service Catalog/prompt{i}.txt`. 
   - **Resolución:** Actualizar `DOCS_DIR` a `BASE_DIR / "docs" / "Sprint 2 - Expansion of Service Catalog"` o mover los prompts al root de docs.

3. **216/226 = 96% completado.** Sprint 5 es esencialmente completo. Si los prompts 1-5 ya generan 216 tools, no se necesita investigación adicional. Si la meta es exactamente 226, faltan ~10 tools de investigación NotebookLM.

---

## 4. Criterios de Aceptación

- [ ] `service_catalog_seed.json` contiene ≥226 tools únicas.
- [ ] `service_catalog_seed.json` contiene ≥90 providers únicos.
- [ ] `scripts/import_service_catalog.py` ejecuta sin errores con variables de entorno configuradas.
- [ ] Verificación de integridad pasa: ≥15 providers, tool count = expected, 0 orphans, 0 incomplete profiles.
- [ ] Todas las tools tienen `tool_profile` con `description`, `risk_level`, `requires_approval`.
- [ ] `ServiceConnectorTool` puede ejecutar al menos 3 tools de diferentes providers (ej: stripe.create_customer, gmail.send, slack.send_message).
- [ ] No hay tool IDs duplicados en el seed file.
- [ ] `expand_catalog.py` encuentra y lee los prompt files correctamente.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Bug de rutas en `expand_catalog.py`** | Script no encuentra prompts → no expande catálogo | Corregir `DOCS_DIR` a ruta correcta o mover prompts |
| **DB no sincronizada con seed** | Seed tiene 216 tools pero DB tiene menos | Re-ejecutar `import_service_catalog.py` para sincronizar |
| **Duplicate tool IDs entre prompts** | Overwrite silencioso, pérdida de data | Agregar logging de conflicts en `expand_catalog.py` |
| **Provider ID inconsistency** | Mismo servicio con IDs diferentes → providers duplicados | Agregar normalización de provider IDs (ej: `google_sheets_api` → `google`) |
| **RLS policies incorrectas** | `org_service_integrations` no accesible por service_role | Verificar política `org_integration_access` con query de prueba |
| **Secret names hardcodeados** | `required_secrets` en provider no coinciden con Vault keys | Documentar convención de naming: `{provider_id}_api_key`, `{provider_id}_token` |

---

## 6. Plan

| # | Tarea | Complejidad | Tiempo Estimado | Dependencias |
|---|---|---|---|---|
| 1 | Corregir ruta de prompts en `expand_catalog.py` | Baja | 15 min | Ninguna |
| 2 | Verificar que prompt1-5 contienen data para 216+ tools | Baja | 10 min | Tarea 1 |
| 3 | Si <226 tools, ejecutar investigación NotebookLM para generar ~10 tools adicionales | Media | 1-2h | Tarea 2 |
| 4 | Re-ejecutar `expand_catalog.py` con prompts corregidos | Baja | 5 min | Tarea 1, 2 |
| 5 | Ejecutar `import_service_catalog.py` contra Supabase | Baja | 10 min | Tarea 4, env vars |
| 6 | Verificar integridad post-import | Baja | 5 min | Tarea 5 |
| 7 | Test manual: ejecutar 3 tools vía ServiceConnectorTool | Media | 30 min | Tarea 6 |
| 8 | Documentar discrepancias pendientes y resolved | Baja | 15 min | Tarea 7 |

**Total estimado:** 2-3 horas (mayormente ya completado).

---

## 🔮 Roadmap (NO implementar ahora)

- **Dynamic tool discovery desde DB:** Actualmente `flow_to_tool.py` solo genera tools de FlowRegistry. Service tools (216+) no aparecen como MCP tools dinámicas. Para que Claude pueda ver y ejecutar las 216 tools directamente vía MCP, se necesita un `build_service_tools()` en `src/mcp/tools.py` que lea `service_tools` de DB y las registre como MCP tools.
- **Health check automation:** `org_service_integrations` tiene columnas `last_health_check` y `last_health_status` pero no hay scheduler que las actualice. `src/scheduler/health_check.py` existe pero no está conectado al lifespan de FastAPI.
- **Secret rotation:** Tokens JWT para SSE son internos; falta integración con secret manager para rotación automática (mencionado en `estado-fase.md`).
- **Tool execution streaming:** Para tools que tardan >30s (ej: reportes grandes), ServiceConnectorTool timeout de 30s puede ser insuficiente.
- **Provider deduplication:** Normalizar IDs de providers para evitar duplicados (ej: `google_sheets` vs `google_sheets_api` → ambos deberían ser `google`).
- **Tool versioning:** `service_tools.version` existe pero no hay lógica de versionado en ServiceConnectorTool. Para APIs que deprecan endpoints, se necesita soporte de versiones.
