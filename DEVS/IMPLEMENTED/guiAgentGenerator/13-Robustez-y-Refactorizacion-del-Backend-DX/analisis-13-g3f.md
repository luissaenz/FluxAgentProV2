# 🧠 ANÁLISIS TÉCNICO — Paso 13: Robustez y Refactorización del Backend (DX)

**Fase:** `guiAgentGenerator`  
**Paso:** 13 — Robustez y Refactorización del Backend (DX)  
**Agente:** `g3f`  
**Estado:** 🔍 ANÁLISIS COMPLETADO  

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

Se ha realizado una auditoría exhaustiva del codebase utilizando rutas reales mapeadas desde `proyecto-config.json`. A continuación, se detalla la evidencia técnica recolectada:

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `class AgentResponse` existe | Búsqueda estática | ✅ | `src/api/routes/agents.py`, línea 28-35 |
| 2 | `created_at` es opcional en `AgentResponse` | Inspección de firma | ✅ | `src/api/routes/agents.py`, línea 35 (`created_at: str \| None = None`) |
| 3 | `class AgentCreate` existe | Búsqueda estática | ✅ | `src/api/routes/agents.py`, línea 21-25 |
| 4 | `def _fetch_mcp_tools` existe | Búsqueda de función | ✅ | `src/cli/commands/tools_list.py`, línea 103-152 |
| 5 | Creación de event loop asíncrono en CLI | Inspección de loop | ✅ | `src/cli/commands/tools_list.py`, línea 141 (`loop = asyncio.new_event_loop()`) |
| 6 | `HTTPException(503)` en templates listing | Inspección de error | ✅ | `src/api/routes/templates.py`, línea 67 (`raise HTTPException(503, "Database unavailable")`) |
| 7 | `HTTPException(503)` en templates detail | Inspección de error | ✅ | `src/api/routes/templates.py`, línea 88 (`raise HTTPException(503, "Database unavailable")`) |
| 8 | `def run_agent` existe en CLI | Inspección de función | ✅ | `src/cli/commands/agent_run.py`, línea 52-64 |
| 9 | Cliente HTTP síncrono en `agent_run.py` (POST) | Inspección de cliente | ✅ | `src/cli/commands/agent_run.py`, línea 89 (`with httpx.Client(timeout=15) as client:`) |
| 10 | Cliente HTTP síncrono en `agent_run.py` (POLL) | Inspección de cliente | ✅ | `src/cli/commands/agent_run.py`, línea 131 (`with httpx.Client(timeout=10) as client:`) |
| 11 | `crew_app = typer.Typer(...)` existe en CLI | Inspección de Typer | ✅ | `src/cli/commands/crew.py`, línea 26-29 |
| 12 | Cliente HTTP síncrono en `crew.py` | Inspección de cliente | ✅ | `src/cli/commands/crew.py`, línea 178 (`with httpx.Client(timeout=15) as client:`) |
| 13 | `class ExportBundleRequest` existe | Búsqueda de schema | ✅ | `src/services/bundle_schemas.py`, línea 111-117 |
| 14 | `class AgentExportItem` existe | Búsqueda de schema | ✅ | `src/services/bundle_schemas.py`, línea 102-109 |
| 15 | Validación hardcodeada de `goal` en `bundles.py` | Inspección de longitud | ✅ | `src/api/routes/bundles.py`, línea 229 (`len(str(soul.get("goal", ""))) < 10`) |
| 16 | Validación hardcodeada de `backstory` en `bundles.py` | Inspección de longitud | ✅ | `src/api/routes/bundles.py`, línea 234 (`len(str(soul.get("backstory", ""))) < 10`) |
| 17 | Validación hardcodeada de `goal` en `bundle_validate_payload.py` | Inspección de longitud | ✅ | `src/cli/commands/bundle_validate_payload.py`, línea 84 (`len(goal) >= 10`) |
| 18 | Validación hardcodeada de `backstory` en `bundle_validate_payload.py` | Inspección de longitud | ✅ | `src/cli/commands/bundle_validate_payload.py`, línea 88 (`len(backstory) >= 10`) |
| 19 | `doctor_builder.py` existe | Búsqueda de archivo | ✅ | `src/cli/commands/doctor_builder.py` |
| 20 | `typer.Option` con syntax de fallback | Inspección de Typer | ✅ | `src/cli/commands/agent_run.py`, línea 53-63 |

#### Discrepancias Técnicas Detectadas

1. **Duplicación y Hardcoding de Longitud Mínima (ID-047):** La longitud mínima de 10 caracteres para `goal` y `backstory` está duplicada como literal `10` en `src/api/routes/bundles.py` y `src/cli/commands/bundle_validate_payload.py`. Esto introduce riesgo de desincronización de contratos (Drift).
   - *Resolución:* Centralizar ambas constantes en `src/services/bundle_schemas.py` como `MIN_GOAL_LENGTH = 10` y `MIN_BACKSTORY_LENGTH = 10` e importarlas en ambos archivos de validación.
