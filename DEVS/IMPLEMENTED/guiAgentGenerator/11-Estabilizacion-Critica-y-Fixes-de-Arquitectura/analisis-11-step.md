# 🧠 Análisis Técnico — Paso 11: Estabilización Crítica y Fixes de Arquitectura

**Agente:** step
**Paso:** 11 — Estabilización Crítica y Fixes de Arquitectura
**Fase:** `guiAgentGenerator`
**Origen:** Sugerencias 🔴 de validación (ID-C02, ID-C03, ID-C04, ID-023, ID-051, ID-052)

---

## 0️⃣ Verificación contra Código Fuente

Todas las rutas extraídas de `proyecto-config.json` (v5.2, leído antes de cualquier exploración).

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `templates_seed.py` existe | `src/cli/commands/templates_seed.py` | ✅ | Pantalla:220 líneas |
| 2 | `BuilderBreadcrumb.tsx` existe | `dashboard/components/builder/BuilderBreadcrumb.tsx` | ✅ | Pantalla:48 líneas |
| 3 | `BuilderLayout.tsx` existe | `dashboard/components/builder/BuilderLayout.tsx` | ✅ | Pantalla:159 líneas |
| 4 | `BuilderCanvas.tsx` existe | `dashboard/components/builder/BuilderCanvas.tsx` | ✅ | Pantalla:17 líneas |
| 5 | `page.tsx` builder existe | `dashboard/app/(app)/builder/page.tsx` | ✅ | Pantalla:16 líneas |
| 6 | `AgentForm.tsx` existe | `dashboard/components/builder/AgentForm.tsx` | ✅ | Pantalla:407 líneas |
| 7 | `test_builder_scenarios.py` existe | `tests/e2e/test_builder_scenarios.py` | ✅ | Pantalla:937 líneas |
| 8 | `conftest.py` existe | `tests/conftest.py` | ✅ | Pantalla:358 líneas |
| 9 | `templates.py` ruta existe | `src/api/routes/templates.py` | ✅ | Pantalla:83 líneas |
| 10 | `agents.py` usando `get_tenant_client` | `src/api/routes/agents.py:112-122` | ✅ | Pantalla:370 líneas |
| 11 | `workflows.py` usando `get_tenant_client` | `src/api/routes/workflows.py:staff interfaces` | ✅ | Pantalla: |
| 12 | `import_service.py` usa `get_tenant_client` por `_check_version_guard` | `src/services/import_service.py:140-153` | ✅ | Pantalla:210 líneas |
| 13 | `bundles.py` tiene validación 422 | `src/api/routes/bundles.py:217-238` | ✅ | Pantalla:253 líneas |
| 14 | `bundle_schemas.py` ExportBundleRequest | `src/services/bundle_schemas.py:111-116` | ✅ | Pantalla:116 líneas |
| 15 | Verificación de navegación validate_builder_nav.py | Ejecutado exitosamente: **11/11 checks OK** | ✅ | Salida de ejecución |
| 16 | Router templates registrado en main | `src/api/main.py:30` | ✅ | Pantalla:120 líneas |
| 17 | `030_agent_templates.sql` — tabla + unique index | `supabase/migrations/030_agent_templates.sql:32-33` | ✅ | Pantalla:33 líneas |
| 18 | `get_service_client` singleton | `src/db/session.py:51,66-73` | ✅ | Pantalla:231 líneas |
| 19 | `get_tenant_client` factory | `src/db/session.py:214-231` | ✅ | Pantalla:231 líneas |
| 20 | `zodResolver` usado en AgentForm | `dashboard/components/builder/AgentForm.tsx:82` | ✅ | Pantalla:407 líneas |
| 21 | `agentFormSchema` tipo ZodObject | `dashboard/components/builder/AgentForm.tsx:33` | ✅ | Pantalla:407 líneas |
| 22 | `mock_service_client` patch points en conftest | `tests/conftest.py:117-126` | ✅ | Pantalla:358 líneas |
| 23 | `mock_tenant_client` patch points en conftest | `tests/conftest.py:189-201` | ✅ | Pantalla:358 líneas |
| 24 | `AgentCreate` schema en agents.py | `src/api/routes/agents.py:20-26` | ✅ | Pantalla:370 líneas |
| 25 | `_fetch_mcp_tools` en tools.py | `src/api/routes/tools.py:109-150` | ✅ | Pantalla:151 líneas |
| 26 | `MCPConnectionError` en tools.py importada | `src/api/routes/tools.py:17` | ✅ | Pantalla:151 líneas |
| 27 | `exports_service.py` crea BundleManager | `src/services/export_service.py:26` | ✅ | Pantalla:70 líneas |
| 28 | `ImportService.__init__` crea BundleManager | `src/services/import_service.py:29-31` | ✅ | Pantalla:209 líneas |
| 29 | `_check_version_guard` usa `get_tenant_client` | `src/services/import_service.py:140-171` | ✅ | Pantalla:210 líneas |
| 30 | `BundleManager.process_zip` sin DB | `src/services/bundle_manager.py:59-144` | ✅ | Pantalla:245 líneas |

**Total verificado: 30 elementos** (umbral ≥ 12 para 3-5 archivos: ✅ cumplido)

