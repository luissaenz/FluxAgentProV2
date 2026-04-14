# 🧠 ANÁLISIS TÉCNICO: EXPANSIÓN DEL CATÁLOGO DE SERVICIOS (PASO 1)

Análisis detallado para la escala masiva del catálogo de servicios TIPO C, pasando de ~50 herramientas a ~270, mediante la transformación de definiciones crudas y su importación en Supabase.

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `service_catalog` existe | `grep -r "CREATE TABLE.*service_catalog" supabase/migrations/` | ✅ | `024_service_catalog.sql:8` |
| 2 | Tabla `service_tools` existe | `grep -r "CREATE TABLE.*service_tools" supabase/migrations/` | ✅ | `024_service_catalog.sql:59` |
| 3 | Seed JSON actual | `ls data/service_catalog_seed.json` | ✅ | Existe, ~50 tools, formato Nested TIPO C |
| 4 | Script de importación | `ls scripts/import_service_catalog.py` | ✅ | Existe y funcional (Paso 5.2.5) |
| 5 | Fuente: `prompt1.txt` | `ls docs/prompt1.txt` | ✅ | 61 tools, accounting/hr/logistics/support... |
| 6 | Fuente: `prompt2.txt` | `ls docs/prompt2.txt` | ✅ | ~60 tools, fintech/legal/marketing... |
| 7 | Fuente: `prompt3.txt` | `ls docs/prompt3.txt` | ✅ | ~60 tools, AI/dev_tools/cloud... |
| 8 | Fuente: `prompt4.txt` | `ls docs/prompt4.txt` | ✅ | ~40 tools, Regional LATAM (MercadoPago, AFIP, etc) |
| 9 | Lógica de Secretos | `src/tools/service_connector.py` | ✅ | Línea 112: Inyecta secret según `auth_type` |
| 10 | Dependencia `httpx` | `pyproject.toml` | ✅ | Linea 23: `httpx>=0.28.0` |
| 11 | Endpoints `/integrations` | `src/api/routes/integrations.py` | ✅ | Rutas `/available` y `/tools/{id}` funcionales |
| 12 | Script `expand_catalog.py` | `ls scripts/expand_catalog.py` | ❌ | **DISCREPANCIA:** No existe aún. Debe crearse. |

**Discrepancias encontradas:**

1. **Naming de `required_secrets`**: El plan sugiere `[provider_id]_api_key`, pero el seed actual usa `_token`, `_access_token` y `_api_key` de forma inconsistente.
   - **Resolución**: Standardizar en el script transformador: si `auth_type` es `oauth2` -> `_oauth_token`, si es `api_key` -> `_api_key`.
2. **URLs con Placeholders**: Varios proveedores (QuickBooks, Xero, MercadoPago) usan `{company_id}` o `{user_id}` en la URL. 
   - **Resolución**: `ServiceConnectorTool` ya soporta `.format(**input_data)` (L107), pero el script debe asegurar que estos placeholders no se corrompan durante la transformación.
3. **Mapeo de `auth.type`**: Los prompts usan `api_key`, `oauth2`, `none`. La DB en `ServiceConnectorTool` maneja `api_key`, `oauth2`, `basic_auth`.
   - **Resolución**: El script debe mapear `none` a `api_key` (con required_secrets vacío) o manejarlo explícitamente para evitar errores de nullability en DB.

---

### 1. Diseño Funcional
- **Happy Path**: 
  1. El usuario ejecuta `python scripts/expand_catalog.py`.
  2. El script lee los 4 archivos de docs.
  3. Parsea los bloques JSON, detecta proveedores y herramientas.
  4. Transforma al esquema anidado (Nested TIPO C).
  5. Escribe un `service_catalog_seed.json` consolidado.
  6. El usuario ejecuta `python -m scripts.import_service_catalog`.
  7. Los endpoints `/api/integrations/available` ahora muestran ~270 herramientas.
