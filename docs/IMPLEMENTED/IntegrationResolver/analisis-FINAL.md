# 🧠 PASO 1: IntegrationResolver — Análisis Técnico (qwen)

## 0. Verificación contra Código Fuente (OBLIGATORIA)

### Exploración del codebase

**Estructura relevante:**
- `src/flows/`: 13 archivos — `architect_flow.py` (core), `base_flow.py` (lifecycle), `dynamic_flow.py` (registro), `workflow_definition.py` (Pydantic), `workflow_guardrails.py` (validación), `registry.py` (@register_flow)
- `src/db/`: `session.py` (TenantClient, get_service_client), `vault.py` (solo lectura: get_secret, list_secrets)
- `src/tools/`: `service_connector.py` (ya lee service_tools + org_service_integrations), `registry.py` (@register_tool)
- `src/api/routes/`: `integrations.py` (endpoints GET /available, /active, /tools/{service_id})
- `supabase/migrations/`: 27 archivos — 024_service_catalog.sql (3 tablas), 002_governance.sql (secrets table), 004_agent_catalog.sql, 006_workflow_templates.sql

**Archivos clave leídos completos:**
1. `architect_flow.py` (394 líneas): Clase ArchitectFlow(BaseFlow), _run_crew L112-163 genera workflow_def → valida → persiste template → persiste agents → registra dynamic flow. NO hay llamada a IntegrationResolver.
2. `vault.py` (95 líneas): Solo 3 funciones: get_secret(), list_secrets(), get_secret_async(). NO existe upsert_secret ni store_credential.
3. `workflow_definition.py` (114 líneas): AgentDefinition.allowed_tools es list[str] (L19), sin validación contra catálogo.
4. `024_service_catalog.sql`: service_tools.id es TEXT PRIMARY KEY (formato service_id.tool_name), org_service_integrations tiene UNIQUE(org_id, service_id), status TEXT DEFAULT 'pending_setup'.
5. `service_connector.py`: Ya implementa verificación de servicio activo (L76-83) y resolución de secretos (L86-90). Patrón reusable.

**Dependencias confirmadas (pyproject.toml):**
- httpx>=0.28.0 ✅ (ya usado en service_connector)
- supabase>=2.10.0 ✅
- crewai>=0.100.0 (optional-dependencies crew) ✅
- NO hay difflib/Levenshtein como dependencia directa — Python standard library difflib disponible

### Tabla de verificación (alcance: 6-10 archivos → mínimo 18 elementos)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `service_catalog` existe | `024_service_catalog.sql` L8 | ✅ | `CREATE TABLE IF NOT EXISTS service_catalog (id TEXT PRIMARY KEY, ...)` — SIN RLS |
| 2 | Tabla `service_tools` existe | `024_service_catalog.sql` L59 | ✅ | `CREATE TABLE IF NOT EXISTS service_tools (id TEXT PRIMARY KEY, service_id TEXT, name TEXT, ...)` — SIN RLS |
| 3 | Tabla `org_service_integrations` existe | `024_service_catalog.sql` L28 | ✅ | `CREATE TABLE IF NOT EXISTS org_service_integrations` con UNIQUE(org_id, service_id), status TEXT DEFAULT 'pending_setup' |
| 4 | Tabla `agent_catalog` existe | `004_agent_catalog.sql` L6 | ✅ | `allowed_tools TEXT[] DEFAULT '{}'` — columna para tools reales |
| 5 | Tabla `workflow_templates` existe | `006_workflow_templates.sql` L6 | ✅ | `definition JSONB NOT NULL DEFAULT '{}'` — guarda allowed_tools dentro |
| 6 | Tabla `secrets` (Vault) existe | `002_governance.sql` L79 | ✅ | `CREATE TABLE IF NOT EXISTS secrets (org_id, name, secret_value)` UNIQUE(org_id, name) |
| 7 | RLS en secrets solo permite SELECT | `002_governance.sql` L92 | ❌ | `FOR SELECT USING (auth.role() = 'service_role')` — NO hay política INSERT/UPDATE |
| 8 | Función `get_service_client` existe | `src/db/session.py` L48 | ✅ | Retorna singleton Client con service_role key |
| 9 | `get_tenant_client` existe | `src/db/session.py` L166 | ✅ | Context manager con set_config RPC para RLS |
| 10 | `upsert_secret` NO existe | `grep -rn "upsert_secret" src/` | ❌ | 0 resultados. vault.py solo tiene get_secret, list_secrets, get_secret_async |
| 11 | `IntegrationResolver` NO existe | `glob src/flows/integration_resolver*` | ❌ | Archivo no creado aún |
| 12 | `ArchitectFlow._run_crew` estructura | `architect_flow.py` L112-163 | ✅ | 7 pasos: execute_architect_agent → parse → validate → ensure_unique → persist_template → persist_agents → register_dynamic |
| 13 | `allowed_tools` en AgentDefinition | `workflow_definition.py` L19 | ✅ | `allowed_tools: list[str] = Field(default_factory=list)` — sin validación contra catálogo |
| 14 | `DynamicWorkflow.register` existe | `dynamic_flow.py` L39 | ✅ | Crea subclase + registra en flow_registry._flows |
| 15 | `service_connector` ya verifica servicio activo | `service_connector.py` L76-83 | ✅ | Query a org_service_integrations WHERE status='active' |
| 16 | `service_connector` ya resuelve secretos | `service_connector.py` L86-90 | ✅ | Usa get_secret() del vault |
| 17 | Endpoint `/api/integrations/tools` existe | `integrations.py` L41 | ✅ | GET /tools/{service_id} retorna id, name, tool_profile |
| 18 | `validate_workflow` guardrails existe | `workflow_guardrails.py` importado L30 | ✅ | Se llama en architect_flow.py L135 |
| 19 | `execute_with_retry` disponible | `session.py` L25 | ✅ | Función module-level para reintentos |
| 20 | `BaseFlow` con error handling | `base_flow.py` L38 | ✅ | Decorador @with_error_handling marca state como FAILED |
| 21 | httpx disponible | `pyproject.toml` L23 | ✅ | `httpx>=0.28.0` en dependencies |
| 22 | `ALLOWED_MODELS` en guardrails | `workflow_guardrails.py` importado en architect_flow L158 | ✅ | Usado en prompt del LLM para restringir modelos |

