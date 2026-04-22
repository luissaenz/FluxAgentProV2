# 📋 Plan de Implementación Detallado – Detalles Faltantes

A continuación se desglosan los puntos pendientes identificados en **`analisis‑FINAL.md`**, sus implicancias y el conjunto de tareas necesarias para resolverlos. Cada sección incluye:

* **Objetivo** – qué se debe conseguir.  
* **Implicancias** – por qué es crítico y qué áreas del proyecto se ven afectadas.  
* **Tareas** – pasos concretos (con sub‑tareas cuando procede).  
* **Dependencias** – artefactos o módulos que deben existir antes de iniciar.  
* **Criterios de aceptación** – cómo validar que la tarea quedó correcta.  
* **Estimación** – tiempo estimado (horas).  

---

## Paso 1: Auth Bridge – `src/mcp/auth.py`

### Objetivo
Implementar la capa de autenticación que valida los JWT recibidos por los endpoints MCP y expone utilidades para:

* Verificar firmas ES256 y HS256 usando **PyJWT**.
* Cachear la JWKS del proveedor (para ES256) y refrescarla cuando expire.
* Proveer la función `verify_org_membership(org_id, token_claims)` usada por el middleware.

### Implicancias
* **Seguridad**: sin esta capa, cualquier cliente podría invocar herramientas MCP.
* **Rendimiento**: la JWKS debe cachearse para evitar una petición HTTP por cada request.
* **Consistencia**: el middleware (`src/api/middleware.py`) ya llama a `_get_jwks_client()`; la nueva implementación debe ser compatible.

### Tareas
| # | Acción | Sub‑tareas | Responsable |
|---|--------|------------|-------------|
| 1 | **Crear archivo** `src/mcp/auth.py` | - Añadir cabecera de licencia y docstring. | — |
| 2 | **Implementar JWKS client** | - Función `_get_jwks_client()` que descarga la JWKS y la guarda en `lru_cache` (TTL ≈ 1 h). <br> - Soporte para múltiples emisores (configurable vía `MCPConfig`). | — |
| 3 | **Validar JWT** | - Función `decode_jwt(token: str) -> dict` que verifica firma, expiración, `aud`, `iss`. <br> - Manejo de errores: `InvalidSignatureError`, `ExpiredSignatureError`, `InvalidAudienceError`. | — |
| 4 | **Verificar membresía org** | - Función `verify_org_membership(org_id: UUID, claims: dict) -> bool` que comprueba que `org_id` está presente en `claims["orgs"]` (o similar). | — |
| 5 | **Integración con middleware** | - Refactorizar `src/api/middleware.py` para importar `decode_jwt` y `verify_org_membership` desde `auth.py`. | — |
| 6 | **Tests unitarios** | - Casos positivos/negativos para cada algoritmo (ES256, HS256). <br> - Test de caché JWKS (mock HTTP). | QA |
| 7 | **Documentación** | - Añadir sección “Auth Bridge” en `docs/architecture.md`. | Docs |

### Dependencias
* **PyJWT** (ya presente).  
* Configuración `MCPConfig.jwks_url` (añadir si falta).  

### Criterios de aceptación
* Todas las rutas MCP rechazan peticiones sin token o con token inválido (401).  
* Token válido con org correcta permite acceso (200).  
* La JWKS se descarga una sola vez por TTL (ver logs).  
* Cobertura de pruebas ≥ 90 %.  

### Estimación
**≈ 8 h** (incluye pruebas y documentación).

---

## Paso 2: Handlers Productivos – `src/mcp/handlers.py`

### Objetivo
Reemplazar el placeholder actual con lógica real para:

* `execute_flow` – lanzar un flow, crear registro de tarea, manejar HITL.  
* `get_task` – consultar estado y resultado.  
* `approve_task` / `reject_task` – cerrar HITL.  
* Otros handlers que requieran acceso a la base de datos (p. ej. `list_agents` ya existen).

