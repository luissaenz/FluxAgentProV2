# 🏛️ Análisis Unificado — Paso 2: Fix `test_3_5_latency.py`

> **Generado por:** UNIFICADOR v3.1
> **Fecha:** 2026-05-02
> **Plan:** `DEVS/plan.md` v3.2 — Paso 2
> **Fase:** Hotfix post-certificación (Fase VI testing — CERRADA)
> **Config:** `proyecto-config.json` v2.0 leído ✅

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:-------|:---------------:|:------------------------:|:------------:|:----------------:|:-----------:|
| kimi   | ✅ (12 checks)  | 5 (D1-D5)               | ✅ 2 tools   | ✅ archivos+ln   | 4.8         |
| qwen   | ✅ (18 checks)  | 3 (D1-D3)               | ✅ 1 tool    | ✅ archivos+ln   | 4.5         |
| glm    | ✅ (13 checks)  | 3 (D1-D3)               | ✅ 1 tool    | ✅ archivos+ln   | 3.8         |
| ds     | ✅ (10 checks)  | 3 (D1-D3)               | ✅ 1 tool    | ✅ archivos+ln   | 3.5         |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|-------------|---------|-------------------------|------------|
| 1 | Plan usa `SUPABASE_ANON_KEY` pero código usa `SUPABASE_SERVICE_KEY` | kimi (D2), qwen (D1), glm (D1), ds (D1) | ✅ `tests/integration/test_3_5_latency.py:43,491` | Skipif debe verificar `SUPABASE_SERVICE_KEY`, NO `SUPABASE_ANON_KEY`. `acreate_client()` línea 491 usa service key como 2do arg. |
| 2 | Plan pide decorador `@pytest.mark.skipif` a nivel clase/fn, pero código YA tiene `pytestmark` module-level (línea 46-49) | kimi (D1), qwen (D2), glm (D3), ds (D2) | ✅ `tests/integration/test_3_5_latency.py:46-49` | Mantener `pytestmark` module-level. Es más robusto: cubre TODOS los tests del módulo + fixtures async + `_main()`. No crear skipif duplicado. |
| 3 | Skipif actual solo verifica `SUPABASE_URL`, falta `SUPABASE_SERVICE_KEY` | kimi (D5), qwen (D3), glm (D2), ds (D3) | ✅ `tests/integration/test_3_5_latency.py:46-49` | Expandir condición: `not SUPABASE_URL or not SUPABASE_SERVICE_KEY`. Fix real del paso. |
| 4 | Reason del skipif actual dice "SUPABASE_URL y SUPABASE_SERVICE_KEY" pero condición solo verifica URL — inconsistencia | kimi (D3), qwen (D3) | ✅ `tests/integration/test_3_5_latency.py:46-49` | Actualizar reason a versión fusionada: `"Requiere Supabase Realtime + DB real — requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env"` |
| 5 | Paso 2 del plan v3.2 es redundante con trabajo ya realizado en Paso 0 (Auditoría de Línea Base, decisión #7) | kimi (D5) | ✅ `DEVS/phase-state.md:146` | El archivo YA fue movido a `tests/integration/` y YA tiene skipif parcial. El fix pendiente es menor: expandir condición. No es un cambio desde cero. |

### Detalle de Aportes por Agente

**kimi** — análisis más profundo. Detectó 5 discrepancias vs 3 del resto. Identificó problemas únicos: RPC `get_server_time` no documentado en migraciones, datos residuales por SIGKILL, redundancia con Paso 0. Propuso 2 herramientas DX útiles. Verificación contra código más detallada (12 checks con evidencia de línea exacta).

**qwen** — segundo más completo. 18 verificaciones contra código (máximo). Análisis de estructura del archivo más granular (mapeo línea por línea). Detectó bug concreto con código de fix exacto. Único en notar que imports tempranos de `MultiCrewFlow` pueden tener side effects.

**glm** — análisis correcto pero menos profundo en data/backend. Propsuesta DX `test-skip-check` interesante pero menos práctica que `check-env`. Recomienda usar `os.getenv()` directo en skipif (otros recomiendan constantes de módulo — estas últimas ganan: evaluadas 1 vez al import, más limpias).

**ds** — análisis conciso pero sólido. Identificó que `SUPABASE_ANON_KEY` no existe en ningún `.py` del proyecto (0 resultados grep). Único en verificar patrón `test_3_1_realtime.py` (usa `sys.exit(1)`, no skipif). Recomendación más simple (solo 2 tareas, sin DX tooling obligatorio).

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Corregir skip condicional en `tests/integration/test_3_5_latency.py:46-49` para que test de latencia Realtime no bloquee CI/local cuando faltan credenciales Supabase. El archivo YA tiene `pytestmark` module-level pero con condición incompleta (solo `SUPABASE_URL`, falta `SUPABASE_SERVICE_KEY`).
- **Corrección crítica al plan:** Plan usa `SUPABASE_ANON_KEY` (incorrecto, no existe en el archivo). Código real usa `SUPABASE_SERVICE_KEY`. Plan propone decorador a nivel clase — código ya tiene `pytestmark` module-level (más robusto). Se implementa expansión del existente.
- **Herramienta DX seleccionada:** `fap check-env` (fusionado de propuestas qwen + ds + kimi). Verifica vars de entorno requeridas antes de ejecutar tests de integración real.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. CI/local ejecuta `pytest tests/integration/`
2. `test_3_5_latency.py` se colecta, módulo se importa
3. `load_dotenv()` carga `.env` (línea 36)
4. `SUPABASE_URL = os.getenv("SUPABASE_URL")` → string o None (línea 42)
5. `SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` → string o None (línea 43)
6. `pytestmark = pytest.mark.skipif(not SUPABASE_URL or not SUPABASE_SERVICE_KEY, ...)` evaluado
7. **Si falta alguna var** → 4 tests = SKIPPED (no FAILED). CI continúa sin bloquearse.
8. **Si ambas vars presentes** → tests corren contra Supabase real. Latencia Realtime se mide.
9. Makefile `test-all` puede eliminar `-k "not latency"` — skipif ya protege CI.

### Edge Cases MVP

| # | Edge Case | Comportamiento esperado |
|---|-----------|------------------------|
| 1 | `SUPABASE_URL` presente pero `SUPABASE_SERVICE_KEY` ausente → SKIPPED | Skipif evalúa `True` por `not SUPABASE_SERVICE_KEY`. Test no ejecuta `acreate_client()` con `None`. |
| 2 | `SUPABASE_SERVICE_KEY` presente pero `SUPABASE_URL` ausente → SKIPPED | Skipif evalúa `True` por `not SUPABASE_URL`. |
| 3 | `.env` no existe → vars = None → SKIPPED | `load_dotenv()` no lanza excepción si archivo no existe. `os.getenv()` retorna `None`. |
| 4 | Ambas vars presentes pero Supabase no alcanzable → test FAILED | Skipif evalúa `False`. Test corre y falla con excepción de red. Es comportamiento esperado (test de integración real). |
| 5 | Makefile `test-all` ejecuta sin `-k "not latency"` → latency tests protegidos por skipif | No require exclusión manual. Skipif module-level maneja todo. |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### M1: Expandir skipif en `test_3_5_latency.py`

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\tests\integration\test_3_5_latency.py`
- **Tipo de cambio:** Modificación
- **Descripción:** Expandir condición del `pytestmark` existente (líneas 46-49) para verificar `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`. Actualizar reason string. NO agregar decorador a nivel clase.
- **Interfaces clave:**
  ```python
  # ANTES (líneas 46-49):
  pytestmark = pytest.mark.skipif(
      not SUPABASE_URL,
      reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
  )
  
  # DESPUÉS:
  pytestmark = pytest.mark.skipif(
      not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
      reason="Requiere Supabase Realtime + DB real — requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
  )
  ```
- **Patrones a seguir:** `tests/integration/test_3_5_latency.py:46-49` — patrón existente en el mismo archivo. Usar constantes de módulo (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`), NO `os.getenv()` directo.

#### M2: Opcional — Eliminar `-k "not latency"` de Makefile

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\Makefile`
- **Tipo de cambio:** Modificación
- **Descripción:** Remover `-k "not latency"` del target `test-all` (línea 92). Skipif robusto hace innecesaria la exclusión manual.
- **Dependencia:** M1 debe estar implementado primero.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: `fap check-env`
- **Qué automatiza:** Verifica que todas las variables de entorno requeridas por tests de integración real estén presentes antes de ejecutar pytest. Elimina ciclo "correr test → falla por falta de env → revisar cuál falta → reintentar".
- **Tipo:** CLI comando (Typer app en `src/cli/main.py`)
- **Ubicación:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\check_env.py`
- **Firma:** `def check_env(profile: str = typer.Option("integration", "--profile")) -> None`
- **Patrón a seguir:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\baseline_check.py` — estructura de verificación + tabla Rich + exit code.
- **Registro en main.py:** `from src.cli.commands.check_env import check_env` + `app.command("check-env")(check_env)` (patrón línea 54 de `src/cli/main.py`)
- **Cómo se usa:** `uv run python -m src.cli.main check-env --profile integration`
  - Perfiles: `integration` (SUPABASE_URL, SUPABASE_SERVICE_KEY), `full` (todas las de .env.example)
  - Output: Tabla Rich con vars, estado (✅/❌), exit code 1 si faltan críticas
- **Impacto para el usuario final:** Feedback inmediato (<1s) si config está completa. Evita ejecutar pytest y descubrir tras 30s que falló por credenciales faltantes.
- **El implementador DEBE usarla** para verificar configuración antes de ejecutar tests de integración real.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Usar `pytestmark` module-level en vez de decorador de clase:** El plan propone `@pytest.mark.skipif` antes de clase/función. El código ya tiene `pytestmark` module-level (línea 46). Este patrón es superior porque: (a) aplica a TODOS los tests del módulo (4 tests + `_main()`), (b) evita que fixtures async (`supabase_client`) se ejecuten si env vars faltan, (c) es el patrón existente validado. El código gana.

2. **Usar constantes de módulo en skipif, no `os.getenv()` directo:** Las variables `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` ya están cargadas como constantes module-level (líneas 42-43) ANTES de la definición de `pytestmark` (línea 46). Usarlas directamente es: (a) más limpio, (b) evaluado una sola vez al import, (c) consistente con el resto del archivo que las usa en fixtures. `os.getenv()` en skipif sería redundante.

3. **Reason string fusionado:** El reason actual ("Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env") describe técnicamente qué falta. El reason del plan ("Requiere Supabase Realtime + DB real — plan.md P0 bug conocido") describe contexto de negocio. Se fusionan: "Requiere Supabase Realtime + DB real — requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env". Esto da contexto + diagnóstico sin tener que abrir el plan.

4. **No tocar `SUPABASE_ANON_KEY`:** Esta variable existe en `.env.example` pero no se usa en ningún test de integración del proyecto. El test de latencia usa `SUPABASE_SERVICE_KEY` para operaciones admin (insert, RPC, delete). `SUPABASE_ANON_KEY` sería insuficiente. No agregar al skipif.

5. **⚠️ Corrección al plan:** El plan dice `SUPABASE_ANON_KEY` pero el código real usa `SUPABASE_SERVICE_KEY`. Se implementa `SUPABASE_SERVICE_KEY`.

6. **⚠️ Corrección al plan:** El plan dice "Añadir `@pytest.mark.skipif`" como decorador nuevo. El código ya tiene `pytestmark` module-level. Se expande el existente, no se crea nuevo.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] skipif en test_3_5_latency.py:46-49 verifica SUPABASE_URL y SUPABASE_SERVICE_KEY
✅ [CODE] No existe skipif duplicado a nivel clase o función — solo pytestmark module-level
✅ [BACKEND] Sin SUPABASE_URL → pytest muestra SKIPPED (no FAILED)
✅ [BACKEND] Sin SUPABASE_SERVICE_KEY → pytest muestra SKIPPED (no FAILED)
✅ [BACKEND] Con ambas vars definidas → tests corren normalmente (comportamiento preservado)
✅ [DX] fap check-env comando existe y ejecuta sin errores
✅ [DX] Makefile test-all puede eliminar -k "not latency" (opcional tras skipif robusto)
```

**Funcionales:**
- [ ] `pytest tests/integration/test_3_5_latency.py -v` muestra 4 SKIPPED sin credenciales
- [ ] `pytest tests/integration/test_3_5_latency.py -v` ejecuta tests con credenciales
- [ ] `SUPABASE_URL=fake pytest tests/integration/test_3_5_latency.py -v` → SKIPPED (falta SERVICE_KEY)
- [ ] `ruff check tests/integration/test_3_5_latency.py` → 0 errores

**Técnicos:**
- [ ] `pytestmark` usa constantes de módulo, no `os.getenv()` directo
- [ ] Reason string fusionado: contexto de negocio + diagnóstico técnico
- [ ] Skipif module-level cubre 4 tests + `_main()` + fixtures async

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|-------|-------------|-------------|--------------|
| 0 | **DX & Tooling:** Crear `fap check-env` en `src/cli/commands/check_env.py` + registrar en `main.py` | Media | 0.3h | Ninguna |
| 1 | **Expandir skipif en `test_3_5_latency.py`** — cambiar condición + reason en líneas 46-49 | Baja | 0.05h | Tarea 0 (dogfooding: usar `fap check-env` para verificar vars) |
| 2 | **Opcional: Eliminar `-k "not latency"` de Makefile** línea 92 | Baja | 0.02h | Tarea 1 |
| | **TOTAL** | | **0.37h** | |

> **Tarea 0 = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap check-env` para verificar configuración antes de tests de integración.

### Detalle Tarea 1 — Expandir skipif

**Archivo:** `tests/integration/test_3_5_latency.py`
**Líneas:** 46-49

```python
# ANTES:
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL,
    reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)

# DESPUÉS:
pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="Requiere Supabase Realtime + DB real — requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env",
)
```

**Notas de implementación:**
- Usar `SUPABASE_SERVICE_KEY` (constante módulo línea 43), NO `os.getenv("SUPABASE_ANON_KEY")`
- NO agregar decorador a nivel clase o función
- Reason fusionado: contexto de negocio + diagnóstico técnico
- `ruff check` post-cambio debe retornar 0 errores

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Skipif incompleto causa TypeError si solo SUPABASE_URL presente | Media | Estado actual: `pytestmark` solo checkea URL, no SERVICE_KEY | Tarea 1 expande condición. Verificar con `SUPABASE_URL=fake pytest ...` |
| `-k "not latency"` en Makefile oculta tests que deberían correr en CI con DB real | Baja | Exclusión manual evita ejecución incluso con credenciales | Tarea 2 elimina exclusión. Skipif robusto maneja casos sin credenciales. |
| Import temprano de `MultiCrewFlow` (línea 71-72) sin credenciales tiene side effects | Media | `multi_crew_flow.py` → importa `BaseCrew` → importa `get_service_client` | En pytest, `global_llm_mock` fixture autuse provee mocks. En standalone, `_main()` verifica vars antes. No bloquea. |
| RPC `get_server_time` no existe en migraciones estándar | Media | Test depende de RPC que no está en schema versionado | Fuera de alcance de este paso. Documentar en TESTING.md como setup manual requerido. |
| Datos residuales si proceso recibe SIGKILL durante test | Baja | Cleanup en `finally` no ejecuta en SIGKILL | Herramienta `fap cleanup-test-events` propuesta para roadmap. Bajo riesgo por aggregate_id único con UUID. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|----|------|-------|-----------------|
| TP-1 | Sin credenciales Supabase | `pytest tests/integration/test_3_5_latency.py -v` sin .env | 4 SKIPPED (0 FAILED, 0 PASSED) |
| TP-2 | Solo SUPABASE_URL definida | `SUPABASE_URL=fake pytest tests/integration/test_3_5_latency.py -v` sin SERVICE_KEY | 4 SKIPPED (condición: not URL or not SERVICE_KEY → True) |
| TP-3 | Ambas vars definidas | `pytest tests/integration/test_3_5_latency.py -v` con .env completo | Tests ejecutan (no skipped). Pueden fallar si no hay Supabase reachable — es aceptable. |
| TP-4 | DX tool check-env | `uv run python -m src.cli.main check-env --help` | Muestra ayuda del comando sin errores |
| TP-5 | Lint skipif | `ruff check tests/integration/test_3_5_latency.py` | 0 errores |
| TP-6 | Makefile test-all (post Tarea 2) | `make test-all` | Test se skipea automáticamente si no hay credenciales. No requiere `-k "not latency"`. |

Comando para ejecutar tests: `uv run pytest tests/integration/test_3_5_latency.py -v --timeout=60`
Comando lint: `uv run ruff check tests/integration/test_3_5_latency.py`

---

## 📊 Calidad de Aportes por Análisis

| Agente | Score | Fortaleza | Debilidad |
|--------|:-----:|-----------|-----------|
| **kimi** | **4.8/5** | Máximas discrepancias (5), más profundo en data layer, identifica RPC gap y redundancia Paso 0. 2 herramientas DX. | Reason string indeciso (dice "documentar sin acción"). |
| **qwen** | **4.5/5** | Máximas verificaciones (18), estructura granular línea por línea, fix code exacto. | Data/backend marked "N/A" — análisis incompleto en esas etapas. |
| **glm** | **3.8/5** | Identifica D1-D3 correctamente. Recomienda `os.getenv()` directo (incorrecto vs constantes módulo). 13 verificaciones sólidas. | Data/backend superficial ("N/A" o "Sin cambios"). DX tool menos práctica. |
| **ds** | **3.5/5** | Conciso pero correcto. Único en verificar inexistencia de `SUPABASE_ANON_KEY` en todo el proyecto. Recomendación más simple (2 tareas). | Análisis menos profundo en todas las etapas. Menos verificaciones (10). |

**Veredicto:** kimi aportó el análisis más valioso (discrepancias únicas, profundidad técnica). qwen segundo mejor (granularidad y precisión). glm y ds correctos pero menos profundos. La unificación toma lo mejor de cada uno: discrepancia de kimi (RPC gap), estructura de qwen (mapeo de archivo), verificación de glm (13 checks), hallazgo de ds (ANON_KEY no existe en .py).

---

**Idioma de respuesta:** Español 🇪🇸
**Destino:** `D:\Develop\Personal\FluxAgentPro-v2\DEVS\IN_PROGRESS\analisis-FINAL.md`