### Discrepancias encontradas

**1. ❌ Vault sin escritura — upsert_secret NO existe y RLS lo bloquea**
- Evidencia: `vault.py` tiene solo funciones de lectura. Migración `002_governance.sql` L92: política `FOR SELECT` únicamente.
- Impacto: IntegrationResolver.store_credential() fallará sin migración RLS + función de escritura.
- **Resolución:** 
  - (a) Nueva migración: añadir política `FOR INSERT/UPDATE` en `secrets` para `service_role`.
  - (b) Añadir `upsert_secret(org_id, name, value)` a `vault.py` usando `get_service_client().table("secrets").upsert(...)`.

**2. ❌ IntegrationResolver no existe — archivo nuevo requerido**
- Evidencia: `glob src/flows/integration_resolver*` → 0 resultados.
- **Resolución:** Crear `src/flows/integration_resolver.py` con clase IntegrationResolver + dataclass ResolutionResult.

**3. ⚠️ Fuzzy match plan vs reality — service_tools.id usa formato `service_id.tool_name`**
- Evidencia: `024_service_catalog.sql` L59: `id TEXT PRIMARY KEY`. En `service_connector.py` L64: busca por `tool_id` directo.
- Plan sugiere buscar por `id ILIKE '%google_sheets%'` — esto funciona pero el formato `google_sheets.read_spreadsheet` no matchea `google_sheets_read` del LLM.
- **Resolución:** Estrategia de matching en 3 niveles:
  - Nivel 1: Exact match en `id` (ej: `gmail.send_email` == `gmail.send_email`)
  - Nivel 2: Extraer service_id de la tool alucinada → filtrar service_tools por service_id → keyword match en name
  - Nivel 3: ILIKE en name + service_id combinado
  - Si nada matchea → not_found

**4. ⚠️ ArchitectFlow no tiene mecanismo de pausa para resolución**
- Evidencia: `architect_flow.py` _run_crew es lineal — no verifica is_ready antes de persistir. BaseFlow tiene request_approval() pero ArchitectFlow no lo usa para este caso.
- Plan asume que si is_ready == False, "retornar al usuario" — pero ArchitectFlow actualmente persiste sin chequear.
- **Resolución:** Insertar llamada al resolver entre validate_workflow (L135) y persist_template (L141). Si not ready, retornar dict con resolution result en vez de continuar.

**5. ⚠️ No hay tabla org_tools o similar para tools activas por org**
- Evidencia: `024_service_catalog.sql` — service_tools es global sin RLS. org_service_integrations vincula org a servicio pero NO a tools específicas.
- Plan asume verificar "activación de tool" pero la activación es a nivel de servicio, no de tool individual.
- **Resolución:** Resolver verifica que el servicio esté activo (status='active' en org_service_integrations). Todas las tools del servicio quedan disponibles.

