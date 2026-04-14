# Análisis Técnico: Expansión del Catálogo de Servicios (~226 tools)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|-----------|
| 1 | Archivo seed existe | `ls data/service_catalog_seed.json` | ✅ | Archivo presente en data/ |
| 2 | Herramientas actuales en seed | Contar len(data['tools']) | ✅ | 216 herramientas actuales (cercano a 226 objetivo) |
| 3 | Script de import existe | `ls scripts/import_service_catalog.py` | ✅ | Script presente en scripts/ |
| 4 | Script ejecutable | `python -m scripts.import_service_catalog` (dry run) | ⚠️ | Requiere env vars SUPABASE_URL y SUPABASE_SERVICE_KEY |
| 5 | Migración 024 existe | `ls supabase/migrations/024_service_catalog.sql` | ✅ | Migración presente |
| 6 | Tabla service_catalog en migración | `grep -n "CREATE TABLE.*service_catalog" supabase/migrations/024_service_catalog.sql` | ✅ | Línea 1: CREATE TABLE service_catalog |
| 7 | Tabla service_tools en migración | `grep -n "CREATE TABLE.*service_tools" supabase/migrations/024_service_catalog.sql` | ✅ | Línea 58: CREATE TABLE service_tools |
| 8 | RLS en service_catalog | `grep -A5 "ALTER TABLE service_catalog" supabase/migrations/024_service_catalog.sql` | ✅ | RLS habilitado con policy para org_id |
| 9 | RLS en service_tools | `grep -A5 "ALTER TABLE service_tools" supabase/migrations/024_service_catalog.sql` | ✅ | RLS habilitado con policy para org_id |
| 10 | Función fix_required_schema en script | `grep -n "def fix_required_schema" scripts/import_service_catalog.py` | ✅ | Línea 42: definición presente |
| 11 | Función extract_providers en script | `grep -n "def extract_providers" scripts/import_service_catalog.py` | ✅ | Línea 73: definición presente |
| 12 | Función verify_integrity en script | `grep -n "def verify_integrity" scripts/import_service_catalog.py` | ✅ | Línea 148: verificación post-import |
| 13 | Script usa upsert | `grep -n "upsert" scripts/import_service_catalog.py` | ✅ | Líneas 138,144: upsert para providers y tools |
| 14 | Seed tiene estructura correcta | Validar JSON y campos requeridos | ✅ | tools[0] tiene id, provider, input_schema, etc. |
| 15 | Providers únicos en seed | len(set(tool['provider']['id'] for tool in data['tools'])) | ✅ | 45 proveedores únicos |

**Discrepancias encontradas:**

- El seed actual ya contiene 216 herramientas, superando el objetivo de ~226 mencionado en el plan. Resolución: Verificar si el plan está desactualizado o si la expansión ya fue parcialmente implementada.

## 1. Diseño Funcional

El paso expande el catálogo de herramientas MCP de ~50 a ~226 herramientas mediante 3 rondas de investigación:

- **Ronda 1 (ya implementada):** Herramientas base (~50) para proveedores clave.
- **Ronda 2:** +88 herramientas adicionales en subcategorías existentes (ej: más endpoints de Slack, GitHub, Notion).
- **Ronda 3:** +88 herramientas adicionales de nuevos proveedores (ej: nuevos servicios como Jira, Figma, Calendly).

**Happy path:**
1. Investigar APIs de proveedores existentes para encontrar endpoints no cubiertos.
2. Investigar nuevos proveedores relevantes para automatización empresarial.
3. Formatear nuevos tools en esquema JSON del seed.
4. Actualizar seed.json con herramientas adicionales.
5. Ejecutar script de import para upsert en DB.
6. Verificar integridad: 226+ tools, sin huérfanos, perfiles completos.