2. **Uso Indebido de `asyncio.new_event_loop()` (ID-003):** El CLI de listing de herramientas crea un event loop completo por cada ejecución de `_fetch_mcp_tools()`. Si este comando es invocado desde procesos asíncronos concurrentes en el futuro, chocará.
   - *Resolución:* Utilizar `asyncio.get_event_loop()` o una abstracción limpia con `asyncio.run()`, manejando el ciclo de vida del loop correctamente mediante fallback.
3. **Bypass de Rutas Documentado (ID-016):** La documentación en `analisis-FINAL.md` describe los endpoints como `/api/agents` cuando las rutas FastAPI reales bajo el prefijo `router` en `agents.py` apuntan a `/agents` (el prefijo en `agents.py:18` es `"/agents"` sin `/api`!).
   - *Resolución:* Sincronizar el prefijo o actualizar las especificaciones de documentación técnica para que reflejen la realidad `/agents` y `/agents/{role}/run`.

---

### 1️⃣ Análisis de Datos (ETAPA 1)

#### Impacto en Base de Datos e Integridad
- **Tablas afectadas (Indirectamente):** `agent_catalog` y `agent_templates`.
- **Estructura del Schema:** El cambio de `created_at: str | None = None` a obligatorio (`created_at: str`) en `AgentResponse` no requiere migraciones físicas en Supabase ya que la columna `created_at` en `agent_catalog` ya está definida como `TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL` (integridad física perfecta). 
- **Integridad de Datos:** Al forzar a nivel de serialización Pydantic que `created_at` sea una cadena requerida (`created_at: str`), garantizamos que ningún registro devuelto por la API carezca de marca temporal. Esto previene que el frontend tenga que manejar fallbacks estáticos de fecha o se rompa ante campos nulos.

---

### 2️⃣ Análisis de Código (ETAPA 2)