---

## 1. Diseño Funcional

### Happy Path (paso completo)

1. **Input:** Usuario describe workflow ("necesito leer Google Sheets y enviar emails").
2. **LLM genera WorkflowDefinition** con allowed_tools alucinadas: `["google_sheets_read", "send_email"]`.
3. **validate_workflow** (guardrails) valida schema básico (snake_case, ciclos, roles).
4. **IntegrationResolver.resolve(workflow_def, org_id)**:
   - Extrae tools únicas de todos los agentes: `{"google_sheets_read", "send_email"}`
   - Para cada tool, busca en `service_tools`:
     - `google_sheets_read` → match fuzzy → `google_sheets.read_spreadsheet` (service_id: google_sheets)
     - `send_email` → match exacto → `gmail.send_email` (service_id: gmail)
   - Para cada service_id único, verifica en `org_service_integrations`:
     - `google_sheets`: status='pending_setup' → va a `needs_activation`
     - `gmail`: status='active' → continúa
   - Para servicios activos, verifica credenciales en Vault:
     - `gmail`: secret_names=['gmail_oauth_token'] → get_secret(org_id, 'gmail_oauth_token') → ✅ existe
   - Retorna `ResolutionResult` con:
     - available: ["gmail.send_email"]
     - needs_activation: ["google_sheets"]
     - not_found: []
     - needs_credentials: []
     - tool_mapping: {"send_email": "gmail.send_email"}
     - is_ready: False (porque needs_activation no vacío)
5. **ArchitectFlow detecta is_ready=False** → retorna respuesta al usuario con diagnóstico:
   ```
   Para crear este workflow necesito resolver lo siguiente:
   
   Servicios que necesitan activación:
     - google_sheets: ¿Querés que lo active para tu org?
   
   Tools mapeadas:
     - "send_email" → "gmail.send_email" ✓
   ```
6. **Usuario activa servicio** (vía dashboard o comando) → ArchitectFlow llama `activate_service("google_sheets")`.
7. **Reintenta resolve()** → is_ready=True → `apply_mapping` reemplaza tools → persiste normalmente.

### Edge Cases MVP

| Escenario | Comportamiento |
|---|---|
| Tool sin match posible | → `not_found`. is_ready=False. Informar usuario. |
| Servicio existe pero inactivo | → `needs_activation`. is_ready=False. |
| Servicio activo pero sin credenciales | → `needs_credentials`. is_ready=False. |
| Múltiples matches fuzzy | → Elegir mejor score. Si empate → not_found (mejor falso negativo que falso positivo). |
| Resolver falla por DB | → Excepción capturada por @with_error_handling → task FAILED. |
| Workflow sin allowed_tools | → Resolver retorna available=[], is_ready=True. Persiste normal. |

### Manejo de errores — qué ve el usuario

- **is_ready=False:** Mensaje estructurado con listas de needs_activation, needs_credentials, not_found.
- **Resolver exception:** "Error interno resolviendo integraciones" + task status=failed en DB.
- **Persistencia exitosa:** "Workflow creado con N agentes. Tools validadas: X reales."

---

## 2. Diseño Técnico

### Componente nuevo: `src/flows/integration_resolver.py`

```python
@dataclass
class ResolutionResult:
    available: list[str]           # Tools reales disponibles
    needs_activation: list[str]    # Service IDs que necesitan activación
    not_found: list[str]           # Tools alucinadas sin match
    needs_credentials: list[str]   # Secret names faltantes
    tool_mapping: dict[str, str]   # alucinada → real
    
    @property
    def is_ready(self) -> bool:
        return not (self.needs_activation or self.not_found or self.needs_credentials)


class IntegrationResolver:
    def __init__(self, org_id: str):
        self.org_id = org_id
        self.db = get_service_client()
    
    async def resolve(self, workflow_def: dict) -> ResolutionResult:
        """
        1. Extraer allowed_tools de todos los agentes
        2. Fuzzy match contra service_tools
        3. Verificar activación en org_service_integrations
        4. Verificar credenciales en Vault
        5. Construir ResolutionResult
        """
    
    async def activate_service(self, service_id: str) -> None:
        """Insertar fila en org_service_integrations con status='pending_setup'."""
    
    async def store_credential(self, secret_name: str, secret_value: str) -> None:
        """Wrapper para upsert_secret(org_id, name, value)."""
    
    def apply_mapping(self, workflow_def: dict, mapping: dict[str, str]) -> dict:
        """Reemplazar allowed_tools en cada agente según mapping."""
```

