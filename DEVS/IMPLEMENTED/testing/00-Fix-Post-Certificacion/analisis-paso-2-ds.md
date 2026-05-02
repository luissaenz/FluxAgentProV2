# Análisis — Paso 2: Fix `test_3_5_latency.py`

**Agente:** ds
**Fecha:** 2026-05-02
**Plan:** `DEVS/plan.md` — Paso 2
**Fase:** Hotfix post-certificación (Fase VI testing — CERRADA)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Archivo `tests/integration/test_3_5_latency.py` existe | glob `tests/integration/test_3_5_latency.py` | ✅ | Archivo 662 líneas |
| 2 | Clase `TestLatencyValidation` existe | grep en archivo | ✅ | Línea 511 |
| 3 | Función `test_full_latency_validation` existe | grep en archivo | ✅ | Línea 523-539 |
| 4 | `pytestmark` module-level skipif existe | grep en archivo | ✅ | Línea 46-49 |
| 5 | `SUPABASE_SERVICE_KEY` usado en archivo | grep | ✅ | Líneas 43, 48, 491, 625, 626, 636 |
| 6 | `SUPABASE_ANON_KEY` existe en cualquier .py | grep codebase | ❌ No existe | 0 resultados en todo el proyecto |
| 7 | `SUPABASE_ANON_KEY` definido en `.env.example` | read `.env.example` | ✅ | Línea 3 |
| 8 | `SUPABASE_SERVICE_KEY` definido en `.env.example` | read `.env.example` | ✅ | Línea 4 |
| 9 | Skip condicional en otros tests integración | grep `skipif` en `tests/integration/` | ✅ | Solo 1 — el mismo archivo |
| 10 | Patrón skipif en `test_3_1_realtime.py` | read | ❌ Usa `if not ...: sys.exit(1)` — no usa pytest.skipif |

### Discrepancias detectadas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan.md usa `SUPABASE_ANON_KEY` pero archivo real usa `SUPABASE_SERVICE_KEY` | Usar `SUPABASE_SERVICE_KEY` que es la variable real del archivo. `.env.example` define ambas. |
| D2 | Archivo YA tiene `pytestmark` module-level `skipif(not SUPABASE_URL, ...)` (línea 46-49). Plan no lo menciona. | Agregar `os.getenv("SUPABASE_SERVICE_KEY")` a condición existente EN VEZ de crear skipif duplicado a nivel clase. Doble skipif es redundante y confuso. |
| D3 | Skipif actual cubre solo `SUPABASE_URL`, no `SUPABASE_SERVICE_KEY` | Expandir skip actual para cubrir ambas variables. |

---

## 1️⃣ Análisis de Datos

**N/A.** Paso 2 no toca schema, migraciones, RLS ni datos.

Sin cambios en DB. Sin nuevas tablas. Sin migraciones.

---

## 2️⃣ Análisis de Código

### Archivo afectado

**`tests/integration/test_3_5_latency.py`** (662 líneas)

### Flujo actual

```
módulo carga .env
→ SUPABASE_URL = os.getenv("SUPABASE_URL")
→ SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
→ pytestmark = skipif(not SUPABASE_URL, reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY")
  → NOTA: reason dice ambas vars pero check solo verifica URL
→ 4 métodos en TestLatencyValidation
  → test_clock_calibration
  → test_full_latency_validation
  → test_event_burst_handling
  → test_integrity_db_vs_received
```

### Bug

`pytestmark` skipif (línea 46-49) chequea solo `not SUPABASE_URL`. Si `SUPABASE_URL` está definida pero `SUPABASE_SERVICE_KEY` no, el test corre y falla con `SupabaseException` porque `acreate_client` recibe `None` como key.

### Fix propuesto en plan

Agregar `@pytest.mark.skipif(not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"), ...)` a nivel clase o función.

### Problemas con fix propuesto

1. **Variable equivocada:** `SUPABASE_ANON_KEY` no es usada en este archivo. Usa `SUPABASE_SERVICE_KEY`.
2. **Doble skip:** Ya existe `pytestmark` module-level. Agregar class-level skipif crea 2 capas de skip innecesarias. Si module-level skips, class-level ni se evalúa — confuso para debug.
3. **Patrón existente:** `test_3_1_realtime.py` no usa pytest.skipif en absoluto (línea 30-32: `sys.exit(1)`). No hay precedente de class-level skipif en tests de integración.

### Recomendación

**Reemplazar** el `pytestmark` existente (línea 46-49) para que verifique ambas variables:

```python
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)
```

### Patrón existente en el proyecto

- `tests/test_3_1_realtime.py:30-32`: `if not SUPABASE_URL or not SUPABASE_SERVICE_KEY: print(...); sys.exit(1)`
- Ningún test de integración usa `@pytest.mark.skipif` a nivel clase.
- El único `pytestmark` en tests/integration es el propio `test_3_5_latency.py`.

---

## 3️⃣ Análisis de Backend

