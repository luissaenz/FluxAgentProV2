# 📋 Análisis Técnico — IntegrationResolver (Paso 1)

---

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `service_catalog` existe | `grep "CREATE TABLE.*service_catalog" migrations/` | ✅ | 024_service_catalog.sql L8 |
| 2 | Tabla `service_tools` existe | `grep "CREATE TABLE.*service_tools" migrations/` | ✅ | 024_service_catalog.sql L59 |
| 3 | Tabla `org_service_integrations` existe | `grep "CREATE TABLE.*org_service_integrations" migrations/` | ✅ | 024_service_catalog.sql L28 |
| 4 | Tabla `agent_catalog` existe | `grep "CREATE TABLE.*agent_catalog" migrations/` | ✅ | 004_agent_catalog.sql L2 |
| 5 | Tabla `workflow_templates` existe | `grep "CREATE TABLE.*workflow_templates" migrations/` | ✅ | 006_workflow_templates.sql L2 |
| 6 | Tabla `secrets` (Vault) existe | `grep "CREATE TABLE.*secrets" migrations/` | ✅ | 002_governance.sql L79 |
| 7 | Función `get_service_client` existe | `grep "def get_service_client" src/db/` | ✅ | src/db/session.py L48 |
| 8 | Función `upsert_secret` en vault.py | Leer vault.py completo | ❌ | **NO EXISTE** — solo tiene get_secret, list_secrets, get_secret_async |
| 9 | Clase `IntegrationResolver` existe | Glob integration_resolver.py | ❌ | **NO EXISTE** — archivo no criado |
| 10 | Estructura de ArchitectFlow | Leer architect_flow.py | ✅ | L112-163: generación + parseo + validación + persist |
| 11 | Campo `allowed_tools` en AgentDefinition | Leer workflow_definition.py | ✅ | AgentDefinition L19: `allowed_tools: list[str]` |
| 12 | Método `DynamicWorkflow.register` | Leer dynamic_flow.py L39 | ✅ | register() existe con firma `(flow_type, definition)` |
| 13 | Dependencia `httpx` | cat pyproject.toml | ✅ | L23: `httpx>=0.28.0` |
| 14 | Campo `tool_profile` en service_tools | Leer 024_service_catalog.sql L67 | ✅ | `tool_profile JSONB NOT NULL` — disponible para matching |
| 15 | Dependencia `crewai` | cat pyproject.toml | ✅ | Es opcional, no directa: `[project.optional-dependencies]` |
| 16 | Query RLS en secrets | Leer 002_governance.sql L91-92 | ✅ | Policy "service_role_only_secrets" — solo SELECT |

### Discrepancias Encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| 1 | **vault.py NO tiene función de escritura** (`upsert_secret`). El plan asume que existe para persistir credenciales del IntegrationResolver. | Crear función `upsert_secret(org_id, name, value)` en vault.py usando service_client. La tabla secrets tiene UNIQUE(org_id, name) en la migración — upsert funciona directo con .upsert(). |
| 2 | **IntegrationResolver no existe** — es 100% nuevo. El archivo `src/flows/integration_resolver.py` no existe en el codebase. | Implementar clase completa desde cero. |
| 3 | **service_tools.tool_profile** — el plan no especifica qué contiene este campo ni cómo usarlo para fuzzy matching. | Definir estrategia de matching basada en los campos explícitos de la migración: `id`, `name`, `service_id`. El campo `tool_profile` es JSONB自由 — puede usarse para keywords/metadata cuando se implemente. |
| 4 | **Falta función para listar integraciones de org** — el resolver necesita consultar `org_service_integrations` por `org_id` y `status`. | Crear helper en vault.py o usar service_client directo. |

---

## 1. Diseño Funcional

### 1.1 Happy Path

1. **Input:** `ArchitectFlow` genera `WorkflowDefinition` con `agents[i].allowed_tools` conteniendo herramientas inventadas por el LLM (ej: `"google_sheets_read"`, `"send_email"`).

2. **Ejecución de IntegrationResolver.resolve(workflow_def, org_id):**
   - Extraer todas las tools únicas de todos los agentes del workflow.
   - Para cada tool, buscar match en `service_tools`:
     - **Match exacto** por `id` (ej: `"gmail.send_email"`).
     - **Match por service_id + keyword en `name`** (ej: `"google_sheets"` + `"read"` → `"google_sheets.read_spreadsheet"`).
     - **Match fuzzy** con ILIKE sobre `name` como último recurso.
   - Para cada servicio (deduplicado), verificar en `org_service_integrations`:
     - Si no existe → añadir a `needs_activation`.
     - Si existe con `status = 'active'` → verificar credenciales en Vault.
   - Para cada servicio activo, verificar que los `secret_names` declarados existen en Vault.
     - Si falta alguno → añadir a `needs_credentials`.

