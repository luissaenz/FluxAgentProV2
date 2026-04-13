# Análisis Técnico: Fase 2.5 - Service Catalog TIPO C

**Agente:** kilo  
**Fecha:** 2026-04-13  
**Alcance:** Implementación completa del Service Catalog TIPO C según plan mcp-analisis-finalV2.md

## 0. Verificación contra Código Fuente

Tabla de verificación con evidencia del código fuente real:

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|----------|
| 1 | Tabla `organizations` existe | `grep -r "CREATE TABLE.*organizations" migrations/` | ✅ | migrations/001_set_config_rpc.sql L53, id UUID PRIMARY KEY |
| 2 | Patrón RLS usa `current_org_id()` | `grep -rn "current_org_id" migrations/` | ✅ | migrations/001_set_config_rpc.sql L37-44, usado en 19 políticas |
| 3 | Función `get_secret()` existe | `grep -rn "def get_secret" src/` | ✅ | src/db/vault.py L23, firma correcta |
| 4 | Clase `OrgBaseTool` existe | `grep -rn "class OrgBaseTool" src/` | ✅ | src/tools/base_tool.py L17 |
| 5 | Dependencia `mcp>=1.0.0` directa | `grep -rn "mcp" pyproject.toml` | ❌ | Solo transitiva vía crewai-tools, no directa |
| 6 | Auth usa PyJWT | `grep -rn "import jwt" src/api/middleware.py` | ✅ | L54: import jwt as pyjwt, usa PyJWKClient |
| 7 | Tabla `activity_logs` existe | `grep -r "activity_logs" migrations/` | ❌ | No existe en ninguna migración |
| 8 | `get_secret_async()` definido | `grep -rn "def get_secret_async" src/` | ❌ | Importado en mcp_pool.py L26 pero no definido |
| 9 | `tool_registry.register()` API | `read src/tools/registry.py L39-47` | ❌ | Es decorador, no método con tool_class |
| 10 | Dependencia `python-jose` necesaria | `grep -rn "jose" src/api/middleware.py` | ⚠️ | No usada, pero en pyproject.toml - verificar si legacy |

**Discrepancias encontradas:**

1. **RLS Policy Pattern:** Plan usa `current_setting('app.current_org_id')::UUID` pero código real usa `current_org_id()` function que retorna `current_setting('app.org_id')` como TEXT.  
   **Resolución:** Usar patrón existente `org_id::text = current_org_id()` para consistencia.

2. **get_secret_async:** Plan asume existe pero solo está importado, no definido.  
   **Resolución:** Crear wrapper async `get_secret_async(org_id, secret_name)` que llame al síncrono en thread pool.

3. **tool_registry.register API:** Plan llama como método `register(name=..., tool_class=...)` pero es decorador `@register(name=...)`.  
   **Resolución:** Usar decorador en la definición de clase, o buscar método alternativo de registro.

4. **activity_logs table:** Plan asume existe para auditoría pero no está creada.  
   **Resolución:** Crear migración 024 incluye activity_logs o usar tabla existente como domain_events.

5. **mcp dependency:** Plan requiere `mcp>=1.0.0` directa pero está como transitiva.  
   **Resolución:** Agregar a pyproject.toml como dependencia directa.

## 1. Diseño Funcional

### Happy Path Principal
1. **Setup DB:** Crear 3 tablas con RLS, índices y FK validadas
2. **Población:** Import script lee JSON canónico, extrae ~20 proveedores y 50 tools, inserta en DB sin errores
3. **Ejecución:** ServiceConnectorTool recibe `tool_id`, lee definición de `service_tools`, verifica servicio activo, resuelve secreto del Vault, ejecuta HTTP, sanitiza output
4. **Monitoreo:** Health checks corren cada 30min, actualizan `last_health_status`, API retorna integraciones activas por org

