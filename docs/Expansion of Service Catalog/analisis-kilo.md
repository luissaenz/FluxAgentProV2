# Análisis Técnico — Expansion of Service Catalog (TIPO C)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|----------|
| 1 | Archivos prompt1.txt a prompt4.txt existen | `ls docs/prompt*.txt` | ✅ | docs/prompt1.txt, docs/prompt2.txt, docs/prompt3.txt, docs/prompt4.txt |
| 2 | Esquema actual del seed es nested (provider object) | Leer data/service_catalog_seed.json | ✅ | Línea 6-14: provider como objeto con id, name, category, etc. |
| 3 | Script import lee de data/service_catalog_seed.json | Leer scripts/import_service_catalog.py | ✅ | Línea 24: seed_path = Path(__file__).parent.parent / "data" / "service_catalog_seed.json" |
| 4 | Tabla service_catalog existe con campos requeridos | Leer supabase/migrations/024_service_catalog.sql | ✅ | Líneas 8-22: id, name, category, auth_type, base_url, required_secrets[] |
| 5 | Tabla service_tools existe con campos requeridos | Leer supabase/migrations/024_service_catalog.sql | ✅ | Líneas 59-68: id, service_id, name, input_schema, output_schema, execution, tool_profile |
| 6 | ServiceConnectorTool lee de service_tools | Leer src/tools/service_connector.py | ✅ | Línea 64: db.table("service_tools").select(...) |
| 7 | Prompt files tienen estructura flat con tool_id, provider string | Leer docs/prompt1.txt líneas 87-91 | ✅ | tool_id, name, provider (string), category, auth object |
| 8 | Mapping tool_id -> id | Plan dice "tool_id -> id" | ✅ | Evidente en estructura |
| 9 | Mapping provider string -> provider object | Plan dice "provider (string) -> provider (object)" | ✅ | Necesita inferir id, category, auth_type, base_url |
| 10 | Mapping auth.type -> provider.auth_type | Plan dice "auth.type -> provider.auth_type" | ✅ | auth object en prompt -> auth_type en provider |
| 11 | Base URL desde execution.url | Plan dice "execution.url base part -> provider.base_url" | ✅ | Extraer base URL de URLs completas |
| 12 | Generar required_secrets | Plan dice "Generate required_secrets (e.g., [provider_id]_api_key)" | ✅ | Basado en auth_type |
| 13 | Deduplicación por ID | Plan dice "Deduplicate tools by ID" | ✅ | Priorizar archivos prompt más nuevos |
| 14 | Seed actual tiene ~50 tools | Contar en data/service_catalog_seed.json | ✅ | 50 tools encontrados (grep "id": en tools) |
| 15 | Import usa upsert con on_conflict="id" | Leer scripts/import_service_catalog.py | ✅ | Línea 138: upsert(provider, on_conflict="id") |
| 16 | Verificación cuenta tools después de import | Leer scripts/import_service_catalog.py | ✅ | Línea 164-171: verifica tool_count == expected_tools |
| 17 | Dependencias incluyen json (built-in) | Python built-in | ✅ | No necesita pyproject.toml |
| 18 | Scripts directory existe | `ls scripts/` | ✅ | import_service_catalog.py existe |

**Discrepancias encontradas:**

- ❌ DISCREPANCIA: Plan menciona ~226 tools pero 4 archivos con ~61 cada = ~244. Evidencia: `wc -l docs/prompt*.txt` → prompt1: 3224 líneas, indica ~61 tools por archivo. Resolución: Ajustar expectativa a ~244 tools totales.

- ❌ DISCREPANCIA: Prompt files usan "auth" object con "type" y "scopes", pero plan dice mapear auth.type -> provider.auth_type. Evidencia: docs/prompt1.txt línea 92-95. Resolución: Usar auth.type como auth_type, ignorar scopes por ahora (service_catalog no tiene auth_scopes).

- ⚠️ NO VERIFICABLE: Cómo inferir base_url exacta de execution.url. Ejemplo: QuickBooks usa "https://quickbooks.api.intuit.com/v3/company/{company_id}/invoice". Asumo extraer protocolo+dominio. Confirmar antes de implementar.

- ❌ DISCREPANCIA: required_secrets formato. Plan: "[provider_id]_api_key". Seed actual: "stripe_api_key". Evidencia: seed línea 14. Resolución: Para consistencia, usar formato seed actual pero generar automáticamente [provider_id]_api_key para nuevos.

## 1. Diseño Funcional

El paso expande el catálogo de herramientas TIPO C agregando ~190 nuevas herramientas de 10 categorías faltantes (accounting, hr, logistics, support, forms, signatures, meetings, databases, marketing_automation, dns_hosting) mediante transformación de archivos prompt1-4.txt al esquema nested requerido.

Flujo completo:
1. Leer JSON arrays de 4 archivos prompt
2. Transformar cada tool flat -> nested schema (provider object, mappings)
3. Combinar con seed existente (~50 tools)
4. Deduplicar por tool_id (priorizar prompt4 sobre prompt1)
5. Actualizar data/service_catalog_seed.json
6. Ejecutar import_service_catalog.py para upsert en DB
7. Verificar integridad (counts, schemas, no orphans)

Happy path: Usuario ejecuta expand_catalog.py, seed se actualiza automáticamente, import funciona sin errores, catálogo expande de 50 a ~240 tools.

