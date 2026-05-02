# Análisis Técnico — Paso 2: Fix `test_3_5_latency.py`

**Agente:** qwen
**Fecha:** 2026-05-02
**Plan:** `DEVS/plan.md` — Paso 2
**Fase:** Hotfix post-certificación (Fase VI testing — CERRADA)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Archivo `tests/integration/test_3_5_latency.py` existe | glob | ✅ | 662 líneas |
| 2 | Clase `TestLatencyValidation` existe | línea 511 | ✅ | `class TestLatencyValidation:` |
| 3 | Función `test_full_latency_validation` existe | línea 523 | ✅ | `async def test_full_latency_validation(...)` |
| 4 | `pytestmark` module-level skipif existe | línea 46-49 | ✅ | `pytestmark = pytest.mark.skipif(not SUPABASE_URL, ...)` |
| 5 | `SUPABASE_SERVICE_KEY` definido como module var | línea 43 | ✅ | `SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` |
| 6 | `SUPABASE_ANON_KEY` en `.env.example` | `.env.example:3` | ✅ | `SUPABASE_ANON_KEY=your-anon-key` |
| 7 | `SUPABASE_SERVICE_KEY` en `.env.example` | `.env.example:4` | ✅ | `SUPABASE_SERVICE_KEY=your-service-key` |
| 8 | `load_dotenv()` antes de `os.getenv()` | línea 36 antes de 42-43 | ✅ | Orden correcto |
| 9 | `MultiCrewFlow` importable | `src/flows/multi_crew_flow.py:35` | ✅ | `class MultiCrewFlow(BaseFlow)` |
| 10 | `EventStore.append_sync` existe | `src/events/store.py:153` | ✅ | `@staticmethod def append_sync(...)` |
| 11 | `LatencyValidator` clase existe | línea 128 | ✅ | `class LatencyValidator:` |
| 12 | `supabase_client` fixture async existe | línea 484 | ✅ | `async def supabase_client() -> AsyncClient` |
| 13 | `acreate_client` importado | línea 72 | ✅ | `from supabase import AsyncClient, AsyncClientOptions, acreate_client` |
| 14 | 4 tests en clase `TestLatencyValidation` | líneas 514-615 | ✅ | `test_clock_calibration`, `test_full_latency_validation`, `test_event_burst_handling`, `test_integrity_db_vs_received` |
| 15 | `pytest.mark.asyncio` decorador usado | líneas 514, 523, 542, 579 | ✅ | Todos los tests async decorados |
| 16 | `_cleanup_events` helper existe | línea 113 | ✅ | `async def _cleanup_events(...)` |
| 17 | `global_llm_mock` fixture autouse | `tests/conftest.py:274` | ✅ | `@pytest.fixture(autouse=True)` |
| 18 | `mock_tenant_client` fixture | `tests/conftest.py:174` | ✅ | Mock de `get_tenant_client()` context manager |

### Discrepancias detectadas

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | Plan.md usa `SUPABASE_ANON_KEY` en skipif propuesto pero archivo real usa `SUPABASE_SERVICE_KEY` (línea 43, 491) | Usar `SUPABASE_SERVICE_KEY` — es la variable que `acreate_client` necesita como segundo argumento |
| D2 | `pytestmark` ya existe (línea 46-49) verificando solo `SUPABASE_URL`. Plan propone agregar skipif nuevo a nivel clase/función → crearía doble skip redundante | Expandir `pytestmark` existente para incluir `not SUPABASE_SERVICE_KEY`. No crear skipif adicional |
| D3 | Reason del skipif actual dice "Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY" pero condición solo verifica URL | Corregir condición para que coincida con reason — verificar ambas variables |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**N/A.** Paso 2 no modifica schema, migraciones, RLS ni estructuras de datos.

- Sin tablas nuevas
- Sin columnas agregadas
- Sin cambios en `domain_events` (tabla que el test usa indirectamente vía `EventStore.append_sync`)
- Sin migraciones necesarias

El test lee/escribe `domain_events` durante ejecución pero eso es comportamiento existente, no cambio de schema.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivo afectado

**`tests/integration/test_3_5_latency.py`** — 662 líneas

### Estructura actual del archivo

```
línea 1-18:   Docstring + metadata
línea 20-36:  Imports stdlib + load_dotenv()
línea 38-49:  Config (SUPABASE_URL, SUPABASE_SERVICE_KEY, pytestmark skipif)
línea 51-65:  Umbrales + logging setup
línea 67-72:  Imports proyecto (MultiCrewFlow, supabase AsyncClient)
línea 74-91:  Helpers (_iso_to_epoch, _percentile)
línea 94-120: DB helpers (_get_valid_org_id, _count_events_in_db, _cleanup_events)
línea 127-477: Clase LatencyValidator (6 fases: calibrate, subscribe, warmup, run, analyze, close)
línea 484-508: Fixtures pytest (supabase_client, test_org_id, task_id)
línea 511-615: Clase TestLatencyValidation (4 tests)
línea 622-662: Main ejecutable standalone (_main + __main__)
```

