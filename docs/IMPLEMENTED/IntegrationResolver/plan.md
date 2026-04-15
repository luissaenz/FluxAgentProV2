PASO 1

IntegrationResolver — Definición
Qué es
Una clase Python (no un agente, no una crew) que se ejecuta entre la generación del WorkflowDefinition por el LLM y la persistencia en DB. Es un paso de validación y resolución que convierte tools alucinadas en tools reales.
Dónde se inserta en ArchitectFlow
Flujo actual:
  LLM genera WorkflowDefinition (L112-163)
    → validate_workflow (guardrails)
      → persist workflow_templates (L336-350)
        → upsert agent_catalog (L360-387)    ← tools alucinadas se persisten
          → register DynamicWorkflow (L394-404)

Flujo nuevo:
  LLM genera WorkflowDefinition (L112-163)
    → validate_workflow (guardrails)
      → IntegrationResolver.resolve(workflow_def, org_id)   ← NUEVO
        → persist workflow_templates
          → upsert agent_catalog                             ← tools validadas/reales
            → register DynamicWorkflow
Interfaz
python# src/flows/integration_resolver.py

from dataclasses import dataclass

@dataclass
class ResolutionResult:
    """Resultado de resolver las dependencias de un workflow."""
    
    # Tools que existen en service_catalog Y están activas para la org
    available: list[str]
    
    # Tools que existen en service_catalog pero NO activas para esta org
    needs_activation: list[str]
    
    # Tools que NO existen en service_catalog
    not_found: list[str]
    
    # Credenciales que faltan en Vault para los servicios activos
    needs_credentials: list[str]
    
    # Mapping de tool alucinada → tool real más cercana
    # Ej: {"google_sheets_read" → "google_sheets.read_spreadsheet"}
    tool_mapping: dict[str, str]
    
    @property
    def is_ready(self) -> bool:
        """True si todo está resuelto y se puede persistir."""
        return len(self.needs_activation) == 0 \
           and len(self.not_found) == 0 \
           and len(self.needs_credentials) == 0


class IntegrationResolver:
    """Valida y resuelve las tools de un WorkflowDefinition contra el catálogo real."""
    
    def __init__(self, org_id: str):
        self.org_id = org_id
        self.db = get_service_client()
    
    async def resolve(self, workflow_def: dict) -> ResolutionResult:
        """
        1. Extrae todas las allowed_tools de todos los agentes del workflow
        2. Para cada tool, busca en service_catalog (fuzzy match)
        3. Verifica activación en org_service_integrations
        4. Verifica credenciales en Vault
        5. Retorna ResolutionResult
        """
    
    async def activate_service(self, service_id: str, secret_names: list[str]) -> None:
        """Activa un servicio para la org."""
    
    async def store_credential(self, secret_name: str, secret_value: str) -> None:
        """Almacena credencial en Vault."""
    
    def apply_mapping(self, workflow_def: dict, mapping: dict[str, str]) -> dict:
        """Reemplaza tools alucinadas por tools reales en el workflow_def."""
Lógica interna de resolve()
Input: workflow_def con agentes que tienen allowed_tools alucinadas
       Ej: ["google_sheets_read", "google_sheets_write", "send_email"]

Paso 1 — Extraer tools únicas de todos los agentes:
  tools_needed = {"google_sheets_read", "google_sheets_write", "send_email"}

Paso 2 — Para cada tool, buscar en service_tools (fuzzy):
  SELECT id, name, service_id 
  FROM service_tools 
  WHERE id ILIKE '%google_sheets%' OR name ILIKE '%google_sheets%'
  
  "google_sheets_read"  → match: "google_sheets.read_spreadsheet"
  "google_sheets_write" → match: "google_sheets.append_rows"  
  "send_email"          → match: "gmail.send_email"
  
  Si no hay match → va a not_found

Paso 3 — Para cada servicio (deduplicated), verificar activación:
  SELECT status FROM org_service_integrations 
  WHERE org_id = $1 AND service_id = $2
  
  "google_sheets" → no existe → needs_activation
  "gmail"         → status='active' → available

Paso 4 — Para servicios activos, verificar credenciales:
  SELECT secret_names FROM org_service_integrations WHERE ...
  Para cada secret_name: verificar que existe en Vault
  
  Si falta → needs_credentials

Paso 5 — Construir ResolutionResult con todo
El fuzzy match de tools
El LLM puede generar cualquier nombre. Necesitamos mapear a tools reales:
LLM generaMatch en service_toolsEstrategiagoogle_sheets_readgoogle_sheets.read_spreadsheetCoincide service_id + keyword "read"read_spreadsheetgoogle_sheets.read_spreadsheetCoincide name parcialleer_hoja_calculogoogle_sheets.read_spreadsheetSin match directo → not_foundgmail.send_emailgmail.send_emailMatch exacto
Estrategia de matching (en orden):

