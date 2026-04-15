# Análisis Técnico — IntegrationResolver (Paso 1)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|-----------|
| 1 | Tabla service_catalog existe | `ls supabase/migrations/024_service_catalog.sql` | ✅ | Migración 024, L8: CREATE TABLE service_catalog |
| 2 | Tabla service_tools existe | `ls supabase/migrations/024_service_catalog.sql` | ✅ | Migración 024, L59: CREATE TABLE service_tools |
| 3 | Tabla org_service_integrations existe | `ls supabase/migrations/024_service_catalog.sql` | ✅ | Migración 024, L28: CREATE TABLE org_service_integrations |
| 4 | Tabla agent_catalog existe | `ls supabase/migrations/004_agent_catalog.sql` | ✅ | Migración 004, L7: CREATE TABLE agent_catalog |
| 5 | Tabla workflow_templates existe | `ls supabase/migrations/006_workflow_templates.sql` | ✅ | Migración 006, L5: CREATE TABLE workflow_templates |
| 6 | Tabla secrets existe | `grep -r "table(\"secrets\")" src/db/` | ✅ | src/db/vault.py L48: svc.table("secrets") |
| 7 | Función get_service_client existe | `grep -r "def get_service_client" src/db/` | ✅ | src/db/session.py L48 |
| 8 | Vault tiene funciones de escritura | `read src/db/vault.py` | ❌ | Solo get_secret, list_secrets, get_secret_async; falta upsert_secret |
| 9 | Arquitectura de ArchitectFlow | `read src/flows/architect_flow.py L112-163` | ✅ | _run_crew con pasos 1-7, validación en L129-132 |
| 10 | allowed_tools en WorkflowDefinition | `read src/flows/workflow_definition.py` | ✅ | AgentDefinition L19: allowed_tools: list[str] |
| 11 | DynamicWorkflow.register | `read src/flows/dynamic_flow.py L39` | ✅ | @classmethod def register(cls, flow_type: str, definition: Dict[str, Any]) |
| 12 | Dependencia httpx | `cat pyproject.toml` | ✅ | L23: "httpx>=0.28.0" |
| 13 | Archivo integration_resolver.py no existe | `ls src/flows/integration_resolver.py` | ✅ | No existe, debe crearse |
| 14 | Prompt Architect incluye allowed_tools | `read src/flows/architect_flow.py L218` | ✅ | "allowed_tools": [array de strings, puede estar vacío []] |
| 15 | Patrón de fuzzy match en SQL | `grep -r "ILIKE" supabase/migrations/` | ⚠️ | No usado aún, pero ILIKE disponible en PostgreSQL |
| 16 | RLS en org_service_integrations | `read supabase/migrations/024_service_catalog.sql L45-51` | ✅ | ENABLE ROW LEVEL SECURITY con policy org_integration_access |
| 17 | allowed_tools en agent_catalog | `read supabase/migrations/004_agent_catalog.sql L12` | ✅ | allowed_tools TEXT[] DEFAULT '{}' |
| 18 | Integración de contextvars en MCP | `grep -r "contextvars" src/mcp/` | ✅ | src/mcp/server_sse.py usa contextvars para org_id |

**Discrepancias encontradas:**

- **Falta upsert_secret en Vault:** src/db/vault.py actualmente solo permite lectura (get_secret, list_secrets, get_secret_async). El IntegrationResolver requiere persistir credenciales nuevas. **Resolución:** Añadir upsert_secret(org_id: str, name: str, value: str) usando get_service_client() y upsert en tabla secrets.

- **Ciclo de vida de ArchitectFlow:** El plan asume que el resolver se inserta entre validate_workflow y persistir. Sin embargo, si is_ready=False, el flow debe retornar información al usuario en lugar de fallar silenciosamente. **Resolución:** Modificar _run_crew para que, si resolver indica faltantes, el output_data contenga ResolutionResult y un mensaje de diagnóstico.

- **Matching fuzzy en service_tools:** El plan sugiere buscar por id o name con ILIKE. En la migración 024, service_tools.id es único por service. **Resolución:** Priorizar match exacto en id, luego ILIKE en name limitado al service_id inferido del nombre alucinado.

## 1. Diseño Funcional

Happy Path:
1. Usuario describe workflow con herramientas (ej: "procesa facturas con Gmail y Sheets").
2. LLM genera WorkflowDefinition con allowed_tools alucinadas como ["gmail_send", "sheets_read"].
3. IntegrationResolver extrae tools únicas de todos los agentes.
4. Mapea "gmail_send" → "gmail.send_email" y "sheets_read" → "google_sheets.read_spreadsheet" vía fuzzy match en service_tools.
5. Verifica que servicios estén activos en org_service_integrations y credenciales existan en secrets.
6. Si todo OK, reemplaza tools alucinadas por reales y permite persistir el workflow.

Edge Cases MVP:
- **Tool no encontrada:** Resolver retorna not_found. Workflow no se crea; usuario debe especificar manualmente o esperar futuras versiones con búsqueda externa.
- **Servicio inactivo:** Resolver detecta en org_service_integrations.status != 'active'. Retorna needs_activation con lista de servicios requeridos.
- **Credenciales faltantes:** Para servicios activos, verifica existencia en secrets. Si falta, retorna needs_credentials con nombres requeridos.
- **Múltiples matches fuzzy:** Si ILIKE retorna varios, seleccionar el de mayor score (exacto en id > contiene service_keyword > ILIKE general).