### Firma de componentes clave

| Componente | Firma | Ubicación |
|---|---|---|
| `LatencyValidator.__init__` | `(self, supabase: AsyncClient, task_id: str, org_id: str) -> None` | línea 131 |
| `LatencyValidator.calibrate_clock` | `async (self) -> None` | línea 142 |
| `LatencyValidator.start_monitoring` | `async (self) -> None` | línea 186 |
| `LatencyValidator.run_multi_crew_flow` | `async (self) -> None` | línea 280 |
| `LatencyValidator.analyze_results` | `async (self) -> dict[str, Any]` | línea 375 |
| `LatencyValidator.close` | `async (self) -> None` | línea 469 |
| `supabase_client` fixture | `async () -> AsyncClient` | línea 484 |
| `test_org_id` fixture | `async (supabase_client: AsyncClient) -> str` | línea 499 |
| `task_id` fixture | `() -> str` | línea 505 |
| `test_clock_calibration` | `async (self, supabase_client, test_org_id) -> None` | línea 514 |
| `test_full_latency_validation` | `async (self, supabase_client, test_org_id, task_id) -> None` | línea 523 |
| `test_event_burst_handling` | `async (self, supabase_client, test_org_id, task_id) -> None` | línea 542 |
| `test_integrity_db_vs_received` | `async (self, supabase_client, test_org_id, task_id) -> None` | línea 579 |

### Bug identificado

`pytestmark` línea 46-49:
```python
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)
```

Problema: condición verifica solo `SUPABASE_URL`. Si `SUPABASE_URL` está definida pero `SUPABASE_SERVICE_KEY` es `None`, el test corre y `acreate_client(SUPABASE_URL, None, ...)` lanza `SupabaseException`.

### Fix propuesto

Reemplazar líneas 46-49:
```python
# ANTES
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)

# DESPUÉS
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido",
)
```

### Por qué NO seguir el plan literalmente

Plan propone:
```python
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"
)
```

Problemas:
1. **Variable incorrecta:** `SUPABASE_ANON_KEY` no se usa en este archivo. Se usa `SUPABASE_SERVICE_KEY` (línea 43, 491).
2. **Doble skip innecesario:** Ya existe `pytestmark` module-level. Agregar decorador a nivel clase duplica lógica.
3. **`os.getenv()` redundante:** Las vars ya están cargadas como constantes de módulo (líneas 42-43). Usar directamente `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` es más limpio.

### Patrón de referencia

No hay precedente de `@pytest.mark.skipif` a nivel clase en `tests/integration/`. El único skipif existente es el propio `pytestmark` de este archivo.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**N/A.** Paso 2 no toca APIs, middleware, endpoints ni contratos backend.

Sin cambios en:
- Rutas API (`src/api/routes/`)
- Middleware (`src/api/middleware.py`)
- CLI commands (`src/cli/commands/`)
- Flujos de datos entre servicios

El test es de integración pura: mide latencia Supabase Realtime (WebSocket) contra inserts en `domain_events`. No pasa por API REST del proyecto.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
CI/local ejecuta pytest
→ test_3_5_latency.py se colecta
→ Módulo carga: load_dotenv() → lee SUPABASE_URL, SUPABASE_SERVICE_KEY
→ pytestmark.skipif evaluado
  → SI falta URL o SERVICE_KEY → SKIPPED (todos los tests)
  → SI ambas presentes → tests corren (requieren DB real + Realtime activo)