Match exacto por id
Match por service_id + keyword en name
Match por name con ILIKE
Si nada matchea → not_found

Para not_found, el paso siguiente (MCPRegistryClient, futuro) buscaría en fuentes externas. Por ahora, retorna la lista para que ArchitectFlow informe al usuario.
Integración en architect_flow.py
El cambio en ArchitectFlow sería mínimo. Después de validate_workflow y antes de persistir:
python# architect_flow.py — después de L163 (workflow_def generado) y antes de L336 (persist)

resolver = IntegrationResolver(org_id=self.org_id)
resolution = await resolver.resolve(workflow_def)

if not resolution.is_ready:
    # Retornar al usuario qué falta
    return self._build_resolution_response(resolution)

# Reemplazar tools alucinadas por tools reales
workflow_def = resolver.apply_mapping(workflow_def, resolution.tool_mapping)

# Continuar con persist normal...
Qué pasa cuando no está ready
ArchitectFlow retorna un mensaje al usuario en vez de persistir:
"Para crear este workflow necesito resolver lo siguiente:

Servicios que necesitan activación:
  - google_sheets: ¿Querés que lo active para tu org?

Credenciales faltantes:
  - google_oauth_token: Necesito un token de Google. 
    ¿Tenés uno o te guío para obtenerlo?

Servicios no encontrados en el catálogo:
  - custom_erp: No encontré esta integración. 
    ¿Tenés la URL del servidor MCP?"
El usuario responde, ArchitectFlow usa activate_service / store_credential, y reintenta resolve(). Cuando is_ready == True, persiste.
Archivos afectados
ArchivoCambiosrc/flows/integration_resolver.pyNUEVO — clase completasrc/flows/architect_flow.pyMODIFICAR — insertar llamada a resolver entre L163 y L336src/flows/architect_flow.pyMODIFICAR — prompt del LLM (L218) puede sugerir tools del catálogo real en vez de inventar
Mejora opcional al prompt del LLM
Actualmente el prompt (L218) dice "allowed_tools": [array de strings, puede estar vacío []]. Si le pasamos la lista de tools disponibles en el catálogo como contexto, el LLM alucinará menos:
python# Antes de llamar al LLM, obtener tools disponibles
available_tools = db.table("service_tools").select("id, name, tool_profile").execute()

# Inyectar en el prompt
prompt += f"\n\nTools disponibles en el catálogo:\n{format_tools(available_tools.data)}"
prompt += "\nUsá SOLO tools de esta lista en allowed_tools. Si necesitás una que no está, usá el nombre más descriptivo posible."
Esto reduce el fuzzy matching necesario pero no lo elimina — el LLM puede seguir inventando.
Esfuerzo
TareaTiempoIntegrationResolver clase + resolve() + matching2happly_mapping + activate_service + store_credential1hIntegración en architect_flow.py (insertar entre L163-L336)1hMejora al prompt del LLM con catálogo30minTests (mock DB + escenarios de matching)1hTotal~5.5h
Análisis Técnico — IntegrationResolver
Análisis del paso de integración del IntegrationResolver en el flujo de ArchitectFlow para resolver alucinaciones de herramientas mediante el catálogo de servicios real.

0. Verificación contra Código Fuente (OBLIGATORIA)
#	Elemento del Plan	Verificación	Estado	Evidencia
1	Tabla service_catalog existe	ls supabase/migrations/	✅	024_service_catalog.sql L8
2	Tabla service_tools existe	ls supabase/migrations/	✅	024_service_catalog.sql L59
3	Tabla org_service_integrations existe	ls supabase/migrations/	✅	024_service_catalog.sql L28
4	Tabla agent_catalog existe	ls supabase/migrations/	✅	004_agent_catalog.sql L2
5	Tabla workflow_templates existe	ls supabase/migrations/	✅	006_workflow_templates.sql L2
6	Tabla secrets (Vault) existe	grep -r "table(\"secrets\")" src/db/	✅	src/db/vault.py L48
7	Función get_service_client existe	grep -r "def get_service_client" src/db/	✅	src/db/session.py L48
8	Manejo de secretos en vault.py	Leer src/db/vault.py	❌	Falta función store_secret
9	Estructura de ArchitectFlow	Leer src/flows/architect_flow.py	✅	L112-163 coinciden con lógica de generación
10	allowed_tools en WorkflowDefinition	Leer src/flows/workflow_definition.py	✅	AgentDefinition L19
11	DynamicWorkflow.register	Leer src/flows/dynamic_flow.py	✅	L39
12	Dependencia httpx para integraciones	cat pyproject.toml	✅	L23
Discrepancias encontradas:

