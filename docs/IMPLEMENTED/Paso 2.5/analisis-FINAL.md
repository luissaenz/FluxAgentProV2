# 🏛️ ANÁLISIS TÉCNICO FINAL: Paso 2.5 - Verificación de Aislamiento Multi-tenant (SOUL)

## 1. Resumen Ejecutivo
Este paso constituye la validación crítica de seguridad para la Fase 2 (Agent Panel 2.0). Tras haber implementado la personalidad de los agentes (SOUL) y enriquecido su UI, es imperativo garantizar que la identidad narrativa de un agente sea estrictamente privada por organización (Tenant). 

El objetivo es confirmar que, aunque dos organizaciones distintas (ej. "Bartenders Alpha" y "Drinks Beta") tengan un agente con el mismo rol técnico (`analyst`), los datos narrativos y visuales no se filtren entre ellas. Se implementará una estrategia de validación en dos capas: lógica de aplicación y políticas de Row Level Security (RLS) en base de datos.

## 2. Diseño Funcional Consolidado

### Happy Path Detallado
1.  **Escenario Base:**
    *   **Org Alpha:** Tiene un agente con rol `analyst` personalizado como "Sombra de Alpha" (Narrativa de espionaje).
    *   **Org Beta:** Tiene un agente con rol `analyst` personalizado como "Luz de Beta" (Narrativa de soporte legal).
2.  **Consulta Legítima:** Un usuario de Org Alpha solicita el detalle de su agente (`GET /agents/{id-alpha}/detail`). La respuesta muestra "Sombra de Alpha".
3.  **Aislamiento de Identidad:** El mismo usuario de Org Alpha intenta consultar el detalle usando el `id` de un agente de Org Beta. El sistema retorna `404 Not Found`.
4.  **Aislamiento de Metadata (Cruce de Nombres):** Si un agente no tiene `agent_id` único sino que se mapea por `agent_role`, se verifica que el JOIN con `agent_metadata` filtre estrictamente por el `org_id` del contexto actual.

### Edge Cases (MVP)
*   **Agente sin Metadata:** Si una organización no ha definido SOUL para un rol, el sistema debe retornar fallbacks (nombres capitalizados) sin filtrar datos de otra organización que sí los tenga.
*   **Bypass de API:** Intentar consultar la tabla `agent_metadata` directamente vía SQL con el contexto de sesión de una organización distinta no debe retornar registros (Verificación de RLS).

### Manejo de Errores
*   **HTTP 404:** Retorno estándar cuando el recurso no pertenece al tenant.
*   **Warning en Logs:** Si se detecta un intento de acceso cross-tenant (match de rol pero mismatch de org), se debe loguear para trazabilidad de seguridad.

## 3. Diseño Técnico Definitivo

### Arquitectura de Validación
Se empleará una estrategia de **Doble Capa de Verificación**:

1.  **Capa A (Lógica de Aplicación):**
    *   Uso de `FastAPI TestClient` para inyectar headers `X-Org-ID`.
    *   Verificación de que `src/api/routes/agents.py` propaga el `org_id` correctamente al `TenantClient`.
    *   Validación de que las queries select incluyen explícitamente `.eq("org_id", context_org_id)`.

2.  **Capa B (Seguridad de Datos - RLS):**
    *   Prueba técnica sobre la tabla `agent_metadata`.
    *   Simulación de sesión de base de datos (`app.org_id`) y verificación de que PostgreSQL filtra los resultados sin filtros explícitos en el `WHERE`.

### APIs y Contratos
*   **Endpoint:** `GET /agents/{id}/detail`
*   **Middleware:** `require_org_id` (encargado de la extracción del header).
*   **Contract:** Se mantiene el contrato definido en `estado-fase.md`.

### Componentes Involucrados
*   `src/api/routes/agents.py`: Endpoint principal bajo prueba.
*   `src/db/session.py`: `TenantClient` que gestiona el contexto `app.org_id`.
*   `supabase/migrations/020_agent_metadata.sql`: Definición de la política `agent_metadata_tenant_isolation`.

## 4. Decisiones Tecnológicas
*   **Framework de Test:** `pytest` con `httpx.AsyncClient` para simular llamadas al backend de forma asíncrona y eficiente.
*   **Script de Validación:** En lugar de un test manual propuesto en otros análisis, se creará un script automatizado `LAST/test_2_5_isolation.py` para asegurar que la validación sea reproducible en cualquier etapa.
*   **Mocks vs DB Real:** Se priorizará el uso de mocks para lógica de API, pero la validación de RLS (Capa B) requerirá una conexión a una instancia de Supabase/Postgres real o local controlada.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] La consulta de un agente externo a la organización autenticada (vía header `X-Org-ID`) retorna `404 Not Found`.
- [ ] La respuesta del agente incluye únicamente la personalidad (display_name/narrative) configurada para la organización solicitante.

### Técnicos
- [ ] Se verifica mediante logs o inspección de query que se llama a `.eq("org_id", org_id)` en el acceso a `agent_metadata`.
- [ ] Existe un script de test automatizado que valida el aislamiento con al menos dos organizaciones de prueba.
- [ ] La tabla `agent_metadata` tiene habilitado RLS y la política `agent_metadata_tenant_isolation` está activa en la base de datos.

### Robustez
- [ ] Si la tabla `agent_metadata` está vacía para una organización, el endpoint responde con los datos básicos del agente y `soul_narrative: null` sin errores.

## 6. Plan de Implementación
1.  **Tarea 1:** Crear el script de test `LAST/test_2_5_isolation.py` (Capa A). (Complejidad: Baja)
2.  **Tarea 2:** Implementar validación de RLS en el script mediante ejecución de RPC `set_config` (Capa B). (Complejidad: Media)
3.  **Tarea 3:** Ejecutar los tests en el entorno de desarrollo y capturar evidencias. (Complejidad: Baja)
4.  **Tarea 4:** Generar el reporte de validación final `LAST/validacion.md` para cierre de Paso 2.5. (Complejidad: Baja)

## 7. Riesgos y Mitigaciones
*   **Riesgo:** Error de configuración en RLS que permita acceso total si `app.org_id` no está seteado.
    *   **Mitigación:** La política de RLS debe usar el valor predeterminado `FALSE` si la variable de configuración es nula.
*   **Riesgo:** Fuga de información por caché agresivo en el frontend.
    *   **Mitigación:** Asegurar que los hooks de React Query incluyan el `org_id` en su `queryKey`.

## 8. Testing Mínimo Viable
*   **Caso 1:** Login Org 1 -> Get Agent Analyst -> Ver "Narrativa A".
*   **Caso 2:** Login Org 2 -> Get Agent Analyst -> Ver "Narrativa B".
*   **Caso 3:** Login Org 1 -> Get Agent Analyst (ID de Org 2) -> Ver 404.

## 9. 🔮 Roadmap
*   **Auditoría de Seguridad Automatizada:** Escaneo periódico de todas las tablas críticas para confirmar que RLS sigue activo y sin bypasses.
*   **Testing E2E con Playwright:** Incorporar el flujo multi-tenant en la suite de pruebas de interfaz de usuario.
