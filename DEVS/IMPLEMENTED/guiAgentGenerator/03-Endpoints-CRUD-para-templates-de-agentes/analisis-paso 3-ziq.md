# 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` NO existe | grep en supabase/migrations/ | ❌ DISCREPANCIA | No matches — tabla nueva, no existe pre-implementación |
| 2 | Migración 0030 NO existe | ls supabase/migrations/ | ❌ DISCREPANCIA | Última 0029 — nueva migración requerida |
| 3 | Módulo `src/api/routes/templates.py` NO existe | ls src/api/routes/ | ❌ DISCREPANCIA | Archivo nuevo — no existe pre-implementación |
| 4 | Router `templates_router` NO registrado en `src/api/main.py` | grep templates_router src/api/main.py | ❌ DISCREPANCIA | No matches — registro nuevo requerido |
| 5 | Patrón endpoint GET /{id} existe en `agents.py` | grep "GET.*{.*_id}" src/api/routes/agents.py | ✅ VERIFICADO | agents.py:54 — @router.get("/{agent_id}/detail") |
| 6 | Patrón endpoint GET / (listar) existe en `tools.py` | grep "@router.get" src/api/routes/tools.py | ✅ VERIFICADO | tools.py:46 — @router.get("/available") |
| 7 | Patrón RLS tenant_isolation existe en `agent_catalog` | grep tenant_isolation supabase/migrations/004_agent_catalog.sql | ✅ VERIFICADO | 004_agent_catalog.sql:22-23 — POLICY con org_id::text |
| 8 | Patrón registro router existe en `main.py` | grep include_router src/api/main.py | ✅ VERIFICADO | main.py:98-112 — 13 routers registrados |
| 9 | Patrón seed script existe en `scripts/seed_system_bundles.py` | read scripts/seed_system_bundles.py | ✅ VERIFICADO | seed_system_bundles.py:14-78 — BundleManager + ImportService |
| 10 | Patrón auth `require_org_id` existe | grep require_org_id src/api/routes/tools.py | ✅ VERIFICADO | tools.py:47 — Depends(require_org_id) |
| 11 | Patrón Pydantic BaseModel existe en routes | grep "class.*BaseModel" src/api/routes/tools.py | ✅ VERIFICADO | tools.py:25-37 — ToolInfo + ToolsListResponse |
| 12 | Patrón query Supabase existe | grep "db.table" src/api/routes/tools.py | ✅ VERIFICADO | tools.py:111-117 — get_service_client() + .table() |
| 13 | Patrón select maybe_single existe en agents.py | grep maybe_single src/api/routes/agents.py | ✅ VERIFICADO | agents.py:37-45 — .select("*").eq().maybe_single() |
| 14 | Patrón HTTPException 404 existe en agents.py | grep HTTPException src/api/routes/agents.py | ✅ VERIFICADO | agents.py:48-49 — raise HTTPException(404) |
| 15 | Patrón JSONB column existe en agent_catalog | grep JSONB supabase/migrations/004_agent_catalog.sql | ✅ VERIFICADO | 004_agent_catalog.sql:11 — soul_json JSONB |
| 16 | Patrón TEXT[] column existe en agent_catalog | grep TEXT\[\] supabase/migrations/004_agent_catalog.sql | ✅ VERIFICADO | 004_agent_catalog.sql:13 — allowed_tools TEXT[] |
| 17 | Patrón is_system BOOLEAN existe en otras tablas | grep is_system supabase/migrations/ | ❌ NO VERIFICABLE | No matches — asumir patrón similar a is_active |
| 18 | Patrón seed inicial existe en otras migraciones | grep INSERT supabase/migrations/0026_bundle_system.sql | ✅ VERIFICADO | 0026_bundle_system.sql:41-50 — INSERT INTO bundle_imports |

**Discrepancias encontradas:** (cada una con resolución propuesta)
- ❌ Tabla `agent_templates` no existe → Implementar nueva migración 0030_create_agent_templates.sql
- ❌ Migración 0030 no existe → Crear archivo versionado 0030_create_agent_templates.sql
- ❌ Módulo `templates.py` no existe → Crear src/api/routes/templates.py con endpoints GET
- ❌ Router no registrado → Agregar import + include_router en src/api/main.py
- ❌ is_system pattern no verificado → Seguir patrón is_active de agent_catalog (BOOLEAN DEFAULT FALSE)

---

# 1️⃣ Análisis de Datos (ETAPA 1)

Tabla `agent_templates` nueva:
- Columnas: id UUID PK, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN
- Relación: Sin FK directas (independiente como agent_catalog)
- RLS: tenant_isolation por org_id (nuevo campo requerido)
- Índices: org_id + category (para filtro ?category=), org_id + is_system (templates predefinidos)
- Constraints: name UNIQUE por org_id (evitar duplicados), max_iter >0
- Seed: 8 templates system (Research Agent, Code Reviewer, etc.) con is_system TRUE

Integridad referencial: Ninguna (templates independientes)

RLS policies: Lectura pública para is_system TRUE, escritura solo owners (patrón tenant_isolation)

---

# 2️⃣ Análisis de Código (ETAPA 2)