### Implicancias
* **Core del producto**: sin estos handlers, los agentes externos solo pueden listar herramientas, no ejecutarlas.  
* **Persistencia**: necesita interacción con tablas `tasks`, `pending_approvals`.  
* **Concurrencia**: los flows pueden ser async; se debe manejar cancelación y time‑outs.

### Tareas
| # | Acción | Sub‑tareas | Responsable |
|---|--------|------------|-------------|
| 1 | **Crear archivo** `src/mcp/handlers.py` | - Cabecera y registro de handlers en `MCPServer`. | — |
| 2 | **Implementar `execute_flow`** | - Validar `flow_type` contra `FlowRegistry`. <br> - Instanciar flow, pasar `input_data`. <br> - Crear registro en tabla `tasks` (estado *running*). <br> - Si flow requiere aprobación (`requires_human`), crear fila en `pending_approvals` y devolver `await_approval`. | — |
| 3 | **Implementar `get_task`** | - Query a `tasks` por `task_id`. <br> - Devolver JSON con `status`, `result`, `error` (si corresponde). | — |
| 4 | **Implementar `approve_task` / `reject_task`** | - Cambiar estado de `pending_approvals`. <br> - Re‑reanudar flow (para approve) o marcar como `failed` (reject). <br> - Emitir evento `domain_events`. | — |
| 5 | **Integración con DB** | - Utilizar `src/db/session.py` (async engine). <br> - Añadir transacciones donde sea necesario. | — |
| 6 | **Tests de integración** | - Simular flow simple sin HITL → tarea completada. <br> - Simular flow con HITL → estado `await_approval` → approve → completado. | QA |
| 7 | **Documentación** | - Añadir ejemplos de uso en `docs/api_mcp.md`. | Docs |

### Dependencias
* **FlowRegistry** (`src/flows/registry.py`).  
* **BaseFlow** con método `requires_human` (añadir si falta).  
* Tablas `tasks` y `pending_approvals` (migraciones ya aplicadas).  

### Criterios de aceptación
* `execute_flow` devuelve `task_id` y crea registro en DB.  
* Flows sin HITL finalizan automáticamente y su `result` está disponible vía `get_task`.  
* Flows con HITL quedan en estado `await_approval`; después de `approve_task` pasan a `completed`.  
* Todos los handlers devuelven respuestas JSON‑RPC válidas y pasan por `sanitize_output`.  

### Estimación
**≈ 12 h** (incluye pruebas y documentación).

---

## Paso 3: Excepciones – `src/mcp/exceptions.py`

### Objetivo
Definir una jerarquía de excepciones MCP y un mapeo a códigos JSON‑RPC estándar (‑32000 … ‑32099) para que el cliente reciba errores estructurados.

### Implicancias
* **Experiencia de desarrollador**: errores claros facilitan depuración.  
* **Consistencia**: todos los handlers usarán la misma estrategia de error.

### Tareas
| # | Acción | Sub‑tareas |
|---|--------|------------|
| 1 | **Crear archivo** `src/mcp/exceptions.py`. |
| 2 | **Definir clases base**: `MCPError`, `InvalidParams`, `AuthError`, `NotFound`, `InternalError`. |
| 3 | **Mapeo**: diccionario `ERROR_MAP = {InvalidParams: -32602, AuthError: -32001, ...}`. |
| 4 | **Helper** `mcp_error_to_response(exc: MCPError) -> dict` que genera el JSON‑RPC `error` object. |
| 5 | **Integrar** en `src/mcp/server.py` (captura de excepciones y uso del helper). |
| 6 | **Tests**: lanzar cada excepción y verificar código y mensaje. |

### Dependencias
* Ninguna externa; solo importaciones internas.

### Criterios de aceptación
* Cada excepción genera el código JSON‑RPC correcto.  
* El cliente recibe `error` con `code`, `message` y opcional `data`.