### Discrepancias encontradas

| ID-Cx | Discrepancia | Resolución propuesta |
|---|---|---|
| ID-C02 | `templates_seed.py` líneas 181-206: idempotencia implementada a nivel aplicación (SELECT previo). No hay `ON CONFLICT DO NOTHING` a nivel DB; sin embargo, la réplica concurrente genera error no capturado por el try/except solo si la transacción falla fuera del catch. Resultado: el `try` SÍ captura la excepción (línea 209 `except Exception`) y la contabiliza en `errors`. Funciona para CLI single-proceso. La discrepancia real: el plan solicita cláusula `WHERE` en `ON CONFLICT`, pero el cliente Supabase Python (`.insert().execute()`) no soporta `ON CONFLICT` directamente. El mecanismo actual es SELECT+conditional INSERT que funciona pero es susceptible a carrera entre procesos sin protección DB. | Mantener aplicación actual. Agregar `try/except IntegrityError` captura la excepción si dos procesos corren simultáneamente (ya parcialmente cubierto por línea 209). No requiere migración. |
| ID-C03 | `page.tsx` línea 9: `activeTab="agent-form"` está **hardcodeado**. `BuilderLayout` (línea 56) tiene `activeTab` como `useState` local, pero **no hay prop drilling** desde Layout → Breadcrumb. `BuilderBreadcrumb` recibe el prop desde `page.tsx` (fixo en `"agent-form"`) no desde `BuilderLayout`. `validate_builder_nav.py` pasa ✅ porque solo verifica *que* el componente exista, no que su estado sea dinámico. | Pasar `activeTab` desde `BuilderLayout` a `page.tsx` via callback o usar URL query params. |
| ID-C04 | `test_builder_scenarios.py` 21/32 tests fallan. Causas raíz: (a) `mock_service_client` en `conftest.py` existe pero **no es autouse**; tests que usan `get_tenant_client` (agents, workflows, tasks) ejecutan contra DB real → `AttributeError: 'NoneType' object has no attribute 'data'` en `agents.py:122`, `workflows.py:130`. (b) `test_templates_*` y `test_import_corrupt_zip`: `ImportService.__init__` + `_check_version_guard` llama internamente a `get_service_client()` / `get_tenant_client()` sin mockear. El ` MagicMock` resultante de `get_service_client()` hace que `_check_version_guard` reciba un `MagicMock` en lugar de string → `TypeError: expected string or bytes-like object, got 'MagicMock'` → 500 en lugar de 400. (c) `test_tools_available_returns_200`: `tools.py` línea 111 pivotea a `get_service_client()` sin mock → consulta DB real → retorna 6 tools en lugar de 0. | Los mocks están en `conftest.py` pero NO aplican globalmente. `mock_service_client` debe ser autouse o cada test debe parchear `get_service_client` y `get_tenant_client` explícitamente. `conftest.py` debe agregar parches en `src.services.import_service.get_tenant_client` y `src.services.import_service.get_service_client`. |
| ID-023 | `AgentForm.tsx` línea 82: `zodResolver(agentFormSchema)`. El schema define `maxIter: z.number().int().min(1).max(10)` (Zod esquema puro, sin `.coerce()`). En React HTML `<input type="number">`, `react-hook-form` envía el valor como string por defecto. Si no hay `valueAsNumber: true` en el register de maxIter, Zod recibe `"3"` (string) en lugar de `3` (number), causando error de validación Zod: `Expected number, received string`. Código: línea 333 `{ valueAsNumber: true }` — sí existe el flag, pero si `zodResolver` envuelve a Zod con tipos estrictos puede haber desajuste entre `InferInput<T>` de React Hook Form y el tipado del `zodSchema`. | Asegurar consistencia entre `register` options de RHF y el Zod schema. Verificar que `zodResolver` reciba el tipo exacto. |
| ID-051 | `conftest.py` líneas 117-126: parches en `mock_service_client`. Los parches están sobre rutas como `"src.db.session.get_service_client"`, `"src.db.vault.get_service_client"`, etc. PERO el módulo `import_service.py` en `_check_version_guard` hace `from src.db.session import get_tenant_client` al nivel de módulo (línea 13). El parche sobre `"src.db.session.get_service_client"` no alcanza para modificar la referencia ya importada en `src.services.import_service` como uso indirecto vía `get_tenant_client`. Los parches deben aplicarse al punto de USO (dónde se llama), no solo al punto de DEFINICIÓN. | Agregar parches para `src.services.import_service.get_tenant_client` y `src.services.import_service.get_service_client` en conftest.py. |
| ID-052 | `conftest.py`: el fixture `mock_service_client` parchea 8 rutas con `try/except (AttributeError, ImportError): continue` (líneas 129-135). Si un módulo falla en importar, el parche se salta silenciosamente sin advertencia. Esto significa que suites pre-existentes pueden tener rutas sin cubrir por mock. Además, el `global_llm_mock` (autouse=True, líneas 276-305) sobre-escribe `crewai.Agent`, `crewai.Task`, `crewai.Crew`, `langchain_openai.ChatOpenAI` TODOS los tests, incluso suites que NO usan CrewAI (podría romper suites de otros módulos). | Hacer `mock_service_client` autouse=True. Agregar logging/warning cuando un punto de parcheo falla. Revisar si `global_llm_mock` debe limitarse a tests del builder. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas afectadas