### Lógica de fuzzy matching

```python
def _find_tool_match(self, tool_hint: str) -> str | None:
    """
    Estrategia en 3 niveles:
    
    Nivel 1 — Exact match por id:
      SELECT id FROM service_tools WHERE id = tool_hint
      → si existe, retornar
    
    Nivel 2 — Service ID + keyword:
      # Extraer posible service_id del hint (ej: "google_sheets_read" → "google_sheets")
      # Buscar service_catalog con name ILIKE '%google_sheets%'
      # Luego buscar service_tools WHERE service_id = matched_service 
      #   AND (name ILIKE '%read%' OR id ILIKE '%read%')
    
    Nivel 3 — ILIKE global en name:
      SELECT id FROM service_tools WHERE name ILIKE '%{hint}%' LIMIT 1
    
    Si nada matchea → None (not_found)
    """
```

### Modificación en `architect_flow.py`

**Insertar entre L135 (validate_workflow) y L141 (ensure_unique_flow_type):**

```python
# Después de: validate_workflow(workflow_def, org_id=self.org_id)
# Antes de: safe_flow_type = self._ensure_unique_flow_type(...)

# ── IntegrationResolver: validar tools contra catálogo real ──
from ..flows.integration_resolver import IntegrationResolver

resolver = IntegrationResolver(org_id=self.org_id)
resolution = await resolver.resolve(workflow_def.model_dump())

if not resolution.is_ready:
    # Retornar diagnóstico al usuario sin persistir
    return self._build_resolution_response(resolution, workflow_def)

# Aplicar mapping de tools alucinadas → reales
workflow_def = self._apply_tool_mapping(workflow_def, resolution.tool_mapping)
```

**Nuevo método en ArchitectFlow:**

```python
def _build_resolution_response(self, resolution, workflow_def):
    """Construir respuesta diagnóstica cuando is_ready=False."""
    message_parts = ["Para crear este workflow necesito resolver lo siguiente:\n"]
    
    if resolution.needs_activation:
        message_parts.append("Servicios que necesitan activación:")
        for svc in resolution.needs_activation:
            message_parts.append(f"  - {svc}: ¿Querés que lo active para tu org?")
    
    if resolution.needs_credentials:
        message_parts.append("Credenciales faltantes:")
        for secret in resolution.needs_credentials:
            message_parts.append(f"  - {secret}: Necesito esta credencial.")
    
    if resolution.not_found:
        message_parts.append("Servicios no encontrados en el catálogo:")
        for tool in resolution.not_found:
            message_parts.append(f"  - {tool}: No encontré esta integración.")
    
    if resolution.tool_mapping:
        message_parts.append("Tools mapeadas:")
        for alucinada, real in resolution.tool_mapping.items():
            message_parts.append(f"  - \"{alucinada}\" → \"{real}\" ✓")
    
    return {
        "status": "resolution_required",
        "is_ready": False,
        "resolution": {
            "available": resolution.available,
            "needs_activation": resolution.needs_activation,
            "not_found": resolution.not_found,
            "needs_credentials": resolution.needs_credentials,
            "tool_mapping": resolution.tool_mapping,
        },
        "message": "\n\n".join(message_parts),
    }
```

### Extensión de `src/db/vault.py`

```python
def upsert_secret(org_id: str, name: str, value: str) -> None:
    """
    Insertar o actualizar un secreto para una organización.
    
    Usa service_role (bypass RLS). Requiere política INSERT/UPDATE en secrets.
    """
    svc = get_service_client()
    svc.table("secrets").upsert({
        "org_id": org_id,
        "name": name,
        "secret_value": value,
    }, on_conflict="org_id,name").execute()
```

### Migración RLS para secrets

```sql
-- Nueva migración: 027_secrets_write_policy.sql
-- Permitir INSERT/UPDATE en secrets para service_role

CREATE POLICY "service_role_write_secrets" ON secrets
  FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_role_update_secrets" ON secrets
  FOR UPDATE USING (auth.role() = 'service_role');
```

### Mejora al prompt del LLM (architect_flow.py L158+)

**Antes de llamar al LLM, inyectar catálogo:**