### Estimación
**≈ 3 h**.

---

## Paso 4: Transporte SSE (Server‑Sent Events)

### Objetivo
Agregar soporte SSE como alternativa a la interfaz Stdio, permitiendo que agentes remotos (p. ej. Claude API) se conecten mediante HTTP y reciban eventos en tiempo real.

### Implicancias
* **Escalabilidad**: clientes pueden permanecer conectados sin abrir procesos locales.  
* **Seguridad**: se debe validar `X‑Org‑ID` en la cabecera y el token JWT.  
* **Compatibilidad**: mantener Stdio como fallback.

### Tareas
| # | Acción | Sub‑tareas |
|---|--------|------------|
| 1 | **Extender `MCPConfig`**: añadir `transport: "stdio" | "sse"` y `sse_endpoint: str`. |
| 2 | **Crear endpoint FastAPI** `GET /mcp/sse` que devuelve `EventSourceResponse`. |
| 3 | **Implementar dispatcher** que envía respuestas de herramientas como eventos (`tool_result`, `task_update`). |
| 4 | **Autenticación**: validar JWT y `X‑Org‑ID` antes de aceptar la conexión. |
| 5 | **Graceful shutdown**: cerrar streams al detener el servidor. |
| 6 | **Tests de integración**: cliente Python que se suscribe, envía `list_tools`, recibe eventos. |
| 7 | **Documentación**: actualizar `README` y `docs/api_mcp.md` con ejemplos SSE. |

### Dependencias
* **FastAPI** y **sse-starlette** (añadir a `pyproject.toml`).  
* **Auth Bridge** (punto 1) para validar token.

### Criterios de aceptación
* Cliente SSE recibe eventos en formato JSON‑RPC sin pérdida de datos.  
* Conexión rechazada sin token válido (401).  
* Compatibilidad con clientes Stdio existente.

### Estimación
**≈ 10 h** (incluye dependencia nueva y pruebas).

---

## Paso 5: Conexión del Scheduler de Health‑Check

### Objetivo
Ejecutar `run_health_checks()` automáticamente al iniciar la aplicación FastAPI y, opcionalmente, al detenerla.

### Implicancias
* **Observabilidad**: sin este scheduler, no se detectan fallos de dependencias.  
* **Rendimiento**: debe ejecutarse en background sin bloquear el event loop.

### Tareas
| # | Acción |
|---|--------|
| 1 | Añadir `@app.on_event("startup")` que lanza `asyncio.create_task(run_health_checks())`. |
| 2 | (Opcional) `@app.on_event("shutdown")` para cancelar la tarea. |
| 3 | Verificar que `run_health_checks` usa `httpx.AsyncClient` y maneja excepciones. |
| 4 | Tests: arrancar la app en modo test y comprobar que se escribe al menos una entrada en `domain_events` después de 5 s. |
| 5 | Documentar en `docs/health_check.md`. |

### Dependencias
* **FastAPI** (ya presente).  
* **run_health_checks** (en `src/scheduler/health_check.py`).

### Criterios de aceptación
* Al iniciar la API, el scheduler se ejecuta al menos una vez.  
* Los logs muestran “Health check executed”.

### Estimación
**≈ 4 h**.

---

## Paso 6: Archivo Seed `data/service_catalog_seed.json`

### Objetivo
Proveer el archivo JSON que contiene los datos de arranque para la tabla `service_catalog`.

### Implicancias
* **Importación**: el script `scripts/import_service_catalog.py` falla si el archivo no existe.  
* **Consistencia**: sin seed, la tabla queda vacía y no hay herramientas TIPO C disponibles.

### Tareas
| # | Acción |
|---|--------|
| 1 | Crear directorio `data/` (si no existe). |
| 2 | Generar `service_catalog_seed.json` con al menos 5 ejemplos de servicios (nombre, descripción, endpoint, método). |
| 3 | Añadir validación en el script de importación: si el archivo falta, lanzar error claro o crear tabla vacía. |
| 4 | Tests: ejecutar script en entorno de pruebas y comprobar que se insertan los registros. |
| 5 | Documentar formato del seed en `docs/service_catalog.md`. |

