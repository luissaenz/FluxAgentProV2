# 🧠 ANÁLISIS TÉCNICO: Sprint 3 — Handlers Productivos (atg)

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `tasks` existe | `grep` en migración 001 | ✅ | `001_set_config_rpc.sql`, L34 |
| 2 | Tabla `tickets` existe | `ls` en migrations | ✅ | `019_tickets.sql` |
| 3 | Clase `FlowRegistry` existe | `grep` en `src/flows/` | ✅ | `src/flows/registry.py`, L32 |
| 4 | Handler `handle_tool_call` | `grep` en `tools.py` | ✅ | `src/mcp/tools.py`, L68 |
| 5 | Dependencia `python-jose` | `cat pyproject.toml` | ✅ | `pyproject.toml`, L29 |
| 6 | Uso de `PyJWT` | `grep` en middleware | ✅ | `src/api/middleware.py`, L62 |
| 7 | Helper `get_service_client` | `grep` en `session.py` | ✅ | `src/db/session.py`, L48 |
| 8 | Migración RLS 025 | `ls` en migrations | ✅ | `025_agent_catalog_rls_update.sql` |
| 9 | Vault Async Wrapper | `grep` en `vault.py` | ✅ | `src/db/vault.py`, L100 |
| 10 | Middleware `apikey` check | `cat` middleware doc | ✅ | `src/api/middleware.py`, L35 |
| 11 | Estructura `src/mcp/` | `ls` en dir | ✅ | Files base Sprint 1/2 presentes |
| 12 | Sanitizador R3 | `ls` en `src/mcp/` | ✅ | `src/mcp/sanitizer.py` |

**Discrepancias encontradas:**
1. ❌ **Librería JWT:** El `pyproject.toml` lista `python-jose` pero `src/api/middleware.py` usa `PyJWT` (`import jwt as pyjwt`).
   - **Resolución:** Agregar `pyjwt>=2.10.0` a `pyproject.toml` o migrar `middleware.py` a `python-jose` para unificar. Se opta por agregar `pyjwt` ya que el middleware depende de `PyJWKClient` (asymmetric signature).
2. ❌ **Rutas del Plan:** El plan usa `D:\Develop...`, el entorno real es `/home/daniel/develop/...`.
   - **Resolución:** Ignorar literales de disco y usar rutas relativas al workspace.
3. ⚠️ **execute_flow:** El plan lo menciona como "tool nueva", pero estructuralmente debe estar integrado en el dispatch genérico de tools dinámicas en `tools.py`.

---

## 1. Diseño Funcional

### Happy Path: Ejecución de Flow via Claude
1. Claude detecta una tool dinámica (ej: `diagnosticar_red_mcp`) generada por `flow_to_tool.py`.
2. El servidor recibe `call_tool`.
3. `handle_tool_call` despacha la solicitud a `src/mcp/handlers.py`.
4. El handler valida el esquema de entrada contra `FlowRegistry`.
5. Se crea una entrada en la tabla `tasks` con estado `pending`.
6. Se instancia el flow correspondiente y se ejecuta de forma asíncrona.
7. El resultado se sanitiza (Regla R3) y se retorna a Claude.

### Edge Cases
- **Flow no registrado:** El despacho debe retornar un error JSON-RPC estándar si el flow desapareció del registro.
- **Error en ejecución:** Captura total de excepciones para evitar caída del servidor MCP (JSON-RPC Error Code -32603).
- **Timeout:** La ejecución de flows largos debe garantizar que no bloquee otros requests MCP (uso de threads/corutinas).

---

## 2. Diseño Técnico

### Componentes nuevos
- **`src/mcp/handlers.py`**: Motor de ejecución.
  - `execute_flow_handler(name, args)`: Orquestador principal.
  - `get_task_handler(task_id)`: Consulta estado en tabla `tasks`.
- **`src/mcp/auth.py`**: Puente de identidad.
  - Genera un token temporal interno si es necesario para que el flow-engine reconozca al usuario/org.
- **`src/mcp/exceptions.py`**: Central de errores.
  - Clase `FAPMCPError` que mapea a `mcp.types.McpError`.

### Modelos de datos
- Se utiliza la tabla `tasks` (id, org_id, payload, result, status).
- Se utiliza la tabla `tickets` para seguimiento de alto nivel.

---

## 3. Decisiones

1. **Unificación JWT:** Se mantendrá `PyJWT` para el Bridge de Auth debido a su mejor soporte nativo para JWKS (asymmetric keys de Supabase). Se recomienda actualizar `pyproject.toml`.
   - *Justificación:* El middleware ya lo usa exitosamente. Retroceder a `python-jose` implica reescribir lógica de rotación de llaves.
2. **Dispatch Dinámico:** `execute_flow` no será una tool *estática* sino el handler por defecto para todos los tools inyectados dinámicamente.
   - *Corrige plan §3.69*: Evita redundancia.
3. **Mapeo de Errores:** Se usará el rango -32000 al -32099 (Server defined errors) para errores específicos de lógica de negocio de FAP.

---

## 4. Criterios de Aceptación (Sí/No)
- [ ] ¿El archivo `src/mcp/handlers.py` existe y maneja la ejecución real?
- [ ] ¿Los errores de ejecución de flows retornan `isError=True` en MCP sin cerrar el proceso?
- [ ] ¿Se crea un registro en la tabla `tasks` por cada ejecución exitosa o fallida?
- [ ] ¿La respuesta de los flows pasa por `sanitize_output()`?
- [ ] ¿La herramienta `get_task` permite consultar el estado de un `task_id` válido?

---

## 5. Riesgos
- **Riesgo de Dependencias:** El servidor podría fallar en entornos donde `PyJWT` no esté instalado si solo se confía en `python-jose`. 
  - *Mitigación:* Actualizar `pyproject.toml` inmediatamente.
- **Bloqueo de Event Loop:** Flows pesados bloqueando el servidor Stdio.
  - *Mitigación:* Ejecutar lógica de flows en `asyncio.to_thread` o garantizar que el flow-engine sea 100% async.

---

## 6. Plan

| Tarea | Complejidad | Tiempo Est. | Dependencia |
|:---|:---:|:---:|:---|
| 1. Fix `pyproject.toml` (PyJWT) | Baja | 0.5h | Ninguna |
| 2. Implementar `exceptions.py` | Baja | 1h | Ninguna |
| 3. Implementar `handlers.py` (Execute logic) | Alta | 4h | exceptions.py |
| 4. Implementar `auth.py` (Identity Bridge) | Media | 2h | Handlers |
| 5. Integrar en `tools.py` y `server.py` | Media | 2h | Handlers |

**Total Estimado: 9.5h**

---

## 🔮 Roadmap
- **Sprint 4**: Soporte para SSE para permitir ejecuciones de larga duración desvinculadas de la sesión Stdio actual.
- **Manejo de Streams**: Permitir que el output de los flows llegue a Claude en tiempo real (requiere soporte MCP v1.0+).