Firmas requeridas:
- def list_templates(org_id: str, category: Optional[str]) -> List[TemplateResponse]
- def get_template_by_id(template_id: str, org_id: str) -> TemplateResponse

Patrones existentes → copiar:
- Patrón query: src/api/routes/tools.py:111-117 (db.table().select().eq().execute())
- Patrón auth: src/api/routes/tools.py:47 (org_id: str = Depends(require_org_id))
- Patrón Pydantic: src/api/routes/tools.py:39-43 (ToolsListResponse con tools + count)
- Patrón error 404: src/api/routes/agents.py:48-49 (HTTPException 404)

Modularidad: Módulo templates.py separado, como tools.py/agents.py

Imports: from src.api.middleware import require_org_id, from src.db.session import get_service_client

---

# 3️⃣ Análisis de Backend (ETAPA 3)

Endpoints:
- GET /api/templates — input: ?category= (opcional), output: {templates: [], count: int}
- GET /api/templates/{id} — input: path id, output: TemplateResponse completo

Middleware: require_org_id (como todos endpoints)

Flujos: DB query → Pydantic serialize → JSON response (patrón estándar FastAPI)

Contratos: Templates incluyen soul_json completo (goal/backstory/role), suggested_tools array

Error handling: 404 si template no encontrado, 403 si no pertenece a org

---

# 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

Flujo end-to-end: Frontend → GET /api/templates → mostrar en TemplatePicker → autocompletar AgentForm → POST a agent_catalog

Coherencia: Templates alimentan builder visual, consistente con Crew Studio

Inconsistencias: Sin frontend aún (Paso 4), pero contratos API definidos

DX & Tooling (OBLIGATORIO):
### Herramienta Propuesta: fap templates seed
- **Qué automatiza:** Seed inicial de 8 templates system sin script manual
- **Tipo:** CLI command
- **Cómo se usa:** fap templates seed --org-id <uuid>
- **Impacto para el usuario final:** Evita ejecutar seed_system_bundles.py manualmente post-migración
- **Prioridad:** Tarea 0 — implementar antes del seed manual

---

# 5️⃣ Criterios de Aceptación

✅ [DATA] Tabla agent_templates existe con columnas correctas + RLS aplicada
✅ [DATA] Seed contiene ≥8 templates con is_system: true
✅ [CODE] Módulo src/api/routes/templates.py existe con firmas correctas
✅ [CODE] Imports correctos (require_org_id, get_service_client)
✅ [BACKEND] GET /api/templates devuelve array de templates
✅ [BACKEND] GET /api/templates/{id} devuelve template con soul_json
✅ [BACKEND] Filtro ?category= funciona
✅ [BACKEND] Endpoint responde 200 con datos válidos
✅ [FULLSTACK] Templates accesibles vía API (contrato para builder)
✅ [DX] CLI fap templates seed ejecuta sin errores

---

# 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| RLS mal aplicada → leak templates entre orgs | Alta | Error en policy SQL | Test unitario con multi-tenant |
| Seed duplica templates system | Media | Script ejecutado múltiples veces | UNIQUE constraint en name + org_id |
| Templates sin soul_json válido → builder falla | Media | Seed data inválida | Validación Pydantic en TemplateResponse |
| Category filtro case-sensitive | Baja | SQL = vs ILIKE | Usar ILIKE para case-insensitive |

- Riesgo integración: Templates dependen de agent_catalog schema (soul_json compatible)
- Riesgo futuro: Templates como base para crews (Paso 7)

---

# 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX & Tooling: CLI seed | src/cli/commands/templates_seed.py | def run(org_id: str) -> None | src/cli/commands/tools_list.py :: tools_app.command("list") | DX | Media | 0.5h | Ninguna | → verificar: fap templates seed --help ejecuta sin errores |
| 1 | Crear migración tabla agent_templates | supabase/migrations/0030_create_agent_templates.sql | id UUID, org_id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN | supabase/migrations/004_agent_catalog.sql :: CREATE TABLE agent_catalog | DATA | Baja | 0.5h | Tarea 0 | → verificar: migrate command sin errores + tabla existe |
| 2 | Implementar módulo src/api/routes/templates.py | src/api/routes/templates.py | @router.get("/") + @router.get("/{template_id}") | src/api/routes/tools.py :: @router.get("/available") | CODE | Media | 1h | Tarea 1 | → verificar: import src.api.routes.templates sin error |
| 3 | Registrar router en src/api/main.py | src/api/main.py | include_router(templates_router) | src/api/main.py :: include_router(tools_router) | CODE | Baja | 0.25h | Tarea 2 | → verificar: grep templates_router src/api/main.py encuentra línea |
| 4 | Seed inicial 8 templates | scripts/seed_agent_templates.py | BundleManager pattern | scripts/seed_system_bundles.py :: seed_architect_bundle() | DATA | Media | 0.5h | Tarea 1 | → verificar: python scripts/seed_agent_templates.py ejecuta + 8 filas en DB |
| 5 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-4 | → verificar: criterios §5 [BACKEND] + [DX] pasan |

**Tiempo total estimado:** 3.75 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Templates editables por users (CRUD completo)
- Templates con skills asociados
- Templates community/marketplace
- AI-generated templates desde prompts
- Templates versioning (draft/published)</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-paso 3-ziq.md