### Edge Cases Relevantes para MVP
- **Servicio no activo:** Tool pertenece a proveedor que org no tiene habilitado → Error "servicio no activo"
- **Tool no encontrada:** `tool_id` no existe en `service_tools` → Error descriptivo
- **Secreto faltante:** `secret_names` definido pero no existe en Vault → Error HTTP auth
- **HTTP failure:** API externa retorna 4xx/5xx → Error con código y mensaje, logged
- **JSON malformado:** Seed JSON tiene schemas inválidos → Script falla con validación
- **Timeout:** API externa tarda >30s → Exception caught, logged como timeout
- **Health check fail:** Servicio retorna 500 → Status "error", no deshabilita automáticamente

### Manejo de Errores
- **Usuario ve:** Mensajes descriptivos en español sin exponer internals ("Error HTTP: 429 Rate limited")
- **Logging:** Errores técnicos con stack traces en logs del sistema
- **Recovery:** Tools con retry automático (3 intentos), circuit breaker para servicios fallidos
- **Fallback:** Si sanitizer falla, output vacío con warning logged

## 2. Diseño Técnico

### Componentes Nuevos
- **Migración 024_service_catalog.sql:** 3 tablas + RLS + índices (basado en patrón migration/005_org_mcp_servers.sql)
- **scripts/import_service_catalog.py:** Script standalone con extract_providers(), extract_tools(), validación FK
- **src/mcp/sanitizer.py:** Función pura sanitize_output() con regex patterns para secrets conocidos
- **src/tools/service_connector.py:** OrgBaseTool genérico, lee execution de DB, integra con Vault y sanitizer
- **src/jobs/health_check.py:** APScheduler job async que actualiza last_health_check/status
- **src/api/routes/integrations.py:** 3 endpoints FastAPI para catálogo y integraciones activas

### Interfaces (basadas en código verificado)
- **ServiceConnectorTool._run(tool_id: str, input_data: dict) → str:** Input Pydantic BaseModel, output string sanitizado
- **get_secret_async(org_id: str, secret_name: str) → str:** Wrapper async del síncrono existente
- **sanitize_output(data: Any) → Any:** Recursivo, patterns regex para Stripe keys, Bearer tokens, etc.
- **tool_registry.register() compatibilidad:** Usar patrón existente de decorador o encontrar método register_tool()

### Modelos de Datos
- **service_catalog:** Global, sin RLS, ~20 registros (proveedores)
- **org_service_integrations:** Per-org con RLS, FK a organizations(id), status enum
- **service_tools:** Global, sin RLS, ~50 registros con execution JSONB y input/output schemas

### Coherencia con estado-fase.md
- ✅ Implementa exactamente el paso 5.2.5 "Service Catalog TIPO C"
- ✅ Usa Vault existente para secretos (Regla R3)
- ✅ OrgBaseTool existente como base
- ✅ RLS pattern consistente con tablas existentes
- ❌ Corrije discrepancias: agrega get_secret_async, activity_logs, mcp directa

**Corrección necesaria:** estado-fase.md menciona "python-jose" pero código usa PyJWT. Actualizar pyproject.toml para remover python-jose si no se usa.

## 3. Decisiones

### Decisiones Nuevas (no en estado-fase.md)
1. **Wrapper get_secret_async:** Crear función async que delegue al síncrono en ThreadPoolExecutor. Justificación: MCP Pool requiere async para no bloquear event loop.

2. **Activity Logs en domain_events:** Usar tabla existente `domain_events` para auditoría en vez de nueva `activity_logs`. Justificación: Evita migración extra, consistente con patrón existente de eventos.

3. **Tool Registry API:** Usar `@tool_registry.register` como decorador en ServiceConnectorTool class. Justificación: Mantiene consistencia con patrón existente en registry.py.

4. **Health Check Frequency:** 30 minutos fijo. Justificación: Balance entre monitoreo proactivo y carga en APIs externas.

5. **Error Status Mapping:** HTTP 4xx → "error", 5xx → "error", timeout → "timeout". Justificación: Granularidad suficiente para debugging sin complejidad excesiva.