Falta upsert_secret en Vault: src/db/vault.py actualmente solo permite lectura (get_secret, list_secrets). El IntegrationResolver requiere persistir credenciales.
Resolución: Añadir upsert_secret(org_id, name, value) a src/db/vault.py usando get_service_client().
Ciclo de vida de ArchitectFlow: El plan asume que el resolver se inserta y ya. Sin embargo, si is_ready es False, el flow debe retornar información de diagnóstico al usuario en lugar de fallar o persistir.
Resolución: Modificar ArchitectFlow._run_crew para que, si el resolver detecta faltantes, el output_data contenga el ResolutionResult y un mensaje de acción.
Matching fuzzy en service_tools: El plan sugiere buscar por id o name. En la migración 024, service_tools.id suele ser service_id.tool_name.
Resolución: Priorizar match exacto en id y luego fuzzy en name limitado al service_id detectado.
1. Diseño Funcional
Happy Path:
El usuario describe un workflow (ej: "lee sheets y manda gmail").
El LLM genera WorkflowDefinition con tools como google_sheets_read.
IntegrationResolver mapea google_sheets_read → google_sheets.read_spreadsheet.
Verifica que google_sheets esté activo para la org y tenga credenciales.
Si todo OK, persiste el workflow con la tool real.
Edge Cases MVP:
Tool no encontrada: Se informa al usuario. El workflow no se crea para evitar errores de runtime.
Servicio inactivo: IntegrationResolver retorna needs_activation. El frontend/usuario puede solicitar activación.
Múltiples matches: Si el fuzzy match devuelve varios, el resolver debe elegir el más probable (heurística por keywords: read, write, get, create).
Manejo de Errores: Si el resolver falla por conectividad a DB, se lanza una excepción capturada por BaseFlow que marca la tarea como failed.
2. Diseño Técnico
Componentes
src/flows/integration_resolver.py: Nuevo componente. Utiliza get_service_client() para acceder a catálogos globales y configuraciones de org.
src/db/vault.py: Extensión para soportar escritura de secretos.
src/flows/architect_flow.py: Modificación en el prompt y en _run_crew.
Interfaces (NUEVAS)
python
# ResolutionResult (Dataclass) - Estructura de comunicación interna
# ToolMapping: dict[str, str] (Alucinada -> Real)
Prompt LLM (Mejora)
Se inyectará un bloque de contexto antes de la descripción del usuario:

text
CONTEXTO DE INTEGRACIONES DISPONIBLES:
{lista_de_tools_del_catalogo}
3. Decisiones
Fuzzy Match basado en Keywords: Se usará una estrategia de scoring simple (Exact ID > Exact Name > Service+Keyword Match) antes de recurrir a ILIKE genérico.
Bloqueo de Persistencia: No se permitirá persistir un workflow_template si contiene tools not_found. Esto garantiza que los workflows dinámicos siempre sean ejecutables.
Uso de metadata en el State: Los detalles de ResolutionResult se guardarán en self.state.metadata si el flow se pausa, para facilitar el diagnóstico.
4. Criterios de Aceptación
 IntegrationResolver resuelve correctamente google_sheets_read contra un catálogo real. (Sí/No)
 ArchitectFlow no persiste el template si is_ready es False. (Sí/No)
 El prompt del Architect incluye tools reales del service_catalog. (Sí/No)
 upsert_secret funciona correctamente en la tabla secrets. (Sí/No)
 apply_mapping reemplaza todas las instancias de tools alucinadas en la lista de agentes. (Sí/No)
5. Riesgos
Alucinaciones persistentes: El LLM puede ignorar la lista de tools reales e inventar nuevas.
Mitigación: El Resolver es el guardián final; si no matchea, bloquea la creación.
Seguridad en Escritura de Vault: upsert_secret usa service_role.
Mitigación: Solo accesible por IntegrationResolver dentro de un flow del sistema. Validar org_id antes de escribir.
Falsos positivos de Fuzzy Match: Mapear a una tool incorrecta por nombre similar.
Mitigación: Mostrar el mapping al usuario en el mensaje de éxito del Architect.
6. Plan
Infra (1h): Añadir upsert_secret y list_org_integrations (útil para el resolver). [Baja]
Resolver Core (2h): Implementar IntegrationResolver con lógica de matching y validación de activación. [Media]
Integration (1h): Modificar architect_flow.py para llamar al resolver y manejar el estado not_ready. [Media]
Prompt Engineering (30m): Inyectar catálogo en el prompt del agente Architect. [Baja]
Testing (1.5h): Unit tests para el resolver (mocking de catálogo) y test manual de punta a punta. [Media]
Total estimado: 6 horas.