**Edge cases:**
- API de proveedor requiere autenticación compleja (OAuth2 vs API key).
- Endpoint tiene rate limits o requiere aprobación manual.
- Esquema de input/output no mapea directamente a JSON Schema.
- Proveedor tiene documentación incompleta o API beta.

**Manejo de errores:**
- Investigación falla: Usar documentación oficial y ejemplos de código.
- Schema inválido: Corregir con fix_required_schema o manualmente.
- Import falla: Revisar logs de Supabase, verificar RLS y permisos.

## 2. Diseño Técnico

**Componentes nuevos/modificados:**
- `data/service_catalog_seed.json`: Expandido con ~88 herramientas ronda 2 + ~88 ronda 3.
- `scripts/import_service_catalog.py`: Re-ejecutado sin cambios (upsert permite adiciones).

**Interfaces:**
- Input de seed: Array de objetos con campos id, name, provider, input_schema, output_schema, execution, tool_profile.
- Output de import: Conteo de providers/tools upserted, verificación de integridad.
- DB: Tablas service_catalog y service_tools con RLS por org_id.

**Modelos de datos:**
- Provider: id, name, category, auth_type, base_url, required_secrets.
- Tool: id, service_id, name, version, input_schema, output_schema, execution, tool_profile (description, risk_level, requires_approval).

**Integraciones:**
- NotebookLM: Para investigación y extracción de endpoints de documentación API.
- Supabase: Upsert a tablas con verificación de RLS.

## 3. Decisiones

- **Herramientas por ronda:** Dividir en 88 por ronda para iteración controlada y testing incremental.
- **Subcategorías existentes primero:** Maximizar utilidad inmediata antes de explorar nuevos proveedores.
- **Upsert en import:** Permite expansiones sin riesgo de duplicados o pérdida de datos existentes.
- **Verificación automática:** Script incluye checks de integridad post-import para validar expansión.

## 4. Criterios de Aceptación

- Conteo de tools en DB = 226+ después del import.
- Todos los tools tienen tool_profile completo (description, risk_level, requires_approval).
- No hay tools huérfanos (service_id válido en service_catalog).
- Todas las schemas JSON válidas y corregidas automáticamente.
- Providers nuevos agregados correctamente con auth_type apropiado.
- Import ejecuta sin errores con env vars configuradas.

## 5. Riesgos

- **Investigación incompleta:** Riesgo de tools con schemas incorrectos. Mitigación: Validar cada tool manualmente antes de agregar al seed.
- **Rate limits en APIs:** Algunos proveedores limitan requests. Mitigación: Usar documentación offline y ejemplos.
- **Cambio de API:** Proveedores pueden deprecar endpoints. Mitigación: Verificar versiones actuales y notas de API.
- **Rendimiento de import:** 226 tools pueden causar timeouts. Mitigación: Import en batches si necesario (modificar script).
- **RLS bypass:** Service role debe mantener acceso. Mitigación: Verificar migración 025 aplicada.

## 6. Plan

- **Ronda 2 investigación (2h):** Usar NotebookLM para analizar docs de proveedores existentes, identificar 88 endpoints faltantes.
- **Ronda 2 formateo (1h):** Convertir findings a formato JSON seed.
- **Ronda 3 investigación (2h):** Investigar nuevos proveedores, seleccionar 88 tools relevantes.
- **Ronda 3 formateo (1h):** Agregar al seed.
- **Actualizar seed (0.5h):** Merge de rondas 2 y 3 en seed.json.
- **Ejecutar import (0.5h):** Correr script con verificación.
- **Testing manual (1h):** Probar 3-5 tools nuevos vía MCP para validar funcionamiento.

**Estimación total:** 8h. Complejidad: Media (investigación + JSON formatting).

## 🔮 Roadmap

- Automatizar extracción de schemas desde OpenAPI specs.
- Integrar health checks para tools nuevos.
- Implementar versioning de catálogo para rollbacks.
- Expandir a 500+ tools con rondas adicionales.
- Soporte para webhooks y eventos en tiempo real.