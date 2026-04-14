# 🧠 ANÁLISIS FINAL: EXPANSIÓN DEL CATÁLOGO DE SERVICIOS (TIPO C)

Este documento consolida el diseño técnico para la escala masiva del catálogo de servicios de FluxAgentPro-v2, integrando ~200 nuevas herramientas desde fuentes externas hacia el esquema productivo.

## 0. Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) |
|:---|:---:|:---:|:---:|:---:|
| **atg** | ✅ | 3 críticas (Secretos, URLs, Script missing) | ✅ | 5 |
| **oc** | ✅ | 2 críticas (Script missing, Mapeo schema) | ✅ | 4 |
| **kilo** | ✅ | 2 críticas (Inferencia base_url, Secret naming) | ✅ | 4 |
| **qwen** | ❌ (Paso equivocado) | N/A (Analizó Paso 5.2) | ❌ | 1 |

### Discrepancias Críticas y Resolución (Hallazgos Consolidados)

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|:---:|---|
| 1 | El script `expand_catalog.py` no existe. | oc / atg | ✅ | Debe crearse en `scripts/` como paso inicial. |
| 2 | Inconsistencia en nombres de `required_secrets`. | atg / kilo | ✅ (seed L14) | Usar `[provider_id]_api_key` para API Keys y `[provider_id]_token` para OAuth2. |
| 3 | URLs con placeholders (`{user_id}`) en prompts. | atg | ✅ (prompt4) | El script debe preservar el string literal para inyección dinámica en runtime. |
| 4 | Inferencia de `base_url` no especificada en plan. | kilo | ✅ | Usar `urllib.parse` para extraer protocolo + host de la primera tool de cada proveedor. |
| 5 | Mapeo de `auth.type: none`. | oc | ✅ | Mapear a `auth_type: api_key` con `required_secrets: []` para evitar fallos de integridad. |

---

## 1. Resumen Ejecutivo
Se escalará el catálogo de servicios de ~50 herramientas actuales a **~240 herramientas totales**, cubriendo 10 categorías críticas (Fintech, HR, Logistics, etc.). El proceso implica la creación de un script transformador que procesa 4 archivos de texto con definiciones crudas, las normaliza al esquema "Nested TIPO C" y las importa en Supabase manteniendo la Regla R3 de seguridad.

**Correcciones al plan general:** 3 (Naming de secretos, Naming de archivo transformador, Inferencia de base_url).

## 2. Diseño Funcional Consolidado
1. **Extracción**: El script `expand_catalog.py` lee `docs/prompt1.txt` a `prompt4.txt`. Utiliza regex para aislar los arrays JSON eliminando texto decorativo de la IA.
2. **Transformación**: Cada entrada "flat" se mapea a un objeto anidado donde la información del proveedor se extrae de campos redundantes en la tool.
3. **Merge**: Se realiza un merge aditivo con el actual `data/service_catalog_seed.json`. Si hay colisión de `id`, prevalece la versión de los prompts más recientes (`prompt4 > ... > seed`).
4. **Persistencia**: Se actualiza el archivo seed en disco.
5. **Importación**: Se invoca el script existente `scripts/import_service_catalog.py` para sincronizar con la base de datos Supabase.

## 3. Diseño Técnico Definitivo

### Componente: `scripts/expand_catalog.py`
- **Lógica de Inferencia de Proveedor**:
  ```python
  provider_id = tool["provider"].lower().replace(" ", "_")
  # Extraer Host de execution.url (evitando corromper placeholders)
  parsed = urlparse(tool["execution"]["url"])
  base_url = f"{parsed.scheme}://{parsed.netloc}"
  ```
- **Mapping de Secretos**:
  - `none` -> `required_secrets: []`
  - `api_key` -> `required_secrets: [provider_id + "_api_key"]`
  - `oauth2` -> `required_secrets: [provider_id + "_token"]`

### Integraciones y Contratos
- **Vault (`src/db/vault.py`)**: Los nombres de secretos generados deben coincidir con las búsquedas que realiza `get_secret(org_id, secret_name)`.
- **Database (`supabase/migrations/024_service_catalog.sql`)**: 
  - `service_catalog`: Se insertan/actualizan ~30-40 proveedores únicos.
  - `service_tools`: Se insertan/actualizan ~240 registros.

## 4. Decisiones Tecnológicas
- **Merge Additive con Overwrite**: Se decidió no borrar herramientas del seed original si no aparecen en los prompts, para preservar integraciones personalizadas previas.
- **Deduplicación por `tool_id`**: Es el identificador único global. No se permiten duplicados en el JSON final.
- **Normalización de IDs**: Todos los `id` de proveedores y herramientas se forzarán a lowercase para evitar colisiones por case-sensitivity en PostgreSQL.

## 5. Criterios de Aceptación MVP ✅
- [ ] **Técnico**: `expand_catalog.py` genera un JSON válido que pasa validación `json.loads()`.
- [ ] **Funcional**: `service_catalog_seed.json` contiene ≥ 230 herramientas post-ejecución.
- [ ] **Estructura**: El 100% de las herramientas nuevas tienen el objeto `provider` anidado (formato TIPO C).
- [ ] **DB**: `import_service_catalog.py` reporta "✅ Import completed successfully!".
- [ ] **Seguridad**: El campo `required_secrets` no está vacío para herramientas que no son `auth_type: none`.
- [ ] **Integridad**: Ninguna herramienta queda "huérfana" (todas tienen un `service_id` que existe en `service_catalog`).

## 6. Plan de Implementación
1. **[Baja]** Crear `scripts/expand_catalog.py` con estructura base de carga de archivos.
2. **[Media]** Implementar `transform_tool()` con lógica de inferencia de `base_url` y secretos.
3. **[Media]** Implementar lógica de merge con prioridad `prompt4 -> prompt1 -> seed`.
4. **[Baja]** Ejecutar y verificar `data/service_catalog_seed.json`.
5. **[Baja]** Ejecutar `scripts/import_service_catalog.py` y validar conteos en DB.

## 7. Riesgos y Mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Corrupción de placeholders `{...}` en URLs | Alto | El mapping de URL debe ser por asignación directa de string, no concatenación parcial. |
| Inconsistencia de Categorías | Medio | Mapear categorías de prompts a un set cerrado definido en `service_catalog.category`. |
| Límite de API Supabase | Bajo | El script de importación actual ya procesa fila por fila de forma robusta. |

## 8. Testing Mínimo Viable
- **Prueba 1**: Verificar que MercadoPago (Región LATAM) tiene el `base_url` configurado como `https://api.mercadopago.com`.
- **Prueba 2**: Verificar que herramientas de `prompt1` (ej. QuickBooks) mantienen sus parámetros de path variables.
- **Prueba 3**: Endpoint `GET /api/integrations/available` debe retornar la lista expandida sin errores 500.

## 9. 🔮 Roadmap
- **Validación Automática**: Implementar el health check scheduler para monitorear el uptime de las ~240 integraciones.
- **Auth Scopes**: Extender el schema para soportar los scopes detallados en los prompts para flujos OAuth2 complejos.
