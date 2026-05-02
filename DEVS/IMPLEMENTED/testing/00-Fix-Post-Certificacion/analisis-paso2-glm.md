# Análisis Técnico — Paso 2: Fix `test_3_5_latency.py`

> **Agente:** glm
> **Paso:** 2 — Fix `test_3_5_latency.py`
> **Fecha:** 2026-05-02
> **Fuente:** `DEVS/plan.md` v3.2 + código fuente real

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `tests/integration/test_3_5_latency.py` existe | `ls tests/integration/` | ✅ | Directorio listing confirma archivo presente |
| 2 | `pytestmark = pytest.mark.skipif` ya existe en línea 46 | Lectura completa del archivo | ✅ | Línea 46-49: `pytestmark = pytest.mark.skipif(not SUPABASE_URL, reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env")` |
| 3 | Variable `SUPABASE_URL` leída en línea 42 | Lectura completa | ✅ | `SUPABASE_URL = os.getenv("SUPABASE_URL")` |
| 4 | Variable `SUPABASE_SERVICE_KEY` leída en línea 43 | Lectura completa | ✅ | `SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` |
| 5 | `os` importado en línea 25 | Lectura completa | ✅ | `import os` |
| 6 | Clase `TestLatencyValidation` existe en línea 511 | Lectura completa | ✅ | `class TestLatencyValidation:` |
| 7 | Método `test_full_latency_validation` existe en línea 524 | Lectura completa | ✅ | `async def test_full_latency_validation(...)` |
| 8 | Plan pide `SUPABASE_ANON_KEY` en skipif | Plan vs código | ❌ | Plan dice `os.getenv("SUPABASE_ANON_KEY")` pero archivo usa `SUPABASE_URL`, no `SUPABASE_ANON_KEY`. Variable usada = `SUPABASE_SERVICE_KEY` |
| 9 | Skipif actual solo chequea `SUPABASE_URL` | Plan vs código | ❌ | Skipif actual (línea 47): `not SUPABASE_URL` — no verifica `SUPABASE_SERVICE_KEY` ni `SUPABASE_ANON_KEY` |
| 10 | `acrocreate_client` usa `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Lectura línea 491 | ✅ | `await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=options)` |
| 11 | `.env.example` define `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` | Lectura `.env.example` | ✅ | Las 3 vars presentes |
| 12 | `tests/test_3_1_realtime.py` usa `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Grep | ✅ | Línea 27: `SUPABASE_URL = os.getenv("SUPABASE_URL")`, también `SUPABASE_SERVICE_KEY` |
| 13 | Función `_main()` chequea ambas vars | Lectura líneas 625-626 | ✅ | `if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:` |

### Discrepancias encontradas:

**D1.** Plan dice usar `SUPABASE_ANON_KEY` en skipif, pero el test usa `SUPABASE_SERVICE_KEY` (no `SUPABASE_ANON_KEY`). El test de integración Realtime necesita **service key** para operaciones admin (insert, rpc), no anon key. **Resolución:** Verificar `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` (no `SUPABASE_ANON_KEY`).

**D2.** Skipif actual (línea 46-49) solo verifica `SUPABASE_URL`, pero `acrocreate_client()` en la fixture `supabase_client` requiere también `SUPABASE_SERVICE_KEY`. Si `SUPABASE_URL` existe pero `SUPABASE_SERVICE_KEY` no → test explota con error críptico en vez de SKIPPED. **Resolución:** skipif debe verificar AMBAS: `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`.

**D3.** Skipif actual usa `pytestmark = pytest.mark.skipif(...)` a nivel módulo (línea 46), no decorador `@pytest.mark.skipif` por método. Plan dice "Antes de la clase `TestLatencyValidation` o función `test_full_latency_validation`". El `pytestmark` a nivel módulo YA CUMPLE el propósito (aplica a todo el módulo). Ambos enfoques son válidos pero difieren del plan. **Resolución:** Mantener `pytestmark` a nivel módulo — es más robusto (cubre `test_clock_calibration` y `_main()` también). Agregar verificación de `SUPABASE_SERVICE_KEY` al skipif existente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Sin cambios. El test interactúa con tablas `organizations` y `domain_events` (ya existentes en migraciones 004 y 021-022).
- ✅ **Integridad referencial:** `domain_events.org_id` FK a `organizations.id`. Test consulta `organizations` para obtener `org_id` válido, luego inserta en `domain_events`.
- ✅ **RLS:** `domain_events` tiene `tenant_isolation` via `org_id`. Test usa `SUPABASE_SERVICE_KEY` que bypass RLS — correcto para test de integración.
- ✅ **Índices:** Sin cambios necesarios.
- ✅ **Tipos:** Sin problemas. `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` son `str | None` via `os.getenv()`.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Función a modificar:** skipif a nivel módulo en `test_3_5_latency.py` líneas 46-49.
  
  **Firma actual:**
  ```python
  pytestmark = pytest.mark.skipif(
      not SUPABASE_URL,
      reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
  )
  ```
  
  **Firma propuesta:**
  ```python
  pytestmark = pytest.mark.skipif(
      not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"),
      reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido",
  )
  ```