### Dependencias
* Ninguna externa, solo la tabla `service_catalog` (migration 024).

### Criterios de aceptación
* El script importa correctamente los registros y muestra “X services imported”.  
* El archivo está versionado en Git.

### Estimación
**≈ 2 h**.

---

## Paso 7: Limpieza de Dependencia `python‑jose`

### Objetivo
Eliminar la dependencia no utilizada `python‑jose[cryptography]` del proyecto y asegurarse de que `PyJWT` sigue declarada.

### Implicancias
* **Reducción de bloat** y evitar confusión futura.  
* **Seguridad**: menos paquetes externos = menor superficie de ataque.

### Tareas
| # | Acción |
|---|--------|
| 1 | Editar `pyproject.toml` – eliminar la línea `python-jose[cryptography]`. |
| 2 | Ejecutar `pip uninstall python-jose` (o equivalente en el entorno). |
| 3 | Ejecutar `pip install -r requirements.txt` para regenerar lock. |
| 4 | Ejecutar tests completos para confirmar que nada se rompe. |
| 5 | Actualizar `docs/dependencies.md` indicando que solo `PyJWT` es requerida. |

### Dependencias
* Ninguna, pero se requiere que la suite de pruebas pase.

### Criterios de aceptación
* `pip list` ya no muestra `python-jose`.  
* Todos los tests siguen pasando (≥ 90 %).

### Estimación
**≈ 1 h**.

---

## 📅 Cronograma Consolidado

| Sprint | Actividad | Horas estimadas | Comentario |
|--------|-----------|----------------|------------|
| **Sprint 3** (prioridad alta) | Auth Bridge, Handlers, Exceptions | 23 h | Núcleo funcional del MCP. |
| **Sprint 3** (continuación) | Health‑check scheduler, Service‑catalog seed | 6 h | Observabilidad y datos iniciales. |
| **Sprint 4** | Transporte SSE | 10 h | Soporte para clientes remotos. |
| **Sprint 4** | Limpieza `python‑jose` | 1 h | Mejora de dependencias. |
| **Total** | **≈ 40 h** (≈ 5 d laborables) | | Se deja margen para revisiones y pruebas. |

---

## ✅ Plan de Verificación Global

1. **CI Pipeline**  
   * Ejecutar `pytest` → cobertura ≥ 90 %.  
   * Linter (`ruff`/`flake8`) sin errores.
2. **Pruebas de integración** (FastAPI TestClient)  
   * `/mcp/sse` → conexión, envío de `list_tools`, recepción de eventos.  
   * `/mcp/execute_flow` → flow sin HITL → `task` completado.  
   * `/mcp/execute_flow` → flow con HITL → `await_approval` → `approve_task` → completado.
3. **Revisión de Seguridad**  
   * Escaneo de dependencias (`pip-audit`).  
   * Verificar que los tokens expirados son rechazados.
4. **Documentación**  
   * Todos los nuevos módulos aparecen en `docs/` y en el README con ejemplos de uso.
5. **Despliegue de Staging**  
   * Desplegar en entorno de pruebas, validar que la UI del dashboard muestra los eventos de health‑check y de tareas.

---

## 📌 Próximos Pasos

1. **Crear rama** `feature/mcp-core-implementation`.  
2. **Abrir Pull Request** con los cambios estructurales (auth, handlers, exceptions).  
3. **Solicitar revisión** del equipo de arquitectura y seguridad.  
4. **Ejecutar pipeline** y corregir fallos antes de merge.

Con este plan, cada detalle faltante queda cubierto, con claridad sobre **qué**, **por qué**, **cómo** y **cuánto** tiempo se necesita. ¡Listos para avanzar!
