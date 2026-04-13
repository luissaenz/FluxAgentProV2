# Análisis Técnico: Paso 4.3 - Implementación de AnalyticalCrew

## 1. Diseño Funcional

### Happy Path Detallado
1. El usuario formula una pregunta analítica en lenguaje natural a través del AnalyticalAssistantChat (paso 4.4).
2. El crew recibe el `query_type` (ej. "agent_success_rate") y parámetros opcionales.
3. Se ejecuta la consulta SQL pre-validada contra la base de datos del tenant.
4. Los resultados se enriquecen con metadata (timestamp, org_id, row_count).
5. Se retorna una respuesta estructurada con los datos analíticos.

### Edge Cases Relevantes para MVP
- **Consulta sin resultados:** Retorna lista vacía con metadata indicando 0 rows.
- **Parámetros inválidos:** Valida que `query_type` esté en allowlist; lanza ValueError si no.
- **Errores de base de datos:** Capturados implícitamente por el tenant client; en caso de fallo, se propaga la excepción.
- **Consultas complejas:** Limitadas a allowlist predefinido; no soporta queries arbitrarias por seguridad.

### Manejo de Errores
- **Query no permitida:** ValueError con lista de queries disponibles.
- **Fallo en DB:** Excepción del cliente Supabase se propaga; el chat debe manejarla mostrando mensaje de error genérico.
- **EventStore no disponible:** Método `query_events` maneja gracefully, retornando solo datos de DB.

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Nuevo archivo:** `src/crews/analytical_crew.py` con clase `AnalyticalCrew`.
- **No hereda patrón estándar:** No usa CrewAI agents/tasks; es una implementación directa para análisis SQL.
- **Integración existente:** Usa `get_tenant_client` y `EventStore` ya implementados.

### Interfaces (Inputs/Outputs de Cada Componente)
- **Input de `analyze()`:** `query_type: str`, `params: Optional[Dict[str, Any]]`
- **Output de `analyze()`:** `Dict[str, Any]` con keys: `query_type`, `executed_at`, `org_id`, `data`, `metadata`
- **Input de `query_events()`:** `event_type`, `aggregate_type`, `limit`
- **Output de `query_events()`:** `List[Dict[str, Any]]` con eventos de DB + memoria

### Modelos de Datos Nuevos o Extensiones
- **No nuevos modelos:** Reutiliza tablas existentes (`tasks`, `tickets`, `domain_events`, `agent_catalog`).
- **Formato de respuesta:** Estructura consistente con campos `role`, `count`, `success_rate`, etc., según query.

### Coherencia con Contratos Existentes
- **Tenant isolation:** Respeta `org_id` y `user_id` en todas las consultas.
- **RLS:** Usa `get_tenant_client` que aplica Row Level Security.
- **EventStore:** Integra con `EventStore` existente para eventos en memoria + DB.
- **No contradice estado-fase:** No modifica contratos vigentes; añade funcionalidad nueva.

## 3. Decisiones

- **Allowlist de queries:** Solo 5 queries predefinidas para seguridad; evita SQL injection y limita complejidad.
- **No SQL raw en Supabase:** Usa PostgREST queries en lugar de raw SQL; asume RPC functions para producción.
- **Agregación en Python:** Para MVP, calcula estadísticas en código (ej. success_rate) en lugar de SQL complejo.
- **Lazy-init EventStore:** Solo inicializa cuando se necesita para optimizar recursos.
- **Limit en queries:** Máximo 10-20 resultados para evitar sobrecarga en UI.

## 4. Criterios de Aceptación
- El método `analyze()` ejecuta correctamente las 5 queries allowlisted sin errores.
- Las consultas retornan datos agrupados y ordenados según especificación (ej. success_rate DESC).
- El `query_events()` combina eventos de memoria y DB, limitado a 100 por defecto.
- Los resultados incluyen metadata completa (executed_at, row_count, query_template).
- Las consultas respetan aislamiento por `org_id` y no acceden a datos de otras organizaciones.
- En caso de query_type inválido, se lanza ValueError con mensaje descriptivo.

## 5. Riesgos

- **Modificación de código protegido:** Archivo en `src/crews/` está bloqueado por CLAUDE.md; requiere issue y aprobación manual del propietario.
- **Asunciones de Supabase:** Código asume PostgREST queries; si cambia la capa DB, requiere refactor completo.
- **Volumen de datos:** Agregación en Python funciona para MVP pero puede ser ineficiente con miles de registros; riesgo de timeouts.
- **Seguridad de queries:** Allowlist limita pero no elimina riesgos; queries mal diseñadas podrían exponer datos sensibles.
- **Dependencia de EventStore:** Si EventStore falla, `query_events` degrada gracefully pero pierde eventos en memoria.

## 6. Plan

1. **Crear issue en repo:** Describir necesidad de modificar `src/crews/analytical_crew.py` (baja complejidad, 1h).
2. **Revisar implementación actual:** Verificar que métodos `_query_*` usen correctamente el tenant client (baja complejidad, 2h).
3. **Probar queries allowlisted:** Ejecutar cada query manualmente y validar resultados contra DB (media complejidad, 3h).
4. **Integrar con EventStore:** Asegurar que `query_events()` funcione con eventos recientes (baja complejidad, 2h).
5. **Añadir logging:** Incluir logs de ejecución para debugging en producción (baja complejidad, 1h).
6. **Code review:** Revisar seguridad y performance con propietario (media complejidad, 2h).

## 🔮 Roadmap
- **RPC functions:** Migrar queries complejas a stored procedures en Supabase para mejor performance.
- **NLP parsing:** Extender para interpretar queries arbitrarias en lenguaje natural usando LLM.
- **Dashboards pre-built:** Crear visualizaciones automáticas basadas en queries comunes.
- **Caching:** Implementar cache Redis para queries frecuentes y reducir carga en DB.
- **Multi-tenant analytics:** Permitir queries cross-org con permisos administrativos.
- **Event correlation:** Análisis de secuencias de eventos para detectar patrones de fallo.</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md