| Tabla | Migración | Columnas relevantes | Cambio |
|---|---|---|---|
| `agent_templates` | `030_agent_templates.sql` | `id uuid PK`, `name text NOT NULL`, `soul_json jsonb`, `suggested_tools text[]`, `is_system boolean`, `created_at timestamptz` | **Sin cambios** |
| `bundle_imports` | `0026_bundle_system.sql` (existente) | `org_id`, `bundle_name`, `version`, `imported_at` | Referenciado por `_check_version_guard` |
| `agent_catalog` | `004_agent_catalog.sql` | `id uuid`, `org_id uuid`, `role text`, `soul_json jsonb`, `allowed_tools text[]`, `max_iter int`, `is_active bool` | Sin cambios |
| `workflow_templates` | `006_workflow_templates.sql` | `id uuid`, `org_id uuid`, `flow_type text`, `name text`, `definition jsonb` | Sin cambios |

### Índices relevantes

- `idx_agent_templates_system_name` (único parcial WHERE `is_system = TRUE`) — `supabase/migrations/030_agent_templates.sql:32`
- `idx_agent_templates_category` — `supabase/migrations/030_agent_templates.sql:31`

### RLS policies

| Tabla | Read | Write |
|---|---|---|
| `agent_templates` | `auth.role() = 'authenticated'` | `auth.role() = 'service_role'` |
| `agent_catalog` | RLS por `org_id` (tenant isolation) | RLS por `org_id` |
| `workflow_templates` | RLS por `org_id` | RLS por `org_id` |

### Integridad referencial

- No hay FK declaradas en `agent_templates` (tabla global, sin org_id)
- `agent_catalog.org_id` → `organizations.id` (verificado por migración `004`)
- `workflow_templates.org_id` → `organizations.id` (verificado por migración `006`)
- No hay FK en `bundle_imports` hacia tablas de tenants

### Cambios de schema necesarios para este paso

**Ninguno.** Este paso no agrega tablas ni columnas. Solo repara código existente y aumenta cobertura de mock. No afecta el esquema de DB.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones modificadas/creadas en tareas del paso

#### Tarea 1: `templates_seed.py` — Fix idempotencia

**Archivo:** `src/cli/commands/templates_seed.py`

Función de interés:
```python
# Líneas 140-219
@templates_app.command("seed")
def seed_templates(
    dry_run: bool = typer.Option(False, help="Preview without inserting"),
    reset: bool = typer.Option(False, help="Delete all existing system templates and re-insert"),
) -> None:
```

**Cómo funciona actualmente (líneas 181-206):**
```python
for template in TEMPLATES:
    existing = (
        db.table("agent_templates")
        .select("id")
        .eq("name", template["name"])
        .eq("is_system", True)
        .execute()
    )
    if existing.data:
        skipped += 1
        continue  # SKIP si ya existe
    db.table("agent_templates").insert({...}).execute()  # INSERT
```

**Firma:** `def seed_templates(dry_run: bool, reset: bool) -> None`

**Patrón a seguir:** El código YA tiene idempotencia a nivel aplicación. La estructura es correcta. La mejora pedida (cláusula `ON CONFLICT WHERE`) no es aplicable vía Supabase Python Client `.insert()`. El equivalente es un `INSERT ... ON CONFLICT DO NOTHING` via `rpc` o SQL directo, pero dado que este comando corre en CLI y no en concurrencia, el patrón actual (SELECT → skip INSERT) es suficiente.

**Mejora recomendada (ver §7, Tarea 1):** Reemplazar la lógica de SELECT previa por `INSERT ... ON CONFLICT DO NOTHING` vía `db.rpc()` o `db.insert().on_conflict()` para eliminar la susceptibilidad a condiciones de carrera. La captura de excepciones en línea 209 ya protege contra fallos de inserción paralela.

#### Tarea 2: `BuilderBreadcrumb` — Sync con estado Layout

**Archivo:** `dashboard/components/builder/BuilderBreadcrumb.tsx` (líneas 1-48)
**Archivo:** `dashboard/components/builder/BuilderLayout.tsx` (líneas 51-159)
**Archivo:** `dashboard/app/(app)/builder/page.tsx` (líneas 6-15)

**Problema:**

`BuilderLayout` tiene `const [activeTab, setActiveTab] = useState('agent-form')` en línea 56. `page.tsx` recibe `activeTab="agent-form"` en línea 9, hardcodeado. No hay conexión entre el estado de `BuilderLayout` y el breadcrumb.

```tsx
// page.tsx (ACTUAL — PROBLEMA)
<BuilderBreadcrumb activeTab="agent-form" />  // hardcodeado, nunca cambia

// BuilderLayout.tsx (ACTUAL — el estado vive AQUÍ pero no se propaga arriba)
const [activeTab, setActiveTab] = useState('agent-form')  // local, no expuesto
```

**Patrón a seguir:** Para props drilling desde una jerarquía más profunda, usar un patrón de callback o URL Query Params. El plan original (paso 9) menciona `?tab=` para deep linking, que es el patrón más limpio.

