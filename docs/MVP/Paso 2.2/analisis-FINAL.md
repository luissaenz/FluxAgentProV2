# 🏛️ ANÁLISIS FINAL: PASO 2.2 - EVOLUCIÓN ENDPOINT AGENTS (BACKEND)

## 1. Resumen Ejecutivo
Este paso consolida la integración de la identidad narrativa (SOUL) en el backend. Se modificará el endpoint `GET /agents/{agent_id}/detail` en `src/api/routes/agents.py` para que, además de los datos técnicos del catálogo y las métricas de rendimiento, devuelva la metadata personalizada (personalidad, nombre amigable y avatar) de la tabla `agent_metadata`.

## 2. Diseño Funcional Consolidado
- **Propósito**: Proveer al frontend toda la información necesaria para renderizar la "Personality Card" del agente en una sola llamada.
- **Enriquecimiento Dinámico**: La respuesta del agente ya no será puramente técnica; ahora tendrá una "capa humana" (display_name y soul_narrative).
- **Graceful Fallback**: 
    - Si `agent_metadata` no existe para un rol, el endpoint utilizará el `role` de `agent_catalog` como `display_name` y dejará `soul_narrative` como una cadena informativa genérica o nula.
- **Impacto UX**: Los usuarios verán agentes con "nombre y apellido" y una descripción de su propósito en lugar de solo identificadores técnicos.

## 3. Diseño Técnico Definitivo
- **Localización**: `src/api/routes/agents.py`.
- **Lógica de Consulta**:
    1. Se mantiene la consulta inicial a `agent_catalog` por `id`.
    2. Una vez obtenido el `agent_role` y el `org_id`, se realiza una consulta secundaria a `agent_metadata`.
    3. Se utiliza el patrón `db.table("agent_metadata").select("*").eq("org_id", org_id).eq("agent_role", role).maybe_single().execute()`.
- **Merging**:
    - Se inyectarán los campos `display_name`, `soul_narrative` y `avatar_url` directamente en el diccionario `agent` de la respuesta.
    - Esto permite que el frontend consuma `data.agent.soul_narrative` de forma natural.
- **Gestión de Errores**:
    - Se capturarán excepciones en la consulta de metadata para asegurar que un fallo en la tabla de identidad no bloquee la visualización de métricas críticas.

## 4. Decisiones
- **Consultas Secuenciales vs Join SDK**: Se elige la consulta secuencial. Aunque el SDK de Supabase permite `.select("*, agent_metadata(*)")`, esto requiere una estructura de FK perfecta que en relaciones lógicas de texto (`role`) puede ser frágil. La consulta secuencial es más controlable y permite implementar los fallbacks fácilmente en Python.
- **Estructura Plana en el JSON**: Los datos de identidad se mezclan con los del catálogo en la clave principal `agent` para facilitar el mapping en componentes React preexistentes.

## 5. Criterios de Aceptación ✅
1. **Presencia de SOUL**: La respuesta JSON incluye los campos `display_name`, `soul_narrative` y `avatar_url` dentro de la clave `agent`. [ ]
2. **Resiliencia a Nulos**: Si un agente no tiene registro en `agent_metadata`, el endpoint responde exitosamente (200 OK) con valores por defecto o nulos en esos campos. [ ]
3. **Mantenimiento de Métricas**: Las métricas de `total_tokens` y `recent_tasks` siguen funcionando correctamente sin interferencia de la nueva lógica. [ ]
4. **Seguridad Multi-tenant**: El enriquecimiento solo devuelve metadata perteneciente al `org_id` de la sesión activa. [ ]

## 6. Plan de Implementación
1. **Tarea 1**: Modificar `get_agent_detail` en `src/api/routes/agents.py` para realizar el fetching de metadata (Baja).
2. **Tarea 2**: Implementar lógica de merge con valores por defecto (Baja).
3. **Tarea 3**: Validar mediante script de integración que un agente configurado en el Paso 2.1 devuelve su SOUL correctamente (Media).

## 7. Riesgos y Mitigaciones
- **Sobrecarga de I/O**: Dos consultas a la DB por cada detalle de agente.
    - *Mitigación*: Ambas consultas usan índices primarios o compuestos (`id` y `org_id + agent_role`), garantizando tiempos de respuesta mínimos (<20ms).
- **Consistencia**: Un cambio en el rol del catálogo invalida el link de metadata.
    - *Mitigación*: Se asume que el cambio de rol es una operación mayor que requiere "re-identificar" al agente.

## 8. Testing Mínimo Viable
- Consultar un agente con metadata (debe mostrar el SOUL).
- Consultar un agente sin metadata (debe mostrar campos base).
- Simular un error en la tabla `agent_metadata` (debe seguir devolviendo métricas básicas).

## 9. 🔮 Roadmap (NO implementar ahora)
- **Caching**: Implementar un cache de 60s para la metadata ya que cambia poco.
- **GraphQL**: Si el panel crece, migrar a una query consolidada para evitar multiples hits.