- **Edge Cases**:
  - **Deduplicación**: Si una tool ID existe en el seed original y en los prompts, el script debe decidir cuál priorizar (se recomienda priorizar el seed manual por ser más preciso, o el prompt si es más nuevo).
  - **Inferencia de Base URL**: Extraer el esquema y dominio de la primera tool de cada proveedor.
- **Errores**:
  - Si un fragmento JSON en los prompt files está corrupto (ej: texto de IA mezclado), el script debe loguear el error y saltar esa tool sin abortar todo el proceso.

### 2. Diseño Técnico
- **Componente 1: `scripts/expand_catalog.py`**:
  - **Regex Parser**: Para extraer arrays JSON de bloques de texto que pueden contener explicaciones de la IA.
  - **Transformer**: Clase/función que toma la tool plana y genera el objeto `provider` anidado.
  - **Metadata Inference**:
    ```python
    provider_id = tool["provider"].lower().replace(" ", "_")
    base_url = "/".join(tool["execution"]["url"].split("/")[:3]) # Simplista, requiere mejora
    ```
- **Componente 2: `data/service_catalog_seed.json`**:
  - Archivo de gran tamaño (>300KB post-expansión). Se debe asegurar que el formato sea ASCII compatible para evitar problemas de encoding con caracteres LATAM (prompt4).

### 3. Decisiones
1. **Deduplicación por `tool_id`**: Si hay colisión, se mantiene la versión del `service_catalog_seed.json` existente (fuente de verdad manual) y se descarta la del prompt.
2. **Standardización de Secretos**: 
   - OAuth2 -> `[provider_id]_oauth_token`
   - API Key -> `[provider_id]_api_key`
3. **Mantenimiento de `import_service_catalog.py`**: NO modificar el importador, el transformador debe adaptarse a la interfaz que el importador ya expone.

### 4. Criterios de Aceptación
- [ ] `expand_catalog.py` genera un JSON válido con ≥ 270 herramientas totales.
- [ ] Todas las nuevas herramientas tienen el objeto `provider` correctamente anidado (TIPO C).
- [ ] El campo `execution.url` mantiene los placeholders `{...}` intactos.
- [ ] `import_service_catalog.py` se ejecuta sin errores de integridad referencial.
- [ ] Endpoint `GET /api/integrations/available` retorna la lista completa en < 500ms.
- [ ] La tabla `service_catalog` en Supabase tiene ≥ 45 proveedores únicos.

### 5. Riesgos
- **Placeholders Variables**: Herramientas como AFIP o MercadoPago tienen URLs complejas. Si la inferencia de `base_url` es incorrecta, el `ServiceConnectorTool` podría fallar al concatenar.
  - *Mitigación*: El transformer debe ser "inteligente" o simplemente usar la URL completa de la tool y dejar `base_url` como metadato descriptivo.
- **Límite de Payload Supabase**: Upsert de 270 filas en bucle puede ser lento o fallar si la conexión es inestable.
  - *Mitigación*: El importador ya usa `upsert` por fila, pero se podría añadir un pequeño delay si es necesario (no esperado).

### 6. Plan de Implementación
1. **Tarea 1 [Alta]**: Implementar `scripts/expand_catalog.py` con regex para extracción robusta de JSON. (4h)
2. **Tarea 2 [Media]**: Ejecutar transformación y validar integridad del nuevo `service_catalog_seed.json`. (1h)
3. **Tarea 3 [Media]**: Ejecutar `scripts/import_service_catalog.py` en entorno de desarrollo. (1h)
4. **Tarea 4 [Baja]**: Verificación mediante query SQL de conteos finales. (0.5h)

**Complejidad:** Media (principalmente por la manipulación de strings y regex de los prompts).

---

### Sección Final: 🔮 Roadmap (NO implementar ahora)
- **Automatic Health Check**: Programar el job de validación de APIs para todas las 270 tools.
- **Provider Settings UI**: Pantalla dinámica en el Dashboard para configurar los secretos de cada uno de los ~45 proveedores.
- **Tool Sandbox**: Entorno para probar ejecuciones de tools TIPO C antes de activarlas para agentes.
