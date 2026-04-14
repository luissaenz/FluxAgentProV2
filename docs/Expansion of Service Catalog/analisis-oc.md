# 📋 ANÁLISIS TÉCNICO — Paso 1: Expansión del Catálogo de Servicios

**Agente:** oc  
**Fecha:** 2026-04-13  
**Paso asignado:** 1.0 + 1.1 + 1.2 (Expansión Service Catalog TIPO C)

---

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Script `expand_catalog.py` existe | `glob scripts/*` → NO existe | ❌ | scripts/ no contiene expand_catalog.py |
| 2 | `data/service_catalog_seed.json` existe | `ls data/` → existe | ✅ | seed file con 50 tools actual |
| 3 | `scripts/import_service_catalog.py` existe | `glob scripts/*` → existe | ✅ | scripts/import_service_catalog.py L1-243 |
| 4 | Tablas service_catalog, service_tools existen | `grep migrations/024_service_catalog.sql` → existe | ✅ | migración 024 con 3 tablas |
| 5 | prompt1.txt tiene ~61 tools | Parse JSON → 61 tools | ✅ |docs/prompt1.txt L82 |
| 6 | prompt2.txt tiene ~61 tools | Parse JSON → 61 tools | ✅ | docs/prompt2.txt L54 |
| 7 | prompt3.txt tiene ~80 tools | Parse JSON → 82 tools | ✅ | docs/prompt3.txt L24 |
| 8 | prompt4.txt tiene ~35 tools | Parse JSON → 35 tools | ✅ | docs/prompt4.txt L43 |
| 9 | ServiceConnectorTool funciona | `src/tools/service_connector.py` → existe | ✅ | tool registrada con @register_tool |
| 10 | RLS en org_service_integrations | migración 024 L47-51 | ✅ | patrón service_role + current_org_id() |
| 11 | Provider schema en seed | `seed.json` → tiene provider object | ✅ | service_catalog_seed.json L6-15 |
| 12 | Dependencia httpx | `pyproject.toml` → httpx>=0.28.0 | ✅ | confirmada |

**Total verificado:** 12 elementos

### Discrepancias encontradas:

1. **CRÍTICA:** El script `expand_catalog.py` NO EXISTE en `scripts/`. El plan lo referencia como existente pero debe crearse.
   - Resolución: Crear el script según especificación del plan.

2. **MENOR:** Los prompt files tienen schemas diferentes al seed actual:
   - Prompt usa `provider` (string) + `auth.type` + `execution.method`
   - Seed usa `provider` (object con id, name, category, auth_type) + `execution.method` como campo separado
   - Resolución: El script transform_tool() ya maneja esta transformación (lines 84-149 de la referencia del plan).

---

## 1. Diseño Funcional

### 1.0 Expansión del Catálogo (script expand_catalog.py)

**Happy Path:**
1. Ejecutar `python scripts/expand_catalog.py`
2. Script carga existente seed (50 tools)
3. Parsea prompt1-4.txt extrayendo JSON arrays (239 tools totales)
4. Transforma cada tool del schema flat (prompt) al schema anidado TIPO C
5. Merge: sobrescribe tools existentes con mismo ID, agrega nuevas
6. Resultado: ~239 tools en service_catalog_seed.json
7. Output: print con counts (existing + new = total)

**Edge Cases:**
- JSON inválido en prompt → skip con warning, continuar con otros
- Tool ID duplicado → priorizar nuevo (prompt4 > prompt3 > prompt2 > prompt1)
- Campo faltante en tool (ej: sin execution.url) → skip con warning

**Manejo de Errores:**
- Si seed no existe → crear nuevo `{"tools": []}`
- Si prompt no existe → skip con warning
- Si transformación falla → skip individual, no abortar proceso

### 1.1 Update Seed (resultado del script)

El script escribir directamente a `data/service_catalog_seed.json`. No requiere paso separado.

### 1.2 Import a DB

**Happy Path:**
1. `python -m scripts.import_service_catalog` (o script directo)
2. Carga seed.json (~239 tools)
3. Extrae providers únicos (~30)
4. Upsert providers en `service_catalog`
5. Upsert tools en `service_tools`
6. Verifica counts: providers≥15, tools=239, no orphans
7. Output: "✅ Import completed successfully!"

**Edge Cases:**
- Provider con mismo ID → sobrescribe (upsert)
- Tool sin service_id válido → orphan check falla
- Schema JSON inválido → fix_required_schema() corrige

**Manejo de Errores:**
- Sin SUPABASE_URL/SERVICE_KEY → print error + exit(1)
- Verification falla → exit(1) con lista de errores

---

## 2. Diseño Técnico

### Componentes

