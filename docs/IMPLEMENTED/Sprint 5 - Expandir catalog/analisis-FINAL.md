# 🏛️ ANÁLISIS UNIFICADO — Sprint 5: Expansión de Catálogo (~226 tools)

## 0. Evaluación de Análisis y Verificaciones

### Tabla de Evaluación

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|
| kilo | ✅ | 2 Encontradas (Rutas, Secretos) | ✅ L11/L118 script | 5 |
| atg | ✅ | 1 Encontrada (HTTPS req) | ✅ script integrity | 4 |
| qwen | ✅ | 1 Encontrada (Count gap) | ✅ grep results | 4 |

### Discrepancias Críticas y Hallazgos Propios

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `expand_catalog.py` no encuentra prompts | kilo | ✅ `scripts/expand_catalog.py:11` busca en root `docs/` | Corregir `DOCS_DIR` a `docs/Sprint 2 - Expansion of Service Catalog/`. |
| 2 | Naming de secretos inconsistente | kilo | ✅ `scripts/expand_catalog.py:60` usa hardcode `{provider_id}_api_key` | Unificar el mapeo de secretos según el tipo de auth (API Key, OAuth, Basic). |
| 3 | Riesgo de URLs inseguras (HTTP) | atg | ✅ `scripts/import_service_catalog.py` no valida protocolo | Agregar validación HTTPS mandatoria en `verify_integrity`. |
| 4 | Brecha de 10 herramientas (~216 actual) | qwen / atg | ✅ `grep -c "input_schema"` retorna 216 | Generar tools para GitHub, Twilio, Zoom y Resend hasta alcanzar 226. |

---

## 1. Resumen Ejecutivo
Este paso completa la expansión masiva del catálogo de servicios TIPO C (integración vía JSON-RPC/HTTP). El objetivo es alcanzar las **226 herramientas** funcionales, asegurando que el script de expansión lea correctamente los prompts y que el script de importación sea estricto con la seguridad (HTTPS) y la integridad de los metadatos (`tool_profile`). Se han identificado y resuelto fallos críticos en las rutas de los scripts de mantenimiento.

---

## 2. Diseño Funcional Consolidado

### Happy Path
1. **Generación:** Se ejecutan los prompts faltantes en NotebookLM para obtener las herramientas de GitHub, Twilio, Resend y Zoom.
2. **Expansión:** Se ejecuta `scripts/expand_catalog.py` (corregido) para consolidar los 5 prompts en `data/service_catalog_seed.json`.
3. **Importación:** Se ejecuta `scripts/import_service_catalog.py` (corregido) para sincronizar la base de datos Supabase.
4. **Verificación:** El sistema confirma la presencia de 226 tools únicas y el Dashboard permite filtrarlas por categoría.

### Manejo de Errores
- **Protocolo Inseguro:** Si una herramienta tiene una URL `http://`, el importador lanzará una excepción y detendrá el proceso de esa herramienta.
- **Conflictos de ID:** En caso de IDs duplicados entre prompts, el script de expansión aplicará una política de "Last Write Wins" (prompt5 prevalece sobre prompt1) con logging del conflicto.

---

## 3. Diseño Técnico Definitivo

### Modificaciones en Scripts

#### `scripts/expand_catalog.py`
- **Correction:** Actualizar `DOCS_DIR = BASE_DIR / "docs" / "Sprint 2 - Expansion of Service Catalog"`.
- **Optimization:** Normalizar consistentemente los `provider_id` (lowercase, sin espacios).

#### `scripts/import_service_catalog.py`
- **Validation:** En la función `extract_tools`, lanzar `ValueError` si `execution["url"]` no empieza con `https://`.
- **Integrity:** Actualizar `expected_tools` a 226.

### Metadatos de Herramientas (`tool_profile`)
Se exige que toda herramienta nueva cumpla el contrato:
- `risk_level`: Determina si requiere auditoría profunda.
- `requires_approval`: Forzado `true` para acciones de escritura/borrado (POST, PATCH, DELETE).

---

## 4. Decisiones Tecnológicas

| # | Decisión | Justificación |
|---|---|---|
| 1 | **HTTPS Mandatorio** | Protege el tráfico de tokens y datos sensibles entre FAP y los proveedores externos. **Corrige plan §5.** |
| 2 | **Upsert persistente por ID** | Permite actualizaciones parciales sin romper integraciones activas de organizaciones en `org_service_integrations`. |
| 3 | **Estandarización de Secretos** | Mapear `api_key` → `{id}_api_key` y `oauth2` → `{id}_token` facilita la configuración por parte del usuario final en el Dashboard. |

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El catálogo en base de datos cuenta exactamente con **226 herramientas**.
- [ ] Al menos 15 proveedores distintos están registrados en `service_catalog`.
- [ ] Herramientas críticas (GitHub, WhatsApp, Email) están presentes y tipificadas como `high` risk si eliminan datos.

### Técnicos
- [ ] `scripts/expand_catalog.py` puede localizar y procesar los 5 archivos de prompts.
- [ ] 0 herramientas "huérfanas" (herramientas sin proveedor válido).
- [ ] 100% de las herramientas tienen un `input_schema` válido para el MCP (tipo `object`).
- [ ] No existen URLs `http://` en ninguna definición de herramienta.

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Notas |
|---|---|---|---|
| 1 | **Fix Rutas:** Corregir `DOCS_DIR` en `expand_catalog.py`. | Baja | Evita que el script falle silenciosamente. |
| 2 | **Seguridad:** Implementar validación HTTPS en `import_service_catalog.py`. | Baja | Mandatorio para cumplimiento de seguridad. |
| 3 | **Data Entry:** Completar el Gap de 10 herramientas en `prompt5.txt`. | Media | Enfocado en GitHub, Twilio y Resend. |
| 4 | **Sincronización:** Ejecutar `expand_catalog.py` e `import_service_catalog.py`. | Baja | `python -m scripts.import_service_catalog`. |
| 5 | **Audit:** Ejecutar `verify_integrity` y documentar el éxito. | Baja | |

---

## 7. Riesgos y Mitigaciones
- **Riesgo:** Implementador copia el script `expand_catalog.py` del plan original sin corregir la ruta de prompts.
- **Mitigación:** Esta decisión está marcada como crítica en el reporte de unificación; el Validador rechazará si la ruta no apunta al folder de Sprint 2.
- **Riesgo:** Inconsistencia de providers (ej: `google_sheets` vs `google_sheets_api`).
- **Mitigación:** Se aplica normalización de strings en el script de expansión antes del `upsert`.