#### Patrones de Diseño y Estructura
- **Tipado Estricto (Pydantic 2.x):** En `src/api/routes/agents.py`, la respuesta de creación y detalle utiliza el esquema `AgentResponse`. Al remover el default de `created_at`, forzamos a los serializadores a resolver la fecha.
```python
# Modificación en AgentResponse:
class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str  # Requerido, sin default None!
```
- **Optimización de Loops Asíncronos (Performance):** Reemplazar `asyncio.new_event_loop()` previene la fatiga de creación de hilos locales en sistemas multi-tenant.
- **Centralización de Constantes:** Definimos en `src/services/bundle_schemas.py`:
```python
MIN_GOAL_LENGTH: int = 10
MIN_BACKSTORY_LENGTH: int = 10
```
Y realizamos el import en los puntos de consumo para cumplir el principio DRY (Don't Repeat Yourself).

---

### 3️⃣ Análisis de Backend (ETAPA 3)

#### Flujo y Contratos de API
- **Endpoints Modificados:**
  - `POST /agents` -> Retornará `AgentResponse` con `created_at` como string obligatorio.
  - `POST /api/bundles/export` -> Validará las longitudes mínimas utilizando las constantes centralizadas importadas.
- **Manejo de Errores de Base de Datos:** En `src/api/routes/templates.py`, las excepciones se capturan limpiamente y se propagan como `HTTPException(status_code=503, detail="Database unavailable")` previniendo la fuga de trazas internas de PostgreSQL/Supabase hacia el cliente HTTP.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

#### Flujo de Integración End-to-End
- **Migración a httpx.AsyncClient en CLI:** CLI (`agent_run.py` y `crew.py`) dejarán de utilizar `httpx.Client()` síncrono. Al migrar a `httpx.AsyncClient` usando `asyncio.run()`, el CLI comparte la misma arquitectura asíncrona no-bloqueante del backend, mejorando dramáticamente los tiempos de polling concurrentes y previniendo bloqueos por sockets inactivos.

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

Para mitigar riesgos de drift de contratos y garantizar que ningún cambio de código rompa la robustez del backend, proponemos la siguiente herramienta de diagnóstico:

```
### Herramienta Propuesta: fap doctor api
- **Qué automatiza:** Analiza estáticamente todas las rutas FastAPI registradas, verifica la coherencia de tipos de retorno contra schemas de bundle, y audita los comandos CLI para asegurar que utilicen httpx.AsyncClient en lugar de hilos síncronos.
- **Tipo:** Comando CLI (Typer)
- **Cómo se usa:** uv run fap doctor api
- **Impacto para el usuario final:** Garantiza consistencia absoluta de contratos API a nivel de compilación estática y tipado antes de desplegar código a producción.
- **Prioridad:** Tarea 0 — Implementar antes del resto del paso.
```

---

### 5️⃣ Criterios de Aceptación

```
✅ [DATA] La serialización de la base de datos mapea siempre 'created_at' como string obligatorio sin defaults nulos.
✅ [CODE] Las constantes MIN_GOAL_LENGTH y MIN_BACKSTORY_LENGTH se definen en bundle_schemas.py y son la única fuente de verdad.
✅ [CODE] Las llamadas HTTP de agent_run.py y crew.py se realizan de manera 100% asíncrona mediante httpx.AsyncClient.
✅ [BACKEND] Los endpoints de templates capturan errores de red de DB y retornan 503 con formato JSON estándar.
✅ [BACKEND] Endpoint POST /agents retorna estado 201 conteniendo el campo created_at obligatorio.
✅ [CLI] Comando fap tools list reutiliza event loops de manera segura previniendo KeyError y colisiones de hilos.
✅ [DX] La herramienta fap doctor api reporta estado limpio (exit 0) sobre la estructura de endpoints del backend y CLI.
```

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** Incompatibilidad con datos antiguos en DB | Media | Registros antiguos en `agent_catalog` podrían tener `created_at` nulo si se insertaron manualmente en la DB sin defaults. | La columna física tiene constraint `NOT NULL DEFAULT NOW()`. En caso extremo de datos históricos locales sucios, correr una migración de limpieza de nulos en `agent_catalog`. |
| **R2:** Bloqueos en llamadas CLI asíncronas | Media | Migrar a `httpx.AsyncClient` requiere control estricto de timeouts y cierres de sesión para evitar descriptores de sockets abiertos. | Utilizar bloques de contexto `async with httpx.AsyncClient(...)` que aseguren el cierre automático de conexiones en runtime. |
| **R3:** Colisión de event loops concurrentes | Baja | Intentar invocar un comando CLI async dentro de otro subproceso asíncrono. | Usar `asyncio.get_event_loop()` o atrapar `RuntimeError` para reusar el loop activo transparentemente. |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap doctor api` | `src/cli/commands/doctor_api.py` | `def doctor_api() -> None` | `src/cli/commands/doctor_builder.py` | DX | Media | 1.5h | Ninguna | → verificar: `uv run fap doctor api` ejecuta sin errores |
| 1 | **Strict Typing**: Forzar `created_at` en Pydantic | `src/api/routes/agents.py` | `created_at: str` (línea 35, remover `| None = None`) | `src/api/routes/agents.py` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run fap doctor api` valida tipo de AgentResponse |
| 2 | **Validation Constants**: Centralizar mínimos | `src/services/bundle_schemas.py` | `MIN_GOAL_LENGTH = 10` y `MIN_BACKSTORY_LENGTH = 10` | `src/services/bundle_schemas.py` | CODE | Baja | 0.5h | Tarea 1 | → verificar: Importable en sesión python sin errores de sintaxis |
| 3 | **Backend Contract Sync**: Importar mínimos en API | `src/api/routes/bundles.py` | `from src.services.bundle_schemas import MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH` | `src/api/routes/bundles.py` | BACKEND | Baja | 0.5h | Tarea 2 | → verificar: `POST /api/bundles/export` lanza 422 ante payload < 10 |
| 4 | **CLI Validation Sync**: Importar mínimos en CLI | `src/cli/commands/bundle_validate_payload.py` | `from src.services.bundle_schemas import MIN_GOAL_LENGTH, MIN_BACKSTORY_LENGTH` | `src/cli/commands/bundle_validate_payload.py` | CODE | Baja | 0.5h | Tarea 2 | → verificar: `uv run fap bundle validate-payload` rechaza goal corto |
| 5 | **DB Error Mapping**: Confirmar HTTP 503 | `src/api/routes/templates.py` | `raise HTTPException(status_code=503, detail="Database unavailable")` | `src/api/routes/templates.py` | BACKEND | Baja | 0.5h | Ninguna | → verificar: `GET /api/templates` retorna 503 si DB se apaga |
| 6 | **CLI Loop Refactor**: Optimizar tools list | `src/cli/commands/tools_list.py` | `loop = asyncio.get_event_loop()` con fallback `asyncio.new_event_loop()` | `src/cli/commands/tools_list.py` | CODE | Media | 1.0h | Ninguna | → verificar: `uv run fap tools list` lista local y MCP sin advertencias |
| 7 | **CLI Async Migration**: Migrar `agent_run.py` | `src/cli/commands/agent_run.py` | `async with httpx.AsyncClient() as client:` | `src/cli/commands/tool_call_test.py` | CODE | Media | 1.0h | Tarea 6 | → verificar: `uv run fap agent run -r test_role -m test` ejecuta bien |
| 8 | **CLI Crew Async Migration**: Migrar `crew.py` | `src/cli/commands/crew.py` | `async with httpx.AsyncClient() as client:` | `src/cli/commands/tool_call_test.py` | CODE | Media | 1.0h | Tarea 7 | → verificar: `uv run fap crew save -n test` guarda snapshot async |
| 9 | **Fullstack live cycle verification** | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-8 | → verificar: Ejecución de `uv run fap doctor api` retorna verde completo |

**Tiempo total estimado:** 7.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Middleware unificado de Base de Datos:** Crear un decorador o middleware global que intercepte cualquier excepción de conectividad Supabase en el backend FastAPI y retorne automáticamente un HTTP 503 centralizado, eliminando bloques `try/except` repetitivos en rutas CRUD.
- **Persistencia de Conexiones en CLI:** Añadir soporte HTTP Keep-Alive persistente en `httpx.AsyncClient` dentro de los comandos CLI para acelerar las peticiones repetitivas de polling reduciendo el handshake TCP/TLS.