```python
# Obtener tools disponibles
svc = get_service_client()
available_tools = svc.table("service_tools").select("id, name, service_id").execute()

# Formatear lista concisa
tools_list = ", ".join([t["id"] for t in available_tools.data[:50]])  # limit 50 para no saturar contexto

# Inyectar en prompt (después de REGLAS CRÍTICAS, antes del cierre)
prompt += f"\n\n8. Tools disponibles en el catálogo (USAR SOLO estas):\n   {tools_list}"
prompt += "\n   Si necesitás una integración que no está en la lista, usá el nombre más descriptivo posible."
```

**Advertencia:** Inyectar 50+ tools aumenta tokens de input ~2-4K. Considerar inyectar solo service_ids + tools por categoría si el contexto del LLM es limitado. Para MVP, acceptable.

---

## 3. Decisiones

| # | Decisión | Justificación | Corrige plan |
|---|---|---|---|
| 1 | **Activation a nivel de servicio, no de tool** | org_service_integrations vincula org→servicio. No existe tabla org_tools. Todas las tools del servicio quedan disponibles al activarlo. | Plan asumía activación por tool (§ "activate_service per tool") |
| 2 | **Fuzzy match: service_id primero, luego keyword** | service_tools.id usa formato `service_id.tool_name`. Buscar ILIKE en todo el catálogo genera falsos positivos. Filtrar por service_id primero reduce espacio de búsqueda. | Plan sugería ILIKE directo sin filtrar por service |
| 3 | **Umbral de matching: exacto > keyword > ILIKE > not_found** | Mejor falso negativo que falso positivo — una tool incorrecta ejecutada es peor que pedir confirmación al usuario. | Plan no definía threshold explícito |
| 4 | **Resolver bloquea persistencia si is_ready=False** | ArchitectFlow retorna diagnóstico sin crear template. Garantiza que ningún workflow con tools inválidas se persiste. | Plan implícito pero no explícito en código |
| 5 | **upsert_secret usa on_conflict="org_id,name"** | Tabla secrets tiene UNIQUE(org_id, name). Upssert es idempotente. | Plan `store_credential` sin especificar conflicto |
| 6 | **No crear tabla nueva para resolución** | ResolutionResult es estado transitorio. Se retorna como output_data de la task. No necesita persistencia propia. | Plan no mencionaba persistir ResolutionResult |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | `IntegrationResolver.resolve()` retorna `ResolutionResult` con is_ready=True cuando todas las tools existen, están activas y tienen credenciales | Ejecutar con catálogo seed conocido → assert is_ready |
| 2 | `IntegrationResolver.resolve()` retorna is_ready=False con needs_activation cuando servicio no está en org_service_integrations | Insertar org sin integración → assert needs_activation contiene service_id |
| 3 | `IntegrationResolver.resolve()` retorna is_ready=False con not_found cuando tool no matchea nada en service_tools | Tool hint inexistente → assert not_found contiene hint |
| 4 | `apply_mapping()` reemplaza todas las allowed_tools alucinadas por tools reales en el workflow_def | Workflow con ["google_sheets_read"] → apply_mapping → workflow tiene ["google_sheets.read_spreadsheet"] |
| 5 | `ArchitectFlow._run_crew()` NO llama a `_persist_template()` si resolution.is_ready=False | Mock resolver → assert _persist_template no llamado |
| 6 | `upsert_secret()` inserta y recupera correctamente un secreto | upsert_secret → get_secret → assert valor igual |
| 7 | Política RLS en secrets permite INSERT/UPDATE para service_role | Ejecutar upsert_secret con service_role → sin error |
| 8 | Prompt del LLM incluye tools del catálogo | Log de _execute_architect_agent muestra tools en prompt |
| 9 | `activate_service()` crea fila en org_service_integrations con status='pending_setup' | Llamar activate_service → query DB → assert fila existe |

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| 1 | **Falso positivo de fuzzy match** — mapear a tool incorrecta por keyword genérica | Agente ejecuta tool equivocada en runtime | Umbral estricto: si score < 0.7 → not_found. Mostrar mapping al usuario para confirmación. |
| 2 | **RLS en secrets no actualizada** — upsert_secret falla silenciosamente o con 403 | Credenciales no se guardan, workflows fallan | Migración 027 como primera tarea. Test inmediato post-migración. |
| 3 | **Token budget del LLM excedido** — inyectar 50+ tools consume 4K+ tokens | LLM trunca contexto o genera respuesta incompleta | Limitar a 30 tools. Si catálogo > 30, inyectar solo service_ids + categorías. |
| 4 | **LLM ignora lista de tools** — sigue alucinando nombres | Resolver rechaza workflow, ciclo infinito de reintentos | Máximo 2 reintentos. Después de 2, retornar error al usuario. |
| 5 | **Race condition en activación** — usuario activa servicio mientras resolver verifica | Falso negativo: necesita activación cuando ya está activo | Usar transacción o re-verificar inmediatamente antes de retornar not_ready. |
| 6 | **Riesgo futuro — validación de input_schema** — Resolver valida nombre de tool pero no los parámetros | LLM genera allowed_tools válidas pero con parámetros que no matchean input_schema real | **Pre-requisito Paso 2:** añadir validación de schema de inputs en cada agente del workflow. |
| 7 | **Service_connector ya implementa verificación** — duplicación de lógica | Resolver y ServiceConnector ambos verifican servicio activo | Documentar que resolver es pre-flight (antes de persistir), connector es runtime (antes de ejecutar). Ambos necesarios. |