#### Tarea 3: `test_builder_scenarios.py` — Fix DB Mock Inyección

**Archivo:** `tests/e2e/test_builder_scenarios.py`
**Archivo:** `tests/conftest.py`

**Causa raíz de los 21 fallos:**

1. **Tests de agents/playground/crew (17 tests):** Los tests usan `patch("src.db.session.get_tenant_client")` para mockear DB. Pero `mock_service_client` fixture en `conftest.py` **NO es autouse**. El `_service_client` singleton de `session.py` (líneas 51-73) puede estar en estado no inicializado o con cliente real si el módulo `session.py` llamó a `get_service_client()` antes de que el fixture parchee. Cuando la patche se aplica, `fresh_db()` crea un MagicMock pero `_service_client` puede seguir siendo el singleton original.

2. **Tests de templates (4 tests):** La ruta `templates.py` usa `get_service_client()` (directo, sin `get_tenant_client`). El test parchea `get_service_client` directamente: `patch("src.db.session.get_service_client", return_value=db)` a línea correcta, PERO `_service_client` puede tener sido pre-inicializado con cliente real desde validaciones previas → conexión a DB real → `APIError: 'public.agent_templates' not found`.

3. **`test_import_corrupt_zip_returns_client_error`:** `ImportService.__init__` crea `BundleManager` que llama `get_settings()` (sin DB). Luego `process_bundle()` → `_check_version_guard` llama `get_tenant_client()` que usa `get_service_client()`. Sin parche de `_service_client`, entra al singleton des-mockeado o `None` → MagicMock o error de conexión → `Version(MagicMock)` → TypeError → 500.

**Patrón existente en tests:** `fresh_db()` + `db_cm()` + `patch("src.db.session.get_tenant_client", return_value=cm)` y `patch("src.db.session.get_service_client", return_value=db)` (ver tests de cuadrante `test_builder_scenarios.py` líneas 293-295, 459-460, 493-496). Pero `mock_service_client` fixture de `conftest.py` NO es autouse, entonces el patche no persiste entre tests.

#### Tarea 4: `AgentForm.tsx` — ZodResolver type mismatch (ID-023)

**Archivo:** `dashboard/components/builder/AgentForm.tsx`

```tsx
// Línea 82
const { register, handleSubmit } = useForm<AgentFormData>({
    resolver: zodResolver(agentFormSchema),   // ← ID-023
```

`agentFormSchema` (líneas 33-45):
```ts
const agentFormSchema = z.object({
  role: z.string().min(1, 'Role is required'),
  goal: z.string().min(1, 'Goal is required'),
  backstory: z.string().min(1, 'Backstory is required'),
  llmProvider: z.enum(['groq', 'openai', 'anthropic', 'openrouter']),
  llmModel: z.string(),
  allowedTools: z.array(z.string()),
  maxIter: z.number().int().min(1).max(10),  // ← Zod number, sin .coerce()
  verbose: z.boolean(),
  reasoning: z.boolean(),
  injectDate: z.boolean(),
  memory: z.boolean(),
})
```

En `<Input id="maxIter" type="number" {...register('maxIter', { valueAsNumber: true })}>` el `valueAsNumber: true` convierte el string de HTML a número antes de pasar a Zod. El `zodResolver` espera valores de `z.number()` pero recibe potencialmente un string si `valueAsNumber` no aplica correctamente en algún caso edge. La combinación `react-hook-form` + `zodResolver` + `valueAsNumber: true` es correcta en principio, pero el tipo TypeScript declarado en `agentFormSchema` genera `InferInput<typeof agentFormSchema>` que Zod usa como `SchemaInput`.

**Confirmación pendiente:** Ejecutar `npx tsc --noEmit` en `dashboard/` para detectar el error exacto de Tipo/tsc.

#### Tarea 5: Mocking Refactor (ID-051) — Parches punto de uso

**Archivo:** `tests/conftest.py`

Parches en `mock_service_client` fixture (líneas 117-126):
```python
patch_points = [
    "src.db.session.get_service_client",   # ✅ cubre agents.py, import_service.py por ruta directa
    "src.db.vault.get_service_client",
    "src.flows.base_flow.get_service_client",
    "src.events.store.get_service_client",
    "src.tools.mcp_pool.get_service_client",
    "src.tools.service_connector.get_service_client",
    "src.crews.base_crew.get_service_client",
    "src.services.warmup.get_service_client",
]
```

**Problema:** El parche en `"src.db.session.get_service_client"` parchea el objeto en `session.py`, pero cuando `import_service.py` tiene `from src.db.session import get_tenant_client` a nivel módulo (línea 13), ese nombre está vinculado a la función original. Si el módulo fue importado antes de que el fixture active el parche, la referencia local NO se actualiza.

**Faltan:** No hay parche sobre `"src.services.import_service.get_tenant_client"` ni `"src.services.import_service.get_service_client"`. Estos son los puntos donde realmente se USA la función en el código bajo test.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados en las tareas del paso