Edge cases:
- Tool_id duplicado: Mantener versión de archivo prompt más alto (4 > 3 > 2 > 1 > seed)
- Provider nuevo: Crear provider object con campos inferidos
- Auth type desconocido: Mapear a "api_key" por defecto
- Execution URL sin base detectable: Usar URL completa como base_url

Manejo de errores: Si transformación falla en un tool, loggear warning y continuar. Si seed JSON inválido, fallar completamente.

## 2. Diseño Técnico

Componentes nuevos/modificados:
- **scripts/expand_catalog.py** (NUEVO): Script principal de transformación
  - Lee prompt1-4.txt como JSON arrays
  - Aplica mappings: tool_id->id, provider string->object
  - Extrae base_url de execution.url (ej: https://api.stripe.com/v1)
  - Genera required_secrets: [provider_id]_api_key para api_key, [provider_id]_token para oauth2
  - Deduplica por id, combina con seed existente
  - Escribe nuevo JSON a data/service_catalog_seed.json

- **data/service_catalog_seed.json** (MODIFICADO): Actualizado con ~240 tools en esquema nested

- **scripts/import_service_catalog.py** (EJECUTADO): Sin cambios, upsert ~30 nuevos providers + ~190 tools

Interfaces (basadas en schemas verificados):
- Input expand_catalog.py: Archivos prompt*.txt en formato JSON array
- Output expand_catalog.py: service_catalog_seed.json compatible con import_service_catalog.py
- import_service_catalog.py input: seed JSON con tools[].provider como object
- DB service_catalog: id TEXT PK, name TEXT, category TEXT, auth_type TEXT, base_url TEXT, required_secrets TEXT[]
- DB service_tools: id TEXT PK, service_id TEXT FK, name TEXT, input_schema JSONB, output_schema JSONB, execution JSONB, tool_profile JSONB

Modelos de datos: Sin cambios, reutiliza schemas existentes de migración 024.

Coherente con estado-fase.md: Usa httpx (línea 23 pyproject), @register_tool (línea 110 registry.py), domain_events (línea 87 migrations/001).

## 3. Decisiones

- **Inferir base_url de execution.url**: Usar urlparse para extraer scheme + netloc. Corrige plan §1.0 — plan dice "base part" pero no especifica cómo. Técnica: urlparse(execution.url).scheme + "://" + netloc

- **Formato required_secrets**: Usar [provider_id]_api_key para api_key, [provider_id]_token para oauth2. Corrige plan §1.0 — plan da ejemplo genérico, pero seed usa nombres específicos. Razón: Consistencia con seed existente para evitar cambios en ServiceConnectorTool

- **Deduplicación por id**: Priorizar prompt4 > prompt3 > prompt2 > prompt1 > seed existente. Técnica: Dict con id como key, overwrite si id ya existe

- **Auth scopes**: Ignorar por ahora, service_catalog.auth_scopes es JSONB default []. Técnica: No mapear auth.scopes de prompt files

## 4. Criterios de Aceptación

- expand_catalog.py se ejecuta sin errores de sintaxis JSON
- service_catalog_seed.json resultante tiene ~240 tools válidos
- Cada tool tiene provider object con id, name, category, auth_type, base_url, required_secrets
- No tools duplicados por id
- import_service_catalog.py completa import con "✅ Import completed successfully!"
- DB tiene ≥30 providers y ~240 tools
- ServiceConnectorTool puede ejecutar una tool nueva (ej: quickbooks.create_invoice) sin cambios en código

## 5. Riesgos

- **Alto**: Base URL inferida incorrecta causa fallos en ejecución. Mitigación: Probar manualmente 2-3 tools nuevas post-import. Riesgo para pasos futuros: ServiceConnectorTool fallará en runtime si URLs mal inferidas

- **Medio**: required_secrets nombre incorrecto. Mitigación: Verificar patrón contra seed existente. Riesgo para pasos futuros: Vault no encontrará secretos, integración fallará

- **Medio**: JSON schema inválido en input_schema/output_schema. Mitigación: Validar con jsonschema library. Riesgo para pasos futuros: ServiceConnectorTool rechazará tools con schemas inválidos

- **Bajo**: Prompt files con datos inconsistentes. Mitigación: Logging detallado de warnings. Riesgo para pasos futuros: Tools incompletas en catálogo

## 6. Plan

1. **Crear expand_catalog.py** (2h): Leer prompt files, implementar transformación y mappings, escribir seed actualizado. Complejidad: Media (parsing JSON, string manipulation)

2. **Ejecutar expand_catalog.py** (15min): Verificar output JSON válido, contar tools ~240. Complejidad: Baja

3. **Ejecutar import_service_catalog.py** (30min): Verificar "✅ Import completed successfully!", verificar counts en DB. Complejidad: Baja

4. **Probar ServiceConnectorTool** (1h): Ejecutar una tool nueva manualmente, verificar resolución de secreto y HTTP call. Complejidad: Media

**Estimación tiempo total: 4h**. Dependencias: 1→2→3→4

## 🔮 Roadmap

- **Optimizaciones**: Paralelizar lectura de prompt files con asyncio
- **Mejoras**: Agregar validación de JSON schemas con jsonschema library
- **Features futuras**: Soporte para auth scopes en service_catalog.auth_scopes
- **Pre-requisitos para Fase 6**: Catálogo completo asegura cobertura de integraciones para agentes externos</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md