---

## 6. Plan

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|
| 1 | **Migración 027:** políticas INSERT/UPDATE en secrets para service_role | Baja | 15min | Ninguna |
| 2 | **Vault write:** upsert_secret() en src/db/vault.py | Baja | 20min | Tarea 1 |
| 3 | **IntegrationResolver core:** clase + resolve() + fuzzy matching | Media | 2h | Tarea 2 |
| 4 | **Resolver auxiliares:** activate_service(), store_credential(), apply_mapping() | Baja | 45min | Tarea 3 |
| 5 | **ArchitectFlow integration:** insertar llamada resolver + _build_resolution_response + pausa si not_ready | Media | 1.5h | Tarea 4 |
| 6 | **Prompt enhancement:** inyectar catálogo de tools en prompt LLM | Baja | 30min | Ninguna (independiente de T3-T5) |
| 7 | **Tests unitarios:** resolver con mocks de DB (happy path, not_found, needs_activation, needs_credentials) | Media | 1.5h | Tareas 3-5 |
| 8 | **Test manual end-to-end:** crear workflow con tools reales + verificar persistencia | Baja | 30min | Tareas 1-7 |

**Tiempo total estimado:** ~7 horas

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (6 puede hacerse en paralelo con 3-5)

---

## 🔮 Roadmap (NO implementar ahora)

### Optimizaciones post-MVP

1. **MCPRegistryClient (futuro):** Para tools not_found, consultar servidores MCP externos en vez de rechazar inmediatamente. El plan menciona esto como "futuro paso".
2. **Scoring de fuzzy match con embeddings:** Usar embeddings de tool descriptions para matching semántico en vez de ILIKE/keyword. "leer hoja de cálculo" → `google_sheets.read_spreadsheet` sin keyword overlap.
3. **Validación de input_schema:** Verificar que los parámetros que el LLM espera para cada tool son compatibles con el input_schema real de service_tools. (Pre-requisito para Paso 2 del plan general).
4. **Caching de resolución:** Cache en Redis del ResolutionResult por org + workflow_hash para evitar re-resolver el mismo workflow repetidamente.
5. **Dashboard de integraciones:** UI que muestre al usuario qué servicios están activos, qué tools tienen disponibles, y permita activar/desactivar con un click.
6. **Auto-activación con guía:** Cuando el resolver detecta needs_activation, generar flujo guiado paso-a-paso para activar el servicio (obtener API key, configurar OAuth, etc.).

### Decisiones de diseño que no bloquean el futuro

- **ResolutionResult como dataclass (no Pydantic):** Liviano, sin overhead de validación. Si en el futuro se necesita persistir en DB, se puede migrar a Pydantic sin romper la interfaz.
- **Fuzzy match como método interno (no servicio separado):** Si el futuro requiere un servicio de matching más sofisticado, se puede extraer sin cambiar IntegrationResolver.resolve().
- **activate_service simplificado (solo inserta fila):** No ejecuta health check ni configuración inicial. Eso va en un paso posterior de "setup wizard" del servicio.

### Pre-requisitos para pasos futuros descubiertos

| Paso futuro | Pre-requisito descubierto |
|---|---|
| Validación de parámetros de tools | service_tools.input_schema debe ser validado contra los inputs del workflow |
| HITL para activación de servicios | pending_approvals necesita nuevo flow_type "service_activation" |
| Streaming SSE de resolución | IntegrationResolver necesita método stream_resolve() con eventos parciales |
| Multi-org resolution | Resolver debe poder copiar configuraciones entre orgs (clone_integration) |