**N/A.** Paso 2 no toca APIs, middleware, endpoints ni flujos backend.

Sin cambios en:
- Rutas API
- Middleware
- Contratos
- Error handling

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo

```
CI/local corre pytest
→ test_3_5_latency.py se colecta
→ pytestmark.skipif evaluado (module-level)
  → SI falta SUPABASE_URL o SUPABASE_SERVICE_KEY → SKIPPED (no FAILED)
  → SI ambas presentes → test corre (requiere DB real + Realtime)
→ CI no se bloquea si no hay credenciales Supabase
```

### Coherencia con plan

- Plan dice "que test no bloquee CI/local" — objetivo correcto
- Plan menciona `SUPABASE_ANON_KEY` pero archivo usa `SUPABASE_SERVICE_KEY` — incoherencia documentada
- Gate: "Test aparece como SKIPPED, no FAILED" — correcto y verificable

### Gaps

1. El skip solo chequea al import. Si el usuario setea las vars y falla Supabase reachability → test sigue fallando. Pero eso es comportamiento esperado (es test de integración real).
2. Si módulo se importa antes de `load_dotenv()`, las vars pueden no estar disponibles. Verificar que `load_dotenv()` está ANTES de leer vars.

**Verificación de orden:** Línea 36 `load_dotenv()` → Línea 42 `os.getenv("SUPABASE_URL")` → Línea 46 `skipif`. Orden correcto ✅.

### DX & Tooling

```
### Herramienta Propuesta: fap check-env
- **Qué automatiza:** Verificar que todas las env vars requeridas existen antes de correr tests de integración real
- **Tipo:** CLI (comando fap)
- **Cómo se usa:** `fap check-env --integration` → muestra qué vars faltan
- **Impacto para usuario final:** Evita correr tests que van a fallar por config incompleta
- **Prioridad:** Baja (el skipif ya resuelve el problema principal)
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] tests/integration/test_3_5_latency.py tiene skipif que verifica SUPABASE_URL y SUPABASE_SERVICE_KEY
✅ [BACKEND] Sin SUPABASE_URL → test aparece como SKIPPED
✅ [BACKEND] Sin SUPABASE_SERVICE_KEY → test aparece como SKIPPED  
✅ [FULLSTACK] Ejecución: `pytest tests/integration/test_3_5_latency.py -v` → SKIPPED (no FAILED) sin credenciales
✅ [DX] Skipif module-level, no duplicado (evitar class-level redundante)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `load_dotenv()` no encuentra .env | Baja | .env no existe o en otra ruta | Ya manejado: vars quedan como `None` → skipif activa |
| Skipif oculta regresión real de latencia | Baja | Si Supabase disponible pero Realtime roto | Test debe fallar cuando credenciales existen. skipif solo activa sin credenciales |
| Import temprano de módulos del proyecto (línea 71-72) sin credenciales | Media | `MultiCrewFlow` importado incluso si skip activo | Ya es así. Si `MultiCrewFlow` tiene side effects al import, podría romper incluso con skip. Verificar que el import es seguro. |
| `SUPABASE_ANON_KEY` vs `SUPABASE_SERVICE_KEY` confusión | Baja | Plan dice ANON_KEY, código usa SERVICE_KEY | Resuelto en §0 — usar SERVICE_KEY |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap check-env` | `src/cli/commands/check_env.py` | `def check_env(integration: bool = False) -> None` | `src/cli/commands/baseline_check.py` | DX | Baja | 0.3h | Ninguna | → verificar: `uv run python -m src.cli.main check-env --help` sin errores |
| 1 | **Fix skipif en `test_3_5_latency.py`** | `tests/integration/test_3_5_latency.py` | **Cambio en líneas 46-49:** reemplazar `pytestmark = pytest.mark.skipif(not SUPABASE_URL, ...)` por `pytestmark = pytest.mark.skipif(not SUPABASE_URL or not SUPABASE_SERVICE_KEY, ...)` | Patrón existente: propio archivo línea 30-32 (`if not SUPABASE_URL or not SUPABASE_SERVICE_KEY`) | CODE | Baja | 0.05h | Ninguna | → verificar: `pytest tests/integration/test_3_5_latency.py -v` muestra SKIPPED sin credenciales |

**Tiempo total estimado:** 0.35h

### Detalle Tarea 1

**Archivo:** `tests/integration/test_3_5_latency.py`
**Líneas:** 46-49
**Cambio:**

```python
# ANTES
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)

# DESPUÉS
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)
```

**No usar `os.getenv()` directo en el decorador.** Las vars ya están cargadas como módulo-level constants (líneas 42-43). Usar `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` directamente — más limpio y evaluado una sola vez.

---

## 🔮 Roadmap

- `SUPABASE_ANON_KEY` no usado en ningún test. Considerar si debe agregarse como checkpoint adicional (cliente anónimo vs service role).
- Tests de integración real se benefician de un `conftest.py` compartido con skipif genérico para credenciales Supabase.