| Componente | Archivo | Rol |
|-----------|---------|-----|
| expand_catalog.py | **A CREAR** | scripts/expand_catalog.py |
| Transformación | Función interna | transform_tool() schema flat→nested |
| Merge | Función interna | merge_tools() deduplicación por ID |
| import_service_catalog.py | **YA EXISTE** | scripts/import_service_catalog.py |

### Interfaz de expand_catalog.py

```python
# Entrada: None (lee archivos fixed)
# Salida: Actualiza data/service_catalog_seed.json

def load_existing_seed() -> Dict: ...
def extract_json_from_prompt(Path) -> List[Dict]: ...
def transform_tool(Dict) -> Dict: ...  # Schema prompt → TIPO C
def merge_tools(List, List) -> List: ...  # Deduplicación
def save_seed(Dict, List) -> None: ...  # Escribe JSON
```

### Schema de Transformación (mapping)

| Campo Prompt | Campo TIPO C | Transformación |
|--------------|--------------|-----------------|
| tool_id | id | Directo |
| provider (string) | provider.id | lower(), replace(" ", "_") |
| provider (string) | provider.name | Original |
| category | provider.category | Directo |
| auth.type | provider.auth_type | oauth2/api_key/none mapping |
| execution.url | provider.base_url | Parse URL → scheme+netloc |
| execution.url | execution.url | Directo |
| execution.method | execution.method | Directo |
| tool_profile | tool_profile | Mueve category, drop example_prompt |

### APIs Reutilizadas

- No hay APIs nuevas. Todo es script offline.
- ServiceConnectorTool (`src/tools/service_connector.py`) ya consume service_tools.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|----------|---------------|
| 1 | Crear expand_catalog.py como script standalone | El plan lo menciona como archivo a crear, no existe aún. |
| 2 | Deduplicar por tool_id con overwrite | Prioriza versiones más nuevas (prompt4 sobre prompt1). |
| 3 | Usar urllib.parse para base_url | Extrae host de URLs con path vars como {company_id}. |
| 4 | No ejecutar import en el mismo script | Separar permite verificar seed.json antes de DB. |

---

## 4. Criterios de Aceptación

- [ ] **1.0.1** Script `expand_catalog.py` ejecuta sin errores
- [ ] **1.0.2** seed.json contiene ≥200 tools después de ejecución
- [ ] **1.0.3** Cada tool tiene estructura TIPO C válida (provider object, execution.method, tool_profile)
- [ ] **1.1.1** seed.json se actualiza en disco con indentación legible
- [ ] **1.2.1** import_service_catalog.py upserta ≥30 providers en service_catalog
- [ ] **1.2.2** import_service_catalog.py upserta ≥200 tools en service_tools
- [ ] **1.2.3** Verification reporta "✅ Import completed successfully!"
- [ ] **1.2.4** Sin orphan tools (todos los service_id referencian providers válidos)

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| JSON en prompts tiene errores de sintaxis | Medium | Script hace try/except por tool, no falla todo |
| Herramientas con URLs inválidas (sin protocolo) | Low | transform_tool genera base_url vacío, import valida después |
| Duplicados con mismo ID pero semántica diferente | Medium | Sobrescribir puede perder funcionalidad. Asumimos prompts son consistentes. |
| Provider ID collisiones (QuickBooks vs quickbooks) | Low | transform_tool normaliza a lowercase |

---

## 6. Plan

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|-------|-------------|--------|---------------|
| 1 | Crear scripts/expand_catalog.py | Baja | 15 min | Ninguna |
| 2 | Ejecutar expand_catalog.py | Baja | 30 seg | Tarea 1 |
| 3 | Verificar seed.json con ≥200 tools | Baja | 5 min | Tarea 2 |
| 4 | Ejecutar import_service_catalog.py | Media | 1 min | Tarea 3 + SUPABASE env vars |
| 5 | Verificar DB counts | Baja | 30 seg | Tarea 4 |

**Tiempo total estimado:** ~18 minutos

---

## 🔮 Roadmap (NO implementar ahora)

1. **Validación de APIs reales:** Verificar que las URLs en execution.url son funcionales (no todas lo serán).
2. **Categorización automática:** Los prompts solo tienen 10 categorías base, pero service_catalog soporta más granular.
3. **OAuth flow para OAuth2:** Las tools con auth_type=oauth2 necesitan token refresh flow (no implementado).
4. **Health checks:** Las integraciones nuevas no tienen health_check_url configuradas.
5. **Bulk import with transactions:** El import actual hace N upserts individuales; podría ser una transacción bulk.

---

## Notas

- El plan menciona ~226 tools, pero la suma real de prompts es 239 (61+61+82+35). Ajustar expectativa.
- ServiceConnectorTool ya funciona y puede ejecutar cualquiera de estas tools una vez importadas.
- No se requiere modificar ningún archivo existente de src/ para este paso.
- RLS en org_service_integrations ya permite acceso por org_id via header X-Org-ID.