3. **Output:** `ResolutionResult` con:
   - `available`: tools resueltas y activas.
   - `needs_activation`: servicios sin activar.
   - `not_found`: tools sin match en el catálogo.
   - `needs_credentials`: secretos faltantes.
   - `tool_mapping`: mapping alucinada → real.

4. **Persistencia condicional:**
   - Si `resolution.is_ready == True` → persistir workflow (continuar ArchitectFlow normal).
   - Si `resolution.is_ready == False` → **no persistir**, retornar diagnóstico al usuario con los pasos para resolver.

### 1.2 Flujo de Activación Manual (no MVP)

Cuando el usuario responde al diagnóstico:
- `IntegrationResolver.activate_service(service_id, secret_names)` → inserta/actualiza en `org_service_integrations` con `status = 'active'`.
- `IntegrationResolver.store_credential(secret_name, secret_value)` → upsert en Vault.
- Re-ejecutar `resolve()` → verificar `is_ready == True` → persistir.

### 1.3 Edge Cases MVP

| Escenario | Comportamiento |
|---|---|
| Tool 完全 no encontrada | No persistir. Añadir a `not_found`. Mostrar al usuario: "Esta tool no existe en el catálogo. ¿Querés agregar una custom?" |
| Match ambiguo (múltiples candidatos) | Elegir el primero por heurística: prioridad por coincidencia de service_id + keyword exacto en name. |
| Servicio inactivo | No bloquear por defecto. Añadir a `needs_activation`. Persistir el workflow pero marcar metadata para que el DynamicFlow falle en ejecución si la tool se intenta usar sin credenciales. |
| Servicio activo sin credenciales | Añadir a `needs_credentials`. Mismo tratamiento que inactivo. |
| Error de conectividad DB | Propagar excepción — ArchitectFlow debe marcar task como failed. |

### 1.4 Manejo de Errores

- **DB offline:** La_query falla → logger.error + raise.
- **Vault error:**get_secret falla para credencial existente → añadir a needs_credentials, no throw.
- **Workflow sin allowed_tools:** Resolver retorna vacío, `is_ready = True` (no hay nada que resolver).

---

## 2. Diseño Técnico

### 2.1 Componentes Nuevos

| Archivo | Descripción |
|---|---|
| `src/flows/integration_resolver.py` | **NUEVO.** Clase `IntegrationResolver` + dataclass `ResolutionResult`. |
| `src/db/vault.py` | **MODIFICAR.** Añadir `upsert_secret(org_id, name, value)`. |
| `src/flows/architect_flow.py` | **MODIFICAR.** Insertar llamada a IntegrationResolver entre L125 (workflow_def parseado) y L129 (validate_workflow). |

### 2.2 Interfaz de IntegrationResolver

```python
# src/flows/integration_resolver.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResolutionResult:
    """Resultado de resolver las dependencias de un workflow."""
    available: list[str] = field(default_factory=list)
    needs_activation: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    needs_credentials: list[str] = field(default_factory=list)
    tool_mapping: dict[str, str] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return (
            len(self.needs_activation) == 0
            and len(self.not_found) == 0
            and len(self.needs_credentials) == 0
        )


class IntegrationResolver:
    """Valida y resuelve las tools de un WorkflowDefinition contra el catálogo real."""

    def __init__(self, org_id: str):
        self.org_id = org_id

    async def resolve(self, workflow_def: dict) -> ResolutionResult:
        """Ejecutar resolución completa."""

    async def activate_service(
        self, 
        service_id: str, 
        secret_names: list[str],
        config: Optional[dict] = None
    ) -> None:
        """Activar un servicio para la org."""

    async def store_credential(self, secret_name: str, secret_value: str) -> None:
        """Almacenar credencial en Vault."""

    def apply_mapping(self, workflow_def: dict) -> dict:
        """Reemplazar tools alucinadas por tools reales en el workflow_def."""
```

### 2.3 Lógica Interna de resolve()