Manejo de Errores:
- Conectividad DB falla: Resolver lanza excepción capturada por BaseFlow, marcando tarea como failed.
- Mapping inválido: apply_mapping verifica que todas las tools originales estén mapeadas; si no, aborta persistencia.

## 2. Diseño Técnico

Componentes Nuevos:
- **src/flows/integration_resolver.py:** Clase principal IntegrationResolver con métodos resolve(), activate_service(), store_credential(), apply_mapping(). Usa get_service_client() para consultas DB.

Interfaces Nuevas:
- **ResolutionResult (dataclass):** Estructura con campos available, needs_activation, not_found, needs_credentials, tool_mapping.
- **Método resolve(workflow_def: dict) -> ResolutionResult:** Procesa definición completa, extrae tools, valida contra catálogos.
- **Método apply_mapping(workflow_def: dict, mapping: dict) -> dict:** Reemplaza allowed_tools en agentes con tools reales.

Modificaciones:
- **src/flows/architect_flow.py:** Insertar llamada a resolver entre validate_workflow (L129) y _persist_template (L139). Si not is_ready, retornar mensaje de diagnóstico en lugar de persistir.
- **src/db/vault.py:** Añadir upsert_secret() para almacenar credenciales nuevas durante activación.
- **Prompt LLM en architect_flow.py:** Inyectar lista de tools disponibles del catálogo antes de la descripción del usuario para reducir alucinaciones.

Modelos de Datos:
- Reutiliza tablas existentes: service_catalog, service_tools, org_service_integrations, secrets.
- WorkflowDefinition permanece igual; allowed_tools se mapea post-validación.

Integraciones:
- **DB Layer:** Queries SELECT en service_tools y org_service_integrations; INSERT/UPDATE en secrets vía vault.
- **MCP Context:** Resolver usa org_id del contexto actual (contextvars en server_sse.py).
- **Async Handling:** Métodos async para no bloquear event loop de FastAPI.

## 3. Decisiones

- **Bloqueo de Persistencia con Tools Inválidas:** No permitir crear workflow si contiene tools not_found. Garantiza ejecutabilidad inmediata.
- **Estrategia de Matching Fuzzy:** Orden: 1) Match exacto en id, 2) Match por service_id + keyword en name (ej: "sheets" + "read"), 3) ILIKE general en name.
- **Almacenamiento de Credenciales durante Flujo:** activate_service() llama upsert_secret() para credenciales proporcionadas por usuario.
- **Diagnóstico de Faltantes al Usuario:** Si not is_ready, ArchitectFlow retorna mensaje estructurado con qué activar y qué credenciales faltan.

## 4. Criterios de Aceptación
- IntegrationResolver mapea correctamente tools alucinadas contra catálogo real.
- ArchitectFlow no persiste template si ResolutionResult.is_ready == False.
- Prompt del Architect incluye tools del service_catalog para reducir alucinaciones.
- upsert_secret funciona para almacenar credenciales nuevas en tabla secrets.
- apply_mapping reemplaza todas las instancias de allowed_tools alucinadas en definición de workflow.
- Resolver detecta servicios inactivos y credenciales faltantes con precisión.

## 5. Riesgos
- **Alucinaciones Persistentes:** LLM ignora lista de tools reales. **Mitigación:** Resolver como guardián final; si no matchea, bloquea creación con mensaje claro.
- **Seguridad en Escritura de Secrets:** upsert_secret usa service_role. **Mitigación:** Validar org_id antes de escribir; solo accesible desde IntegrationResolver en flows del sistema.
- **Falsos Positivos en Fuzzy Match:** Mapear a tool incorrecta por similitud. **Mitigación:** Mostrar mapping final al usuario en confirmación de creación.
- **Sobrecarga en DB durante Matching:** Múltiples queries ILIKE. **Mitigación:** Indexar name en service_tools; cachear catálogo si volumen alto.

## 6. Plan
- **Resolver Core (2h):** Implementar IntegrationResolver con lógica de matching y validación. Baja complejidad.
- **Integración en ArchitectFlow (1h):** Modificar _run_crew para insertar resolver y manejar not_ready. Media complejidad.
- **Extensión Vault (30min):** Añadir upsert_secret a vault.py. Baja complejidad.
- **Mejora Prompt (30min):** Inyectar catálogo disponible en prompt del LLM. Baja complejidad.
- **Tests (1.5h):** Unit tests para resolver (mock DB) y test de integración manual. Media complejidad.

**Total estimado: 5h**

## 🔮 Roadmap
- **Búsqueda Externa de Tools:** Para not_found, integrar MCPRegistryClient para buscar en fuentes externas (futuro Sprint).
- **Cache de Catálogo:** Almacenar service_catalog en Redis para reducir queries DB durante matching.
- **Validación Avanzada de Credenciales:** Verificar formato y expiración de tokens OAuth antes de almacenar.
- **Dashboard de Mappings:** UI para que usuarios vean y corrijan mappings fuzzy antes de persistir.</content>
<parameter name="filePath">LAST/analisis-kilo.md