### Correcciones al Plan (basadas en código real)
1. **Corrige §10.5.2 RLS:** Usar `org_id::text = current_org_id()` en vez de `current_setting('app.current_org_id')::UUID`.
2. **Corrige dependencias:** Agregar `mcp>=1.0.0` directa a pyproject.toml.
3. **Corrige auditoría:** Usar `domain_events` existente en vez de `activity_logs` nueva.

## 4. Criterios de Aceptación
- Las 3 tablas existen con RLS activo y FK validadas
- 50 tools importadas sin huérfanos (cada tool tiene provider válido)
- ServiceConnectorTool ejecuta tool leyendo de DB + resuelve secreto + sanitiza output
- Output nunca contiene secrets (Stripe keys, Bearer tokens, etc.)
- Health checks actualizan status cada 30min
- GET /api/integrations/active retorna solo servicios activos de la org
- Ejecuciones auditadas en domain_events
- Tests pasan: sanitizer atrapa secrets, connector rechaza servicios inactivos

## 5. Riesgos

### Riesgos Técnicos
- **Riesgo Alto:** Discrepancia RLS pattern - si se usa patrón incorrecto, isolation falla. Mitigación: Test manual de RLS policies.
- **Riesgo Medio:** get_secret_async no definido - import error en MCP Pool. Mitigación: Implementar wrapper antes de cualquier test.
- **Riesgo Medio:** Tool registry API mismatch - ServiceConnectorTool no se registra. Mitigación: Verificar registro manual tras implementación.

### Riesgos de Integración
- **Riesgo Alto:** activity_logs no existe - auditoría falla. Mitigación: Usar domain_events existente como alternativa validada.
- **Riesgo Bajo:** Seed JSON issues - import falla. Mitigación: Validación JSON Schema antes de commit.

### Riesgos de Discrepancias Plan vs Código
- **Riesgo Medio:** Varias correcciones necesarias - delay en implementación. Mitigación: Documentar todas las correcciones upfront.

## 6. Plan

### Tareas Atómicas
1. **Crear get_secret_async wrapper** (30min, Baja) - Función async en vault.py
2. **Actualizar pyproject.toml** (15min, Baja) - Agregar mcp>=1.0.0, remover python-jose si no usado
3. **Migración 024_service_catalog.sql** (45min, Media) - 3 tablas + RLS + índices + test inserts
4. **src/mcp/sanitizer.py** (30min, Baja) - Función sanitize con patterns regex
5. **scripts/import_service_catalog.py** (1h, Media) - Extract functions + main + validaciones
6. **src/tools/service_connector.py** (2h, Alta) - OrgBaseTool completo + test mock
7. **Registro ServiceConnectorTool** (30min, Baja) - Resolver API registry y registrar
8. **src/jobs/health_check.py** (1h, Media) - Job APScheduler + actualización DB
9. **src/api/routes/integrations.py** (45min, Media) - 3 endpoints FastAPI
10. **Tests E2E** (1h, Media) - ServiceConnectorTool con datos reales
11. **Verificación final** (30min, Baja) - Health checks corriendo, API funcional

**Total estimado:** 8-10h (ajustado por correcciones necesarias)

### Dependencias
- 1 → 3 (get_secret_async antes de migration si usa Vault)
- 3 → 5 (tablas antes de import)
- 5 → 6 (seed data antes de connector)
- 6 → 7 (implementación antes de registro)
- 7 → 10 (registro antes de tests)

## 🔮 Roadmap (NO implementar ahora)
- **Rate limiting:** Por org/servicio para evitar abuso
- **Caching tool definitions:** En Redis para performance
- **Bulk operations:** Ejecutar múltiples tools en batch
- **Custom auth flows:** OAuth flows complejos más allá de API key
- **Service discovery:** Auto-detección de nuevos proveedores
- **Analytics:** Métricas de uso por tool/servicio
- **Versioning:** Soporte para múltiples versiones de tools
- **Testing sandbox:** Entorno de test con mocks para development</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md