```
1. Extraer tools únicas:
   tools_needed = set(agent["allowed_tools"] for agent in workflow_def["agents"])

2. Para cada tool en tools_needed:
   a. Buscar en service_tools por id exacto:
      SELECT id, name, service_id FROM service_tools WHERE id = $1
      → Si encuentra → mapping[tool] = id, guardar service_id
   b. Si no, buscar por service_id inferido:
      Si "x_y" en tool → service_id = "x", buscar en service_tools 
      WHERE service_id = $service_id AND name ILIKE '%y%'
   c. Si no, búsqueda fuzzy:
      SELECT id, name, service_id FROM service_tools 
      WHERE name ILIKE $'%{tool}%'
   d. Si nada → not_found.append(tool)

3. Para cada service_id único detectado:
   a. Query org_service_integrations:
      SELECT status, secret_names FROM org_service_integrations
      WHERE org_id = $org_id AND service_id = $service_id
   b. Si no existe → needs_activation.append(service_id)
   c. Si status != 'active' → needs_activation.append(service_id)
   d. Si activo, para cada secret_name:
      → Verificar get_secret(org_id, secret_name)
      → Si falla → needs_credentials.append(secret_name)

4. Retornar ResolutionResult.
```

### 2.4 Integración en ArchitectFlow

**Ubicación propuesta:** Entre L125 (`workflow_def = self._parse_workflow_definition(raw_result)`) y L129 (`validate_workflow`):

```python
# architect_flow.py — dentro de _run_crew(), después de parseo y antes de validación

# 1. Validar y resolver herramientas contra el catálogo
from .integration_resolver import IntegrationResolver

resolver = IntegrationResolver(org_id=self.org_id)
resolution = await resolver.resolve(workflow_def.model_dump())

if not resolution.is_ready:
    logger.warning(
        "ArchitectFlow[%s] resolution no lista: need_act=%s, not_found=%s, need_cred=%s",
        self.state.task_id,
        resolution.needs_activation,
        resolution.not_found,
        resolution.needs_credentials,
    )
    # Persistir state de diagnóstico para UI
    self.state.extracted_definition = workflow_def
    return {
        "status": "needs_resolution",
        "needs_activation": resolution.needs_activation,
        "not_found": resolution.not_found,
        "needs_credentials": resolution.needs_credentials,
        "message": (
            "El workflow no puede persistirse hasta resolver las siguiente integraciones:\n"
            f"- Servicios por activar: {resolution.needs_activation}\n"
            f"- Herramientas no encontradas: {resolution.not_found}\n"
            f"- Credenciales faltantes: {resolution.needs_credentials}"
        ),
    }

# 2. Reemplazar tools alucinadas por reales
workflow_def = resolver.apply_mapping(workflow_def.model_dump())

# 3. Continuar con validate_workflow (L129 actual)...
```

### 2.5 Extensión de vault.py