- ✅ **Patrones:** `pytestmark` a nivel módulo es patrón existente en el propio archivo. Otros tests en el proyecto usan `pytest.mark.skip` (no `skipif`). Patrón de skipif con env vars = estándar pytest.
- ✅ **Modularidad:** Cambio mínimo, localizado en 1 línea (~4 líneas con reason). No afecta otras funciones.
- ✅ **Imports:** `os` ya importado (línea 25). Se cambia de usar variable pre-asignada `SUPABASE_URL` a `os.getenv("SUPABASE_URL")` directamente en skipif — más idiomático. Las variables de entorno `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` siguen existiendo para uso del módulo.
- ✅ **Calidad:** Sin impacto en complejidad ciclomática. Cambio es una condición bool más.

### Detalle técnico del skipif

El `pytestmark` a nivel módulo es preferible al decorador por método porque:
1. Cubre TODOS los tests del módulo (`test_clock_calibration`, `test_full_latency_validation`, `test_event_burst_handling`, `test_integrity_db_vs_received`)
2. Evita que fixtures async (`supabase_client`) se ejecuten si las env vars faltan
3. Es consistente con el patrón ya existente en el archivo

**Pero** el `reason` del plan es correcto y debe actualizarse también. El reason actual mienta: dice "SUPABASE_URL y SUPABASE_SERVICE_KEY" pero solo verifica `SUPABASE_URL`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** Sin cambios. No se tocan endpoints.
- ✅ **Middleware:** Sin cambios.
- ✅ **Flujos:** Test de integración conecta a Supabase Real. Skipif solo controla si se ejecuta o no en CI/local.
- ✅ **Contratos:** El test promete: si `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` existen → ejecutar prueba de latencia Realtime. Si faltan → SKIP.
- ✅ **Error handling:** Sin skipif actual adecuado, test FALLA con error críptico (conexion refused / auth error) en vez de SKIP limpio.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** CI env no tiene Supabase vars → sin skipif → test FAILED. Con skipif correcto → test SKIPPED. QA/local con Supabase real → test se ejecuta normalmente.
- ✅ **Coherencia:** Decisión phase-state.md §4.D7: "Skip condicional via `skipif` + mover a `tests/integration/`". Archivo ya está en `tests/integration/`. Solo falta corregir skipif.
- ✅ **Alineación:** Plan es realizable. Un solo cambio de 4 líneas.
- ✅ **Gaps:** Ninguno significativo.
- ✅ **DX & Tooling (OBLIGATORIO):**

