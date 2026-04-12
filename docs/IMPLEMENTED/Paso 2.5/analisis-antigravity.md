# 🧠 ANÁLISIS TÉCNICO: Paso 2.5 - Verificación de Aislamiento Multi-tenant (SOUL)

## 1. Diseño Funcional

### Happy Path Detallado
El objetivo es garantizar que la identidad narrativa (SOUL) de un agente sea privada para su organización y no se filtre a otras organizaciones que tengan agentes con el mismo rol técnico.

1.  **Configuración de Test:**
    *   **Org Alpha:** Posee un agente `analyst` con nombre "Archivista Alpha" y narrativa "Especialista en logs de alta densidad".
    *   **Org Beta:** Posee un agente `analyst` con nombre "Cerebro Beta" y narrativa "Focalizado en optimización de costos".
2.  **Solicitud Legítima (Alpha):**
    *   Usuario de Org Alpha consulta `GET /agents/{id-alpha}/detail`.
    *   **Resultado:** Recibe "Archivista Alpha".
3.  **Solicitud Cruzada (Intento de fuga):**
    *   Usuario de Org Alpha intenta consultar el `agent_id` perteneciente a Org Beta.
    *   **Resultado esperado:** La API retorna `404 Not Found` porque el primer filtro (`.eq("id", agent_id).eq("org_id", org_id)`) falla en `agent_catalog`.
4.  **Validación de RLS (Nivel DB):**
    *   Incluso si alguien saltara la lógica de la API, una consulta directa a `agent_metadata` con el contexto de sesión de Org Alpha NO debe devolver registros de Org Beta.

### Edge Cases (MVP)
*   **Agente sin Metadata:** Si una organización crea un agente pero no ha personalizado su SOUL, el sistema debe retornar los fallos de resiliencia (nombres capitalizados por defecto) sin error 500.
*   **Colisión de Roles:** Verificar que dos agentes con el mismo `agent_role` pero distinto `org_id` no mezclen sus narrativas en el Join.

### Manejo de Errores
*   **Error 404:** Se debe retornar cuando un `agent_id` no pertenece a la organización enviada en la cabecera `X-Org-Id`.
*   **Logging:** Cualquier fallo en el lookup de metadata debe loguearse como `warning` pero NO bloquear el retorno de las métricas del agente (implementado en `src/api/routes/agents.py`).

---

## 2. Diseño Técnico

### Componentes Involucrados
*   **Backend Router (`src/api/routes/agents.py`):** Utiliza `get_tenant_client(org_id)` que inyecta el contexto de RLS.
*   **Database Table (`agent_metadata`):** Posee política `agent_metadata_tenant_isolation` basada en `current_setting('app.org_id')`.
*   **Script de Test (`LAST/test_2_5_isolation.py`):** Script ligero para validar el comportamiento sin levantar todo el frontend.

### Interfaces
*   **Endpoint:** `GET /agents/{agent_id}/detail`
*   **Cabecera Obligatoria:** `X-Org-Id` (UUID).

### Modelos de Datos (Modificaciones)
*   No se requieren cambios en el esquema. La restricción `UNIQUE(org_id, agent_role)` en `agent_metadata` es la pieza clave para el lookup exacto por tenant.

---

## 3. Decisiones

1.  **Validación vía Pytest:** Se decide utilizar una prueba de integración que interactúe con el cliente Supabase simulando el cambio de `org_id`.
2.  **Aislamiento en dos niveles:**
    *   **Nivel 1 (Aplicación):** Filtros explícitos `.eq("org_id", org_id)` en las queries de FastAPI.
    *   **Nivel 2 (Datos):** Políticas RLS en PostgreSQL para defensa en profundidad.

---

## 4. Criterios de Aceptación (Binarios)

1.  ¿El endpoint retorna `404` si el `agent_id` existe en la base de datos pero pertenece a otra `org_id`? (Sí/No)
2.  ¿La respuesta del agente incluye los campos `display_name` y `soul_narrative` específicos de la organización solicitante? (Sí/No)
3.  ¿La tabla `agent_metadata` tiene habilitado RLS? (Sí/No)
4.  ¿Se usa `maybe_single()` o `single()` con filtro de `org_id` para evitar leaks por roles duplicados en la tabla de metadata? (Sí/No)

---

## 5. Riesgos

*   **Riesgo:** La política de RLS usa `current_setting('app.org_id', TRUE)`. Si esta variable no se setea (ej. bug en `TenantClient`), la política podría fallar silenciosamente permitiendo acceso total si no se maneja el caso `NULL`.
    *   *Mitigación:* La política debe estar diseñada para que si `app.org_id` no coincide, el resultado sea vacío. (Verificado en migración 020).
*   **Riesgo:** Confusión en tests por uso de `service_role`.
    *   *Mitigación:* Asegurar que el script de test use el flujo de `TenantClient` y no el `service_client` directamente para las verificaciones de aislamiento.

---

## 6. Plan de Ejecución

1.  **Tarea 1:** Crear `LAST/test_2_5_isolation.py` con dos casos de prueba: uno para acceso exitoso y otro para acceso denegado entre organizaciones. (Complejidad: Baja)
2.  **Tarea 2:** Ejecutar el test y capturar logs de Supabase si es posible para confirmar la activación del RLS. (Complejidad: Baja)
3.  **Tarea 3:** Generar reporte de validación final `LAST/validacion-2-5.md`. (Complejidad: Baja)

---

## 🔮 Roadmap (Fuera de MVP)
*   **Auditoría de Acceso:** Registrar intentos de acceso cross-tenant en una tabla de auditoría para seguridad.
*   **Metadata Global:** Permitir marcas de agentes "globales" (de sistema) que sean visibles por todas las organizaciones pero editables solo por admins.