```python
# Añadir a vault.py

def upsert_secret(org_id: str, name: str, value: str) -> None:
    """
    Insertar o actualizar un secreto en el Vault.

    Args:
        org_id: UUID de la organización
        name: Nombre del secreto (ej: "google_oauth_token")
        value: Valor del secreto (texto plano — se almacena como-is)

    Uso interno por IntegrationResolver. No hay返回值 —
    cualquier error debe manejarse en el caller.
    """
    svc = get_service_client()

    svc.table("secrets").upsert({
        "org_id": org_id,
        "name": name,
        "secret_value": value,
    }, on_conflict="org_id,name").execute()

    logger.info("Vault: secreto '%s' upserted para org '%s'", name, org_id)
```

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| 1 | **Blocking por defecto si is_ready == False** | Un workflow con tools no resolvedas NO debe persistir. Si persiste, el DynamicWorkflow fallará en ejecución con errores crípticos. Es mejor bloquear antes y giving feedback claro. |
| 2 | **Estrategia de matching en 3 pasos** | Prioridad: id exacto → service_id + keyword → fuzzy. Esto minimiza falsos positivos. El campo tool_profile queda libre para futura expansión (keywords declarados). |
| 3 | **No auto-activación de servicios** | El plan sugiere `activate_service()` como método público. Pero la activación real requiere que el usuario proporcione credenciales. Por tanto, no se activa automáticamente — se retorna needs_activation + mensaje al usuario. |
| 4 | **Herramienta no encontrada = bloquear** | A diferencia de servicios inactivos, una tool que no existe en el catálogo es un error de definición. No podemos crear un workflow que reference tools inexistentes. |
| 5 | **Diagnóstico en response JSON** | En vez de raise error, ArchitectFlow retorna un JSON con status "needs_resolution" y los campos de diagnóstico. El frontend (o el usuario via LLM) puede usar esto para pedir al usuario las integraciones faltantes. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | IntegrationResolver.resolve() retorna ResolutionResult con todos los campos | Sí — test unitario con mock DB |
| 2 | Matching exacto por id funciona (google_sheets.read_spreadsheet) | Sí — test unitario |
| 3 | Matching por service_id + keyword funciona (sheet → google_sheets.read_spreadsheet) | Sí — test unitario |
| 4 | Tool no encontrada aparece en not_found | Sí — test unitario |
| 5 | Servicio inactivo aparece en needs_activation | Sí — test unitario |
| 6 | Credencial faltante aparece en needs_credentials | Sí — test unitario |
| 7 | is_ready == True solo cuando todo resolvedo | Sí — test unitario |
| 8 | apply_mapping() reemplaza todas las herramientas | Sí — test unitario |
| 9 | upsert_secret() funciona en tabla secrets | Sí — test de integración |
| 10 | ArchitectFlow no persiste si is_ready == False | Sí — test de integración (mock resolve) |
| 11 | ArchitectFlow retorna diagnóstico en JSON | Sí — test de integración |
| 12 | El workflow persistido tiene tools reales, no alucinadas | Sí — test E2E |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| 1 | Falso positivo en fuzzy match (tool incorrecta) | Media | Alto | Incluir tool_mapping en mensaje de éxito; permitir al usuario revisar antes de confirmar. |
| 2 | LLM ignora el catálogo inyectado y sigue inventando | Alta | Medio | El resolver es el guardián final; si no matchea, bloquea. |
| 3 | Credenciales en Plain Text en Vault | Baja | Alto | La tabla secrets no tiene encryption a nivel DB; usar Supabase Vault (si está configurado) o documentar que se cifra a nivel aplicación. |
| 4 | Error de DB durante resolve() | Baja | Alto | Wrap en try/except; marcar task como failed con error claro. |
| 5 | Múltiples matches ambiguos | Media | Bajo | Logging del match elegido; mostrar alternativas en mensaje. |
| 6 | Servicio existente con status diferente a 'active' | Media | Medio | Soportar estados: pending_setup, active, suspended, disconnected. |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Deps | Estimación |
|---|---|---|---|---|
| 1 | Añadir `upsert_secret()` a vault.py | Baja | — | 30 min |
| 2 | Crear `IntegrationResolver` con estructura y tipos | Baja | 1 | 30 min |
| 3 | Implementar lógica de resolve() (matching) | Alta | 2 | 2h |
| 4 | Implementar apply_mapping() | Baja | 3 | 30 min |
| 5 | Implementar activate_service() y store_credential() | Media | 4 | 30 min |
| 6 | Integrar en ArchitectFlow._run_crew() | Media | 3, 5 | 1h |
| 7 | Tests unitarios IntegrationResolver | Media | 3-5 | 1.5h |
| 8 | Test de integración ArchitectFlow | Alta | 6 | 1h |
| | **TOTAL** | | | | **~7.5h** |

---

## 🍃 Roadmap (NO Implementar Ahora)

- **[Post-MVP]** Inyectar catálogo de tools en el prompt del agente Architect para reducir alucinaciones antes de que ocurran.
- **[Post-MVP]** Soporte para tool_profile JSONB (keywords declarados) para matching más preciso.
- **[Post-MVP]** Integración con fuentes externas (MCPRegistryClient) para tools no encontradas en el catálogo local.
- **[Post-MVP]** Validación de credenciales en tiempo de ejecución (no solo en creación) — el DynamicFlow debe verificar credenciales antes de executar cada step.
- **[Post-MVP]** UI en Dashboard para gestionar integraciones (activar servicios, cargar credenciales) sin necesitar al ArchitectFlow.
- **[Post-MVP]** Rotación automática de secretos via Supabase Vault (si disponível).

---

## 📊 Métrica de Calidad

| Métrica | Valor |
|---|---|
| Elementos verificados contra código | 16 |
| Discrepancias detectadas | 4 (todas con resolución) |
| Resoluciones con evidencia | 100% |
| Criterios de aceptación binarios | 12/12 |
| Criterios cubren todo el paso | ✅ Todos los sub-pasos |
| Suposiciones no verificadas | 1 (tool_profile sin uso definido — marcar ⚠️) |
| Estimación de tiempo incluida | ✅ 7.5h total |

---

**Idioma:** Español 🇪🇸