```
### Herramienta Propuesta: fap test-skip-check
- **Qué automatiza:** Verificar qué tests de integración/e2e se skipping vs failing sin Supabase real. Ejecuta `pytest --collect-only -q` + analiza markers skipif para reportar qué tests se skipEARÍAN en CI sin env vars.
- **Tipo:** comando CLI
- **Cómo se usa:** `fap test-skip-check [--env SUPABASE_URL,SUPABASE_SERVICE_KEY]`
- **Impacto para el usuario final:** Evita sorpresas en CI: reporta qué tests se skipearían antes de ejecutar la suite completa. Detecta tests que FALLARIAN por falta de env vars.
- **Prioridad:** Baja — no bloquea implementación del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] skipif verifica tanto SUPABASE_URL como SUPABASE_SERVICE_KEY
✅ [CODE] reason actualizado a "Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"
✅ [TEST] pytest tests/integration/test_3_5_latency.py -v muestra SKIPPED (no FAILED) cuando env vars faltan
✅ [CODE] Variables SUPABASE_URL y SUPABASE_SERVICE_KEY siguen disponibles para fixtures y _main()
✅ [FULLSTACK] CI sin Supabase env vars: test SKIPPED. Local con env vars: test corre normalmente
✅ [DX] Herramienta fap test-skip-check propuesta (prioridad baja, no bloquea)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Skipif no verifica `SUPABASE_SERVICE_KEY` (estado actual) — test explota en vez de SKIP | Alta | `acrocreate_client()` recibe `SUPABASE_SERVICE_KEY=None` cuando env var falta → `TypeError` o auth error críptico | Cambiar skipif a verificar ambas vars |
| Plan usa `SUPABASE_ANON_KEY` en skipif pero test usa `SUPABASE_SERVICE_KEY` | Media | Confusión entre anon key y service key en plan | Usar `SUPABASE_SERVICE_KEY` (correcto para ops admin del test) |
| `pytestmark` a nivel módulo vs decorador por método | Baja | Plan sugiere decorador antes de la clase, pero `pytestmark` ya existe y es más robusto | Mantener `pytestmark` a nivel módulo |
| Skipif podría ocultar fallo real si Supabase está accesible pero mal configurado | Baja | Test se skipea si cualquier var falta, incluso si servicio está disponible | Reason del skipif ya indica "bug conocido". Queda registro del P0. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX:** skip-check CLI (Opcional, prioridad baja) | `src/cli/commands/test_skip_check.py` | `def check_skip_markers(env_vars: list[str] | None = None) -> dict[str, Any]` | `src/cli/commands/baseline_check.py :: run()` | DX | Baja | 0.5h | Ninguna | → verificar: `fap test-skip-check --help` ejecuta sin errores |
| 1 | Corregir skipif en test_3_5_latency.py | `tests/integration/test_3_5_latency.py:46-49` | Cambiar `not SUPABASE_URL` → `not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY")`._reason = `"Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"` | `pytestmark = pytest.mark.skipif(...)` patrón existente línea 46 | CODE | Baja | 0.05h | Ninguna | → verificar: `pytest tests/integration/test_3_5_latency.py -v` muestra `SKIPPED` cuando env vars faltan |
| 2 | Eliminar vars redundantes si skipif ya no las usa | `tests/integration/test_3_5_latency.py:42-44` | Mantener `SUPABASE_URL = os.getenv("SUPABASE_URL")` y `SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` — usadas por fixtures líneas 491, 636. Eliminar comentario de línea 45-48 si queda obsoleto. | Sin cambios, cleanup menor | CODE | Baja | 0.02h | Tarea 1 | → verificar: `ruff check tests/integration/test_3_5_latency.py` → 0 errores |

**Tiempo total estimado:** 0.12h (sin DX) / 0.62h (con DX)

---

## 🔮 Roadmap (NO implementar ahora)

- `fap test-skip-check` — comando CLI que detecta tests que FALLARÍAN por falta de env vars (prioridad baja)
- Unificar patrón skipif en todos los tests de integración que dependen de Supabase real (`test_3_1_realtime.py` también usa vars sin skipif)
- Considerar `@pytest.mark.integration` marker custom para separar tests que necesitan infraestructura real

---

## 🚫 Reglas de Oro — Checklist

- ✅ Análisis accionable y específico, no genérico
- ✅ TODO verificado contra código
- ✅ Discrepancia señalada: plan usa `SUPABASE_ANON_KEY` → código usa `SUPABASE_SERVICE_KEY`
- ✅ Discrepancia señalada: skipif actual solo verifica 1 var, no 2
- ✅ Si el plan contradice el código → el código gana + discrepancia documentada (D1, D2, D3)
- ✅ Coherente con phase-state.md
- ✅ TODO el paso cubierto (skipif + reason + variables)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta
- ✅ Tareas atómicas: 1 tarea = 1 artefacto
- ✅ Interfaz exacta por tarea
- ✅ Patrón de referencia explícito
- ✅ Verificación inline por tarea

---

## 📊 Métrica de Calidad

| Métrica | Valor |
|---|---|
| `proyecto-config.json` leído | ✅ 100% |
| Elementos verificados (§0) | 13 (≥ 8 para 1-2 archivos) |
| Discrepancias detectadas | 3 (D1, D2, D3) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 6, verificables |
| Riesgos identificados | 4 (1 alto, 1 medio, 2 bajo) |
| Tareas atómicas | 3 (2 obligatorias + 1 DX opcional) |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia por tarea | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 0 |
| Propuesta DX | 1 herramienta (`fap test-skip-check`) |
| Estimación de tiempo | 0.12h (sin DX) |