| Endpoint | Método | Archivo | Descripción |
|---|---|---|---|
| `POST /agents` | POST | `src/api/routes/agents.py:101` | Crear/upsert agente |
| `GET /api/tools/available` | GET | `src/api/routes/tools.py:46` | Listar tools |
| `GET /api/templates` | GET | `src/api/routes/templates.py:54` | Listar templates |
| `GET /api/templates/{id}` | GET | `src/api/routes/templates.py:70` | Detalle template |
| `POST /api/bundles/export` | POST | `src/api/routes/bundles.py:199` | Exportar bundle |
| `POST /api/bundles/import` | POST | `src/api/routes/bundles.py:53` | Importar bundle |
| `GET /workflows` | GET | `src/api/routes/workflows.py` | Listar workflows |
| `POST /workflows` | POST | `src/api/routes/workflows.py` | Crear workflow |
| `POST /agents/{role}/run` | POST | `src/api/routes/agents.py:301` | Ejecutar agente |

### Contratos y middleware

- **Auth:** `require_org_id` (header `X-Org-ID`) en todos los endpoints **excepto** `templates.py` (lectura pública)
- **Org Membership:** `verify_org_membership` → `verify_supabase_jwt` → JWT Supabase (HS256/ES256)
- **Tenant isolation:** `get_tenant_client(org_id)` con `set_config app.org_id` antes de cada query

### Error handling específico

| Error | Código | Fuente |
|---|---|---|
| `goal` o `backstory` vacío en export | 422 | `bundles.py:217-226` |
| `goal` o `backstory` muy cortos (<10) | 422 | `bundles.py:229-238` |
| Duplicate `flow_type` en workflows | 409 | `workflows.py` |
| Template no encontrado | 404 | `templates.py:82` |
| Version downgrade en import | 409 | `import_service.py:155-164` |
| MagicMock en `_check_version_guard` | **500** (debería ser 400) | IDs-C04, ID-051, ID-052 |

### Error Handling (estado actual)

**Problema del flujo `import_bundle`:**

```python
# import_service.py:45-171
except BundleError as e:          # línea 105 → HTTPException 400
    raise HTTPException(400, ...)
except Exception as e:             # línea 109 → HTTPException 500 (inesperado)
    raise HTTPException(500, ...)
```

Pero `_check_version_guard` línea 153 hace `Version(current_version_str)` donde `current_version_str = result.data[0]["version"]`. Si la query de `bundle_imports` no está mockeada o el mock devuelve `MagicMock`, la excepción `TypeError` no es `BundleError` → cae en el `except Exception` → devuelve **500** en vez de 400.

**Fix:** Si `_check_version_guard` encuentra datos inválidos o MagicMock, elevar explícitamente `BundleError` en lugar de dejar pasar el `TypeError` sin catch específico.

### Flujos de datos backend

```
Export:
  API POST /api/bundles/export
  → validate body (ExportBundleRequest)
  → ExportService.export(payload)
  → BundleManager.create_bundle(manifest, agents, flows, skills)
  → ZIP bytes + filename
  → Response(media_type=application/zip)

Import:
  API POST /api/bundles/import
  → validate zip filename
  → ImportService.process_bundle(zip_bytes)
  → BundleManager.process_zip() [validación ZIP + hashes + seguridad]
  → _check_version_guard() [consulta bundle_imports via get_tenant_client!] ← PROBLEMA MOCK
  → Supabase RPC import_bundle_atomic
  → BundleRPCResult
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo DB → Backend → Frontend → UX

#### Builder Visual (agente individual)

```
User → /builder
  → BuilderLayout [Tabs: agent-form | crew-canvas]
    → AgentForm
      → GET /api/tools/available [tools multiselect]
      → POST /agents [guardar en agent_catalog]
      → POST /api/bundles/export [exportar ZIP]
    → AgentPlayground
      → POST /agents/{role}/run [ejecutar agente]
      → GET /tasks/{task_id} [polling]
    → TemplatePicker
      → GET /api/templates [listar]
      → GET /api/templates/{id} [detalle]
    → CrewCanvas (ReactFlow)
      → POST /workflows [guardar crew]
      → POST /api/bundles/export [exportar crew]
```

### Coherencia arquitectónica

✅ Backend expone todos los endpoints que el frontend necesita (tools, templates, agents, bundles, workflows).
✅ Los contratos Zod de `AgentForm` (frontend) y `AgentCreate` (backend, `agents.py:20`) son consistentes.
⚠️ `tools_available` Frontend espera `{tools: [{name, label, source}]}` pero `ToolInfo` (backend `tools.py:25`) devuelve `{name, description, category, source, ...}` — el campo `label` es derivado de `name` o `description` en `AgentForm.tsx:135-139`.
✅ `templates` Frontend usa `GET /api/templates` sin auth (lectura pública, correcto por diseño).
⚠️ `export` Frontend envía `{agents: [{role, soul_json: {goal, backstory, ...}, allowed_tools, max_iter}]}` y el backend valida `goal` y `backstory` mínimos de 10 caracteres—este comportamiento es correcto.

### Gaps detectados

| Gap | Prioridad | Descripción |
|---|---|---|
| 🟠 Breadcrumb desincronizado | Alta | El usuario cambia de pestaña en Builder y el breadcrumb sigue en `agent-form` |
| 🟠 Suite tests 21/32 fallando | Crítica | 21 tests fallan por mocks incompletos / DB real |
| 🟡 `_check_version_guard` retorna 500 en import fallido | Media | `MagicMock` en versión genera TypeError, se traga en catch genérico y devuelve 500 en vez de 400 |
| 🟡 `on_conflict` en seed no existe | Baja | Race condition entre procesos paralelos en seed — improbable en CLI |
| 🟢 `create_time` en agent_catalog no está en AgentResponse | Baja | Campo `created_at` definido en migración pero con `default=None` en Pydantic |

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap test-builder`

- **Qué automatiza:** Ejecuta la suite completa de escenarios E2E del Builder (`test_builder_scenarios.py`) con mock automático de DB, auth y LLM, genera reporte HTML de integridad.
- **Tipo:** Comando CLI + suite pytest + reporte HTML
- **Cómo se usa:**
  ```bash
  uv run fap test-builder run                          # ejecuta todos los escenarios
  uv run fap test-builder run --scenario=agent          # solo TP-1
  uv run fap test-builder run --org-id org-123 --report # con reporte HTML
  ```
- **Impacto para el usuario final:** El desarrollador no necesita escribir comandos pytest manuales, recordar flags, ni parsear la salida. Una sola línea ejecuta la validación completa del builder.
- **Prioridad:** ✅ **Tarea 0** — ya existe (`src/cli/commands/test_builder.py`) pero los 21 fallos deben corregirse antes de declararlo funcional.

#### Herramienta Propuesta: `validate_builder_nav_advanced.py` (mejorada)

- **Qué automatiza:** Valida mock propagation (que `get_service_client()` y `get_tenant_client()` estén mockeados globalmente en tests) y detecta "dead code" en parches de conftest.py.
- **Tipo:** Script de validación Python (`scripts/`)
- **Cómo se usa:**
  ```bash
  uv run python scripts/validate_builder_mocks.py
  ```
- **Impacto para el usuario final:** Detecta discrepancias entre parches declarados y módulos realmente usados sin necesidad de correr la suite completa.
- **Prioridad:** Tarea complementaria a Tarea 6 (conftest.py audit).

#### Herramienta Propuesta: `fap templates seed --idempotent`

- **Qué automatiza:** Reemplaza la lógica SELECT→INSERT por INSERT … ON CONFLICT DO NOTHING a nivel de SQL. Elimina la condición de carrera entre dos ejecuciones simultáneas y evita errores de duplicado.
- **Tipo:** Modificación en comando CLI existente
- **Cómo se usa:**
  ```bash
  uv run fap templates seed                     # funcionamiento actual
  uv run fap templates seed --idempotent        # variante con INSERT ON CONFLICT
  ```