→ CI no se bloquea sin credenciales
→ Gate: pytest muestra SKIPPED, no FAILED ✅
```

### Coherencia con phase-state.md

- `phase-state.md` decisión #7: "Fix `test_3_5_latency`: Skip condicional via `skipif` + mover a `tests/integration/`" — ya movido, skipif parcial existe
- `phase-state.md` línea 91: discrepancia conocida "Bug approval rules: `>=`/`<=`/`==` fixeado en Paso 2" — este es OTRO Paso 2 (hotfix post-certificación), no confundir con Paso 2 de Fase VI original
- Plan v3.2 es hotfix post-certificación — contexto correcto

### Gaps identificados

1. **Imports del proyecto al inicio del archivo** (líneas 71-72): `MultiCrewFlow` y `acreate_client` se importan a nivel módulo. Si el módulo se carga sin credenciales, `MultiCrewFlow` importa `BaseCrew` → `get_service_client` → puede fallar si no hay mocks activos. PERO: `global_llm_mock` fixture es autouse y `mock_service_client` existe en conftest. Para tests pytest esto funciona. Para ejecución standalone (`python test_3_5_latency.py`) el main ya maneja el caso (línea 625-627: `sys.exit(1)`).

2. **Reason string del skipif:** Plan propone `"Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"`. Reason actual dice `"Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env"`. Ambas son válidas. Usar la del plan para consistencia con documentación.

### DX & Tooling

```
### Herramienta Propuesta: fap check-env
- **Qué automatiza:** Verifica que variables de entorno requeridas existen antes de ejecutar tests de integración que dependen de servicios externos
- **Tipo:** CLI (comando fap)
- **Cómo se usa:** `fap check-env --profile integration` → lista vars requeridas, marca presentes/ausentes, retorna exit code 1 si faltan críticas
- **Impacto para usuario final:** Evita ejecutar `pytest tests/integration/` y descubrir tras 30 segundos que falló por falta de credenciales. Feedback inmediato (<1s)
- **Prioridad:** Baja — el skipif resuelve el problema inmediato. Herramienta útil para onboarding y CI debugging
```

Implementación sugerida:
- Archivo: `src/cli/commands/check_env.py`
- Firma: `def check_env(profile: str = "integration") -> None`
- Perfiles: `integration` (SUPABASE_URL, SUPABASE_SERVICE_KEY), `full` (todas las de .env.example)
- Patrón a seguir: `src/cli/commands/baseline_check.py` — misma estructura de verificación + tabla Rich

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] tests/integration/test_3_5_latency.py pytestmark verifica SUPABASE_URL y SUPABASE_SERVICE_KEY
✅ [CODE] No existe skipif duplicado a nivel clase o función
✅ [BACKEND] Sin SUPABASE_URL → pytest muestra SKIPPED (no FAILED)
✅ [BACKEND] Sin SUPABASE_SERVICE_KEY → pytest muestra SKIPPED (no FAILED)
✅ [FULLSTACK] Con ambas vars definidas → tests corren normalmente (comportamiento existente preservado)
✅ [DX] fap check-env comando existe y ejecuta sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Skipif oculta fallo real de latencia | Baja | Si Supabase disponible pero Realtime roto, test debería fallar | Skipif solo activa cuando faltan credenciales. Con credenciales, test corre y falla si hay problema real |
| `MultiCrewFlow` import tiene side effects | Media | Import de `multi_crew_flow.py` → importa `BaseCrew` → importa `get_service_client`. Si no hay mock en contexto de import module-level, puede fallar | Verificar que imports son seguros. En pytest, fixtures autouse proveen mocks. En standalone, main verifica vars antes de importar |
| Confusión ANON_KEY vs SERVICE_KEY | Baja | Plan dice ANON_KEY, código usa SERVICE_KEY | Resuelto en §0 D1 — usar SERVICE_KEY |
| `load_dotenv()` no encuentra .env | Baja | .env no existe o ruta incorrecta | Ya manejado: vars quedan `None` → skipif activa. `load_dotenv()` no lanza excepción si archivo no existe |
| Tests de integración real requieren Supabase Realtime activo | Media | No es solo credenciales — servicio Realtime debe estar habilitado en proyecto Supabase | Fuera de alcance de este fix. Es limitación inherente del test de integración real |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap check-env` | `src/cli/commands/check_env.py` | `def check_env(profile: str = typer.Option("integration", "--profile")) -> None` | `src/cli/commands/baseline_check.py` — estructura de verificación + tabla Rich + exit code | DX | Baja | 0.3h | Ninguna | → verificar: `uv run python -m src.cli.main check-env --help` ejecuta sin errores |
| 1 | **Fix skipif module-level** | `tests/integration/test_3_5_latency.py` líneas 46-49 | **Reemplazar:** `pytestmark = pytest.mark.skipif(not SUPABASE_URL or not SUPABASE_SERVICE_KEY, reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido")` | Patrón existente: mismo archivo línea 46-49 (expandir condición existente, no crear nuevo skipif) | CODE | Baja | 0.05h | Ninguna | → verificar: `pytest tests/integration/test_3_5_latency.py -v` muestra 4 SKIPPED sin credenciales |
| 2 | **Registrar comando check-env en main.py** | `src/cli/main.py` | Agregar: `from src.cli.commands.check_env import check_env` + `app.command("check-env")(check_env)` | `src/cli/main.py:54` — patrón `app.command("baseline-check")(baseline_check)` | CODE | Baja | 0.05h | Tarea 0 | → verificar: `uv run python -m src.cli.main check-env --profile integration` muestra vars requeridas |

**Tiempo total estimado:** 0.4h

### Detalle Tarea 1 (fix skipif)

**Archivo:** `tests/integration/test_3_5_latency.py`
**Líneas:** 46-49

```python
# ANTES (líneas 46-49):
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)

# DESPUÉS:
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido",
)
```

**Notas:**
- Usar `SUPABASE_SERVICE_KEY` (constante de módulo línea 43), NO `os.getenv("SUPABASE_ANON_KEY")`
- No agregar skipif adicional a nivel clase o función — `pytestmark` aplica a todos los tests del módulo
- Reason actualizado para coincidir con plan.md

---

## 🔮 Roadmap

- `SUPABASE_ANON_KEY` definido en `.env.example` pero no usado en ningún test de integración. Considerar si tests de lectura pública deberían usar anon key en vez de service key.
- Tests de integración real se benefician de conftest compartido con skipif genérico para credenciales Supabase. Evitaría repetir lógica en cada archivo de test que requiera DB real.
- `fap check-env` podría extenderse para validar conectividad real (ping a Supabase URL), no solo presencia de variables.
