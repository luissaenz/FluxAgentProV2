# 🧠 ANÁLISIS TÉCNICO — Sprint 5: Expansión de Catálogo (~226 tools)

**Paso:** String 5 (Sprint 5)
**Agente:** atg

---

## 0. Verificación contra Código Fuente

### Exploración Inicial

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Seed de Catálogo | `data/service_catalog_seed.json` | ✅ | Archivo existe, **216 tools** detectadas (vía grep `input_schema`). |
| 2 | Script de Importación | `scripts/import_service_catalog.py` | ✅ | Archivo existe con lógica de upsert y corrección de schemas. |
| 3 | Tabla `service_catalog` | `migrations/024_service_catalog.sql` | ✅ | Estructura validada en Sprint 2. |
| 4 | Tabla `service_tools` | `migrations/024_service_catalog.sql` | ✅ | Estructura validada en Sprint 2. |
| 5 | Route `integrations` | `src/api/routes/integrations.py` | ✅ | Endpoints `/available`, `/active` y `/tools/{id}` operativos. |

### Hallazgos Clave
- El catálogo actual cuenta con **216 tools** distribuidas en ~40 categorías.
- Faltan **10 tools** para alcanzar el objetivo de ~226 definido en el `plan.md`.
- El script de importación realiza una limpieza automática de schemas (`fix_required_schema`).
- Todas las herramientas actuales (216/216) cuentan con `tool_profile` completo (description, risk_level, requires_approval).

---

## 1. Diseño Funcional

### 1.1 Objetivo
Completar la expansión del catálogo de servicios TIPO C para dotar a los agentes de capacidades en áreas de nicho (DevOps, LegalTech, FinTech Avanzado) y asegurar la integridad total de los datos antes del cierre de la fase.

### 1.2 "Ronda 3" de Expansión
Se proponen 10 nuevas tools para cerrar la brecha:
1. **GitHub:** `create_pull_request` (DevOps).
2. **GitHub:** `add_comment_to_issue` (DevOps).
3. **Linear:** `create_issue` (Project Management).
4. **Resend:** `send_transactional_email` (Email).
5. **LemonSqueezy:** `get_license_key` (Ecommerce).
6. **Twilio:** `send_whatsapp_message` (Messaging).
7. **PostHog:** `capture_event` (Analytics).
8. **Sentry:** `list_recent_errors` (DevOps).
9. **DocuSign:** `create_envelope_from_template` (LegalTech).
10. **Zoom:** `create_meeting` (Meetings).

### 1.3 Calidad de Datos
Cada nueva tool debe seguir el estándar:
- `id` jerárquico (`proveedor.accion`).
- `input_schema` con tipos correctos y descripciones útiles.
- `execution` con método HTTP, URL (soporta placeholders) y headers.
- `tool_profile` con `risk_level` verificado.

---

## 2. Diseño Técnico

### 2.1 Componentes a Modificar
- `data/service_catalog_seed.json`: Inserción de los nuevos objetos JSON.
- `scripts/import_service_catalog.py`: Mejora en la función `verify_integrity` para validar que las URLs de ejecución usen HTTPS.

### 2.2 Flujo de Importación
1. Backup de la tabla `service_tools` (vía Supabase Dashboard o script).
2. Edición manual/generada del seed JSON.
3. Ejecución: `python -m scripts.import_service_catalog`.
4. Verificación de logs: Asegurar "SUCCESS" y tool count = 226.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| 1 | **Completar a 226 tools exactas** | Cumplimiento estricto del Roadmap definido en `plan.md`. |
| 2 | **No modificar el schema de la DB** | El diseño de Sprint 2 ha demostrado ser suficiente para la expansión. |
| 3 | **Validación de HTTPS obligatoria** | Seguridad: No se permiten integraciones vía HTTP plano para proteger keys/tokens. |
| 4 | **Uso de `upsert` persistente** | Permite re-ejecutar el script sin duplicar datos ni perder integraciones existentes de usuarios. |

---

## 4. Criterios de Aceptación (MVP)

### Funcionales
- [ ] El seed JSON contiene al menos 226 herramientas únicas.
- [ ] El script de importación finaliza con estado "SUCCESS".
- [ ] La tabla `service_tools` en Supabase refleja exactamente 226 registros.

### Técnicos
- [ ] 100% de las nuevas herramientas usan HTTPS en su campo `execution.url`.
- [ ] 100% de las nuevas herramientas tienen un `input_schema` válido (tipo `object`).
- [ ] No existen herramientas "huérfanas" (sin un `service_id` válido en `service_catalog`).

---

## 5. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| 1 | **Escalabilidad de la UI** | Listar 226 herramientas en un solo combo-box puede ser lento. | El frontend debe implementar filtrado por categoría o búsqueda texto (ya soportado por API integrations.py). |
| 2 | **Tokens de prueba** | Las 10 nuevas tools requieren ser testearlas para verificar que los endpoints existen. | Verificación manual de los docs de los proveedores elegidos (GitHub, Twilio, etc). |
| 3 | **Colisión de IDs** | IDs duplicados en el seed. | El script de importación detecta duplicados vía `upsert` y logs de integridad. |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|
| 1 | Investigar y redactar las 10 tools faltantes (GitHub, Twilio, etc). | Media | 2h | - |
| 2 | Actualizar `data/service_catalog_seed.json`. | Baja | 1h | 1 |
| 3 | Agregar validación HTTPS a `scripts/import_service_catalog.py`. | Baja | 30m | - |
| 4 | Ejecutar importación y verificar integridad. | Baja | 30m | 2, 3 |

**Total estimado:** 4 horas.

---

**Idioma:** Español 🇪🇸
**Documento generado:** `/home/daniel/develop/Personal/FluxAgentProV2/docs/Sprint 5 — Expansión de Catálogo/analisis-atg.md`