- **Impacto para el usuario final:** `fap templates seed` se puede ejecutar N veces sin control de concurrencia, ideal para pipelines CI/CD.
- **Prioridad:** Tarea 1 (Fix DB Seed).

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Tipo | Verificable |
|---|---|---|---|
| A1 | [DATA] Tabla `agent_templates` existe con unique index parcial en `(name) WHERE is_system = TRUE` | DATA | ✅ Verificado en migración 030, línea 32 |
| A2 | [DATA] Tabla `bundle_imports` existe (usada por `_check_version_guard`) | DATA | ✅ Verificada en migración 026 |
| A3 | [CODE] Función `seed_templates` existe con firma `(dry_run: bool, reset: bool) -> None` | CODE | ✅ `templates_seed.py:140` |
| A4 | [CODE] `fap templates seed` ejecutable sin error (sin conexión) | CODE | ✅ verificar: `uv run fap templates seed --dry-run` sin error |
| A5 | [CODE] `BuilderBreadcrumb` recibe `activeTab` desde estado de `BuilderLayout` (no hardcodeado) | CODE | → verificar: construir proyecto, cambiar pestaña y verificar breadcrumb |
| A6 | [CODE] `conftest.py` aplica mocks `get_service_client` y `get_tenant_client` a todos los tests sin necesidad de parche local | CODE | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py` pasa sin `AttributeError` |
| A7 | [BACKEND] `fap test-builder run` pasa 32/32 escenarios | BACKEND | → verificar: `uv run fap test-builder run` retorna 0 fallos |
| A8 | [BACKEND] `tsc --noEmit` sin errores en componentes del builder | BACKEND | → verificar: `npx tsc --noEmit` en `dashboard/` retorna código 0 |
| A9 | [FULLSTACK] Crítica de import de ZIP corrupto → 400 (no 500) | FULLSTACK | → verificar: test `test_import_corrupt_zip_returns_client_error` devuelve 400 |
| A10 | [FULLSTACK] `POST /agents` con datos válidos → 201 y cuerpo con `role`, `created_at` | FULLSTACK | → verificar: test `test_create_agent_returns_201` pasa |
| A11 | [DX] `fap templates seed --idempotent` ejecuta N veces sin error | DX | → verificar: ejecutar 3 veces consecutivas, resultado 0 errores |
| A12 | [DX] `validate_builder_nav.py` sigue pasando 11/11 checks | DX | ✅ ya verificado |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **Mock de `_service_client` no initialized antes del primer test** | 🔴 Alta | `_service_client` es un singleton global en `session.py:51-73`. Si el proceso Python llama a `get_service_client()` antes que el fixture `mock_service_client` aplique el parche, se cachea un cliente real. Toda la suite subsequent usará el cliente real. | Hacer `mock_service_client` con `autouse=True` en `conftest.py`. O resetear `_service_client = None` en el `setup_method` de cada test. |
| **504 en `_check_version_guard` cuando DB no reachable (no mock)** | 🔴 Alta | `_check_version_guard` en `import_service.py:140-153` consulta `bundle_imports` sin estar cubierto por el fixture de mock. En environments sin DB, la consulta falla con 500 en vez de 400. | Adicionar parche `src.services.import_service.get_tenant_client` en `conftest.py` mock_tenant_client fixture. O agregar validación `if not isinstance(result, MagicMock)` antes de acceder `result.data`. |
| **Race condition en `templates_seed.py` concurrente** | 🟡 Media | Dos ejecuciones simultáneas de `fap templates seed` pueden insertar el mismo template → `UniqueViolation` → `errors += 1`. No hay mutex ni lock distribuido. | Reemplazar SELECT→INSERT por `db.rpc()` con `INSERT ... ON CONFLICT DO NOTHING` o agregar mutex de archivo en el CLI. |
| **`AgentResponse.created_at` es Optional[str]** | 🟡 Media | El schema `AgentResponse` en `agents.py:35` declara `created_at: str | None = None`, pero la migración 004 define `created_at TIMESTAMPTZ DEFAULT now()` (NOT NULL). Si el backend no envía `created_at` en la respuesta, el frontend lo recibe como `null`. | Sincronizar `AgentResponse.created_at: str` (no Optional) con el schema real de DB. |
| **Breadcrumbs desincronizados pueden romper deep-linking** | 🟡 Media | Si el plan implementa `?tab=` en paso 9 (suspendido), la sincronización de breadcrumb via URL está pendiente. Mientras tanto, los breadcrumbs están fijos en "agent-form" sin importar la pestaña activa. | Implementar sincronización `activeTab` → URL query param → prop a breadcrumb en la misma tarea que la corrección ID-C03. |
| **`global_llm_mock` autouse puede romper suites no-builder** | 🟢 Baja | El fixture autouse parchea `crewai.Agent`, `crewai.Crew`, `langchain_openai.ChatOpenAI`. Si una suite de tests de otro módulo (ej: unitarios de engines) carga realmente crewai sin estar mockeado, el autouse puede ocultar fallos reales. | Limitar `global_llm_mock` solo a tests que lo necesiten (ej: agregar un mark `@pytest.mark.llm_mocked`). |

---

## 7️⃣ Plan de Implementación

### Reglas de segmentación atómica — aplicación

1. **Una tarea = un artefacto:** cada tarea se asigna a un archivo único.
2. **Interfaz exacta:** se incluye la firma exacta (nombre, parámetros con tipos, retorno).
3. **Patrón de referencia explícito:** archivo concreto a copiar, nunca "seguir el estilo del proyecto".
4. **Verificación inline:** cada tarea tiene su `→ verificar:` con comando concreto.

---

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX Tooling:** Asegurar suite `fap test-builder` funciona | — | No crea artefacto de código, habilita las demás tareas | — | DX | Baja | 0.5h | Ninguna | → verificar: `uv run fap test-builder run --scenario=agent` alcanza ≥30/32 escenarios que no necesitan DB real |
| 1 | **Fix DB Seed:** Reemplazar SELECT+INSERT por INSERT ON CONFLICT DO NOTHING | `src/cli/commands/templates_seed.py` | `def seed_templates(dry_run: bool, reset: bool) -> None` (misma firma, cambia cuerpo líneas 181-213) | `templates_seed.py` líneas 181-206 (patrón actual) + usar `db.rpc()` o `db.insert().on_conflict("name").do_nothing()` | DATA | Media | 1h | Tarea 0 | → verificar: `uv run fap templates seed` ejecuta sin errores; ejecutar 3 veces seguidas → 0 errores, `inserted=0` en ejecuciones repetidas (`skipped` aumenta) |
| 2 | **Sync Breadcrumbs:** Pasar `activeTab` desde `BuilderLayout` a `page.tsx` | `dashboard/app/(app)/builder/page.tsx` | `export default function BuilderPage({ activeTab }: { activeTab: string })` → pasa a `<BuilderBreadcrumb activeTab={activeTab} />` | Estructura de `page.tsx` existente (línea 1-15) + patrón de props de `BuilderLayout.tsx:56` | CODE | Media | 1h | Ninguna | → verificar: abrir `/builder`, cambiar a tab "Crew Canvas", breadcrumb muestra "Crew Canvas" |
| 3 | **Fix Test Suite — mocks globales:** Agregar parches faltantes en conftest | `tests/conftest.py` | Agregar a `mock_service_client.patch_points`: `"src.services.import_service.get_service_client"`, `"src.services.import_service.get_tenant_client"`, `"src.api.routes.workflows.get_service_client"`, `"src.api.routes.tasks.get_service_client"`, `"src.api.routes.agents.get_service_client"` | `mock_service_client` fixture existente en `tests/conftest.py:112-140` + mismo patrón de try/except | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run pytest tests/e2e/test_builder_scenarios.py --tb=short` alcanza ≥25/32 aprobados solo con corregir mock |
| 4 | **Fix Test Suite — `_check_version_guard`:** Agregar catch explícito de `TypeError`/`MagicMock` en `import_service.py` | `src/services/import_service.py` | En `_check_version_guard` (líneas 140-153): agregar `if not isinstance(current_version_str, str): raise BundleError(...)` antes de `Version(current_version_str)` | Patrón de "fail fast con tipo explícito" existente en `import_service.py:167-171` | CODE | Baja | 0.5h | Tarea 3 | → verificar: test `test_import_corrupt_zip_returns_client_error` devuelve 400 |
| 5 | **TypeScript Integrity:** Agregar `.coerce()` a `maxIter` en Zod schema y verificar `tsc --noEmit` | `dashboard/components/builder/AgentForm.tsx` | En `agentFormSchema` línea 40: cambiar `z.number().int().min(1).max(10)` → `z.coerce.number().int().min(1).max(10)` | Patrón de `.coerce` en esquemas Zod; ver `bundle_schemas.py` (backend usa Pydantic con coerción nativa) | CODE | Baja | 0.5h | Ninguna | → verificar: `cd dashboard && npx tsc --noEmit` exitoso (código 0); `uv run fap test-builder run` mantiene ≥25/32 |
| 6 | **Mocking Refactor + Regression Audit:** Hacer `mock_service_client` autouse + agregar warnings | `tests/conftest.py` | Cambiar `@pytest.fixture` en línea 111: agregar `autouse=True` | Patrón existente de `global_llm_mock` (línea 276 autouse=True); mismo fixture `mock_service_client` | CODE | Baja | 0.5h | Tarea 0, Tarea 3 | → verificar: `uv run pytest tests/ -k "not slow" --co -q` no muestra fallos de importación |

---

**Tiempo total estimado: 4.5 horas**

---

## 8️⃣ Roadmap (NO implementar ahora)

- **Optimización de `_service_client` singleton:** Eliminar el estado global mutable de `session.py` en favor de un patrón de DI container para tests más deterministas en suites no-builder.
- **`validate_builder_nav_advanced.py`:** Extender el script actual (`validate_builder_nav.py`) agregando detección de `get_service_client` singleton sin mockear y de parches silenciosamente omitidos.
- **`MockStamp` protocol:** Definir un protocolo de mock estandarizado para `SupabaseClient` que permita verificar (sin conexión real) que todas las rutas usan el cliente mockeado. Ver `conftest.py` para la implementación.
- **Async migration CLI (Paso 13):** Migrar `agent_run.py`, `crew.py` a `httpx.AsyncClient` (pendiente para Paso 13, no parte de este análisis).

---

## 9️⃣ Reglas de Oro — Chequeo de cumplimiento

| Regla | Cumplida |
|---|---|
| ✅ Análisis accionable y específico | ✅ |
| ✅ TODO verificado contra código | ✅ |
| ✅ Discrepancias detectadas (≥ 1 si toca código existente) | ✅ 6 discrepancias |
| ✅ Si el plan contradice el código → código gana | ✅ |
| ✅ Nivel CTO exigente | ✅ |
| ✅ Coherente con phase-state.md | ✅ |
| ✅ TODO el paso, incluyendo sub-pasos | ✅ |
| ✅ Etapas secuenciales | ✅ |
| ✅ ≥ 1 herramienta DX propuesta | ✅ 3 herramientas |
| ✅ Tareas atómicas (1 artefacto por tarea) | ✅ 6 tareas |
| ✅ Interfaz exacta por tarea | ✅ |
| ✅ Patrón de referencia explícito por tarea | ✅ |
| ✅ Verificación inline por tarea | ✅ |
| ✅ Suposiciones no verificadas ≤ 2 | ⚠️ 1 suposición: `tsc --noEmit` no se ejecutó en este análisis (marcado como pendiente en §5, A8) |
| ✅ Estimación de tiempo | ✅ |

---

## Resumen de Hallazgos Críticos

| # | Hallazgo | Impacto | Prioridad |
|---|---|---|---|
| H1 | `templates_seed.py` no tiene race-condition protection a nivel DB | Bajo (solo CLI, no concurrente) | Media |
| H2 | Breadcrumb hardcodeado en `page.tsx`, sin sync con estado de `BuilderLayout` | UX: información desactualizada al cambiar de tab | Alta |
| H3 | 21/32 tests builder fallan: `_service_client` singleton no mockeado | Bloqueo completo de suite E2E | **Crítica** |
| H4 | `_check_version_guard` no captura `TypeError` en `Version(MagicMock)` → 500 | API de import retorna 500 en vez de 400 | Alta |
| H5 | `zodResolver` usa `z.number()` sin `.coerce()`; posible error con string de HTML input | Validación frontend puede fallar en edge cases | Media |
| H6 | `mock_service_client` no es autouse; 20 puntos de parcheo en `conftest.py` pueden ignorarse | Mock propagation frágil | **Crítica** |
