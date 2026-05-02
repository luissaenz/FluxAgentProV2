# Analisis Tecnico — Paso 7: Documentacion y Cierre

**Agente:** ds
**Fecha:** 2026-05-01
**Referencia:** `DEVS/plan.md` §Paso 7 (Documentacion y Cierre)
**Estado Fase:** testing — 2/8 pasos completados (phase-state.md)
**Config:** `proyecto-config.json` — paths.root=`D:\Develop\Personal\FluxAgentPro-v2`

---

## 0 Verificacion contra Codigo Fuente

| # | Elemento | Verificacion | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `TESTING.md` existe en raiz | glob `TESTING.md` | **NO EXISTE** | No encontrado |
| 2 | `Makefile` existe en raiz | glob `Makefile` | **EXISTE** | Makefile:1-177 — 177 lineas |
| 3 | `Makefile` target `test-all` existe | grep `test-all` en Makefile | **NO EXISTE** | No definido |
| 4 | `Makefile` target `test-fast` existe | grep `test-fast` en Makefile | **NO EXISTE** | No definido |
| 5 | `Makefile` target `coverage` existe | grep `coverage\|test-cov` en Makefile | **EXISTE** | Makefile:91-94 — target `test-cov`, no `coverage` |
| 6 | `Makefile` target `test` ejecuta pytest | Makefile:81-83 | **EXISTE** | `$(PYTEST) tests/ $(test-args)` |
| 7 | `Makefile` target `lint` usa ruff | Makefile:97-103 | **EXISTE** | `ruff check src/ tests/` |
| 8 | `Makefile` rutas compatibles Windows | paths con `.venv/bin/python` | **NO** | Makefile:7-10 — `.venv/bin/python`, `.venv/bin/pip`, `.venv/bin/pytest`, `.venv/bin/uvicorn` — todos Unix paths |
| 9 | `Makefile` `clean` target compatible Windows | `find` commands | **NO** | Makefile:108-114 — `find . -type d -name "__pycache__" -exec rm -rf {} +` — Unix-only |
| 10 | `Makefile` `stop` target compatible Windows | `pkill` command | **NO** | Makefile:145 — `pkill -f "uvicorn src.api.main:app"` — Unix-only |
| 11 | `CHANGELOG` existe en raiz | glob `CHANGELOG*` | **NO EXISTE** | No encontrado |
| 12 | Reporte cobertura HTML existe | glob `htmlcov/index.html` | **NO EXISTE** | No se ha generado |
| 13 | `fap phase-close` comando existe | grep en `src/cli/main.py` | **EXISTE** | main.py:21,52 — `phase_close` importado y registrado |
| 14 | `phase_close.py` soporta `--certify` | `src/cli/commands/phase_close.py` | **EXISTE** | phase_close.py:311-459 — `--certify` flag completo |
| 15 | Suite actual tests | `Get-ChildItem -Recurse test_*.py | Measure` | **EXISTE** | 59 archivos test |
| 16 | `pytest-cov` en dev dependencies | pyproject.toml:50 | **INSTALADO** | `"pytest-cov>=6.0.0"` |
| 17 | `pyproject.toml` tiene config coverage | pyproject.toml | **SIN CONFIG** | No hay `[tool.coverage.*]` ni `[tool.pytest.ini_options]` con `addopts` para coverage |
| 18 | `DEVS/IMPLEMENTED/testing/` estructura existe | ls `DEVS/IMPLEMENTED/testing/` | **EXISTE** | 7 subdirectorios: 00-06 |
| 19 | `DEVS/IMPLEMENTED/testing/` tiene carpeta paso 7 | ls `DEVS/IMPLEMENTED/testing/` | **NO EXISTE** | Solo 00-06 |
| 20 | `phase-state.md` marca paso 6 completado? | phase-state.md:18-23 | **PENDIENTE** | phase-state.md linea 23 dice `[ ] Paso 6` |
| 21 | `phase-state.md` marca paso 7 pendiente | phase-state.md:23 | **PENDIENTE** | Linea 24 dice `[ ] Paso 7: DX Final y Automatizacion CI` |
| 22 | `fap test-step` soporta paso 7 | `test_step.py` STEP_TEST_FILES | **NO** | test_step.py:23-42 — soporta pasos 1,2,3,5. No 4,6,7 |

### Discrepancias Encontradas

| # | Discrepancia | Resolucion |
|---|---|---|
| D1 | `Makefile` usa `.venv/bin/python` (Unix) — incompatible Windows | Makefile:7-10. Cambiar a `uv run` o deteccion de OS. `uv` maneja multiplataforma. |
| D2 | `Makefile` usa `find` y `pkill` — comandos Unix-only | Makefile:108-114,145. Reemplazar `find` con `Remove-Item` (PowerShell) o `Get-ChildItem`. `pkill` con `Stop-Process`. |
| D3 | `Makefile` no tiene targets `test-all`, `test-fast`, `coverage` segun plan | Plan D7.2 requiere estos 3 targets. Solo `test`, `test-verbose`, `test-cov` existen. |
| D4 | `fap phase-close` fue disenado para Fase V (details4agents) — resolve D1-D6 viejos | phase_close.py:94-218. Referencia `estado-fase.md` (no usado en Fase VI). No cubre cierre de Fase testing. Requiere actualizacion. |
| D5 | `fap test-step` no soporta paso 7 | test_step.py:23-42. Paso 7 no tiene test files. Tampoco pasos 4 y 6. |
| D6 | `pyproject.toml` sin config de coverage explicita | No hay `[tool.coverage.run]` ni thresholds configurados. `pytest-cov` instalado pero sin config. |
| D7 | `TESTING.md` no existe — documentacion de ejecucion ausente | Plan D7.1 requiere documentar comandos exactos por paso y estrategia de mocking. |
| D8 | `CHANGELOG` no existe — historial de mejoras ausente | Plan D7.5 requiere entry por cada paso. |
| D9 | `README.md` desactualizado — dice "Fase 1 — Motor Base" | README.md:5 — no refleja estado actual de Fase VI (testing) |
| D10 | `DEVS/IMPLEMENTED/testing/` sin carpeta `07-Documentacion-y-Cierre/` | Plan D7.4: `fap phase-close` debe archivar en `DEVS/IMPLEMENTED/certificacion/`. Plan dice `certificacion/`, no `testing/07-Documentacion-y-Cierre/`.

---

## 1 Analisis de Datos (ETAPA 1)

**Impacto:** Nulo. Paso 7 no crea/modifica tablas, migraciones, RLS, indices ni constraints.

- **Schema:** Sin cambios
- **Integridad referencial:** Sin impacto
- **RLS:** Sin cambios
- **Indices:** Sin cambios
- **Tipos de datos:** Sin impacto

**Conclusion:** DATA layer no afectado. Paso 7 es puramente documentacion + tooling.

---

## 2 Analisis de Codigo (ETAPA 2)

### Archivos a CREAR

| Archivo | Tipo | Descripcion |
|---|---|---|
| `TESTING.md` | Documentacion | Comandos exactos por paso, estrategia de mocking, CI execution |
| `CHANGELOG` | Documentacion | Registro de mejoras por paso desde Fase VI |
| `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/analisis-7-ds.md` | Archivo | Analisis actual |

### Archivos a MODIFICAR

| Archivo | Cambio | Riesgo |
|---|---|---|
| `Makefile` | Agregar targets `test-all`, `test-fast`, `coverage`. Fix rutas Windows (`.venv/bin/` → `uv run`). Fix `find`/`pkill` Windows-incompatibles. | **Medio** — Makefile actual funciona en WSL. Cambios multiplataforma no deben romper WSL. |
| `src/cli/commands/phase_close.py` | Actualizar para Fase VI (testing). Referencias a `estado-fase.md` → `phase-state.md`. Nuevas discrepancias D7-D10. | **Medio** — `phase_close` es critico para cierre de fase. Cambios deben mantener retrocompatibilidad. |
| `src/cli/commands/test_step.py` | Agregar paso 7 a STEP_TEST_FILES (aunque no tenga tests unitarios, tener entrada para cobertura) | **Bajo** — solo agregar entrada en diccionario |
| `pyproject.toml` | Agregar `[tool.coverage.run]` config, `[tool.coverage.report]` thresholds | **Bajo** — config adicional, no rompe nada |
| `phase-state.md` | Marcar pasos 0-7 como completados. Actualizar progreso a 8/8. | **Bajo** — documental |

### Archivos a GENERAR (automatico)

| Archivo | Comando | Descripcion |
|---|---|---|
| `htmlcov/index.html` | `pytest --cov=src --cov-report=html` | Reporte de cobertura HTML |
| `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/` | `fap phase-close` (archivado) | Carpeta de cierre |

### Patrones existentes

- **CLI commands:** `test_step.py` — estructura Typer con flags, `phase_close.py` — certificacion con reporte Rich
- **Makefile:** Usa variables `$(PYTEST)`, `$(UVICORN)`. Pattern `mock_service_client` y `time.time` mocking para testing
- **phase-state.md:** Formato markdown con tablas de progreso, checklist

### Cohesion y acoplamiento

- `TESTING.md` independiente — no tiene dependencias de codigo
- `CHANGELOG` independiente — solo registro historico
- Makefile targets dependen de: `uv sync` (instalacion), `pytest` (tests), `ruff` (lint)
- `phase_close.py` depende de: subprocess (lint, tests), IO en config/phase-state files
- Actualizacion `phase-state.md` es manual o via `fap phase-close --certify`

---

## 3 Analisis de Backend (ETAPA 3)

**Impacto:** Nulo. Paso 7 no crea/modifica endpoints, middleware, rutas ni contratos de API.

- **Endpoints:** Sin cambios
- **Middleware:** Sin cambios
- **Flujos:** Sin cambios
- **Contratos:** Sin cambios
- **Error handling:** Sin cambios

**Conclusion:** Backend layer no modificado. Paso 7 solo toca tooling CLI + docs + build config.

---

## 4 Analisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Developer
├── D7.1: lee TESTING.md → sabe comandos exactos por paso
├── D7.2: make test-all → ejecuta pasos 0-7 en orden
│   ├── make lint       → ruff check
│   ├── make test       → pytest tests/
│   ├── make test-fast  → pytest tests/ -x --no-header
│   ├── make test-cov   → pytest --cov=src --cov-report=html
│   └── make coverage   → pytest --cov=src --cov-report=term-missing
├── D7.3: pytest --cov=src --cov-report=html → htmlcov/index.html
│   └── Verificar cobertura global >75%
├── D7.4: fap phase-close testing --certify
│   ├── Corre lint + tests
│   ├── Resuelve discrepancias
│   ├── Actualiza phase-state.md + proyecto-config.json
│   └── Archiva en DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/
└── D7.5: CHANGELOG → entries por paso
```

### Coherencia

- **D7.1 (TESTING.md):** Documentacion necesaria para que cualquier dev pueda ejecutar cada paso sin leer el plan. Incluye estrategia de mocking (conftest.py, time.time patching).
- **D7.2 (Makefile):** Complementa `fap test-step` existente. `make test-all` unifica la suite completa. `make test-fast` para CI rapido.
- **D7.3 (Coverage):** Solo viable despues de pasos 0-6 implementados. `pytest-cov` ya instalado.
- **D7.4 (phase-close):** Integra todo. Sin las tareas D7.1-D7.3 completadas, `phase-close` produce certificacion incompleta.
- **D7.5 (CHANGELOG):** Registro historico. Sin las tareas D7.1-D7.4, entries serian incompletos.

### Gaps y ambiguedades

1. **Makefile targets vs fap CLI overlap:** Plan D7.2 pide `make test`, `make test-fast`, `make test-all`, `make lint`, `make coverage`. `fap test-step` y `fap phase-close` ya existe. Makefile y CLI son interfaces complementarias: Makefile para CI (simple), CLI para dev interactivo (detallado).

2. **`test-fast` sin definicion clara:** Plan no especifica que incluye. Interpretacion: solo tests unitarios (pasos 1-2), sin e2e, sin stress, sin benchmarks. `pytest tests/unit/ tests/integration/ -x --no-header -q`.

3. **Coverage threshold >75%:** Plan pide "Cobertura global >75%". Sin ejecutar `pytest --cov=src` en la suite completa no se sabe si se cumple. Depende de cuantos tests de pasos 0-6 se implementaron realmente.

4. **`fap phase-close` actualizacion:** Comando existente hardcodeado para Fase V. Para Fase VI necesita:
   - Referenciar `phase-state.md` en vez de `estado-fase.md`
   - Nuevas discrepancias D7-D10
   - Archivar en `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/`
   - `fap phase-close testing --certify`

5. **README.md desactualizado:** Dice "Fase 1 — Motor Base". Deberia reflejar Fase VI — Testing. No es critico para certificacion pero afecta DX.

### DX & Tooling — Propuesta Obligatoria

```
### Herramienta Propuesta: `make test-all` + `fap final-report`
- **Que automatiza:** Ejecucion completa de certificacion (pasos 0-7) con reporte unificado.
  `make test-all` es interfaz simple para CI. `fap final-report` genera reporte de certificacion final.
- **Tipo:** Makefile target + CLI comando
- **Como se usa:**
  ```bash
  make test-all                    # CI: ejecuta toda la suite en orden
  make test-fast                   # Dev rapido: solo unit + integration
  make coverage                    # Reporte de cobertura completo
  fap final-report --output reporte-certificacion.md  # Reporte final
  ```
- **Que automatiza:**
  - `make test-all`: lint → unit tests → integration tests → e2e → stress → security → performance → cobertura
  - `fap final-report`: consolida resultados de todos los pasos, genera markdown estructurado con pass/fail por paso
- **Impacto para el usuario final:**
  - No necesita leer el plan para saber como correr tests
  - CI puede ejecutar `make test-all` y saber si todo pasa
  - Dev puede ejecutar `make test-fast` para feedback rapido
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5 Criterios de Aceptacion

```
[DOC] D7.1: TESTING.md existe en raiz con comandos exactos por paso (0-7) y estrategia de mocking
[DOC] D7.1: TESTING.md documenta fixtures conftest.py, time.time patching, MCPPool.reset()
[DOC] D7.2: Makefile target `test` ejecuta pytest tests/
[DOC] D7.2: Makefile target `test-all` ejecuta pasos 0-6 en orden
[DOC] D7.2: Makefile target `test-fast` ejecuta solo test unitarios + integracion
[DOC] D7.2: Makefile target `lint` ejecuta ruff check
[DOC] D7.2: Makefile target `coverage` ejecuta pytest --cov=src --cov-report=html
[DOC] D7.2: Makefile compatible Windows (usa uv run, no find/pkill)
[DOC] D7.3: pytest --cov=src --cov-report=html genera reporte en htmlcov/index.html
[DOC] D7.3: Cobertura global >75%
[DX] D7.4: fap phase-close testing --certify ejecuta y pasa (lint + tests + discrepancias + archivado)
[DX] D7.4: fap final-report genera reporte markdown de certificacion
[DOC] D7.5: CHANGELOG existe con entries por paso desde Fase VI
[DOC] phase-state.md actualizado: 8/8 pasos completados, fase marcada como CERRADA
[DOC] proyecto-config.json actualizado: phase.current_step = "07-Documentacion-y-Cierre"
```

---

## 6 Riesgos

| Riesgo | Severidad | Causa | Mitigacion |
|---|---|---|---|
| R1: Cobertura <75% tras suite completa | **Alta** | Pasos 0-6 pueden no cubrir suficiente codigo. Plan dice ">75%" pero no hay medicion previa. | Ejecutar `pytest --cov=src` TEMPRANO para medir. Si <75%, priorizar tests que cubran gaps. |
| R2: Makefile no-portable rompe CI en Windows | **Media** | Makefile actual usa `.venv/bin/python`, `find`, `pkill`. CI runner Windows fallaria. | Usar `uv run` (multiplataforma). Reemplazar `find` con comandos PowerShell. Documentar WSL como alternativa. |
| R3: `fap phase-close` modificaciones rompen compatibilidad | **Media** | `phase_close.py` disenado para Fase V. Cambios para Fase VI pueden romper dry-run o --certify para fases anteriores. | Mantener backward compat. Parametro `phase` ya existe. Solo agregar logica condicional para "testing" phase. |
| R4: CHANGELOG sin entries de pasos 0-6 | **Baja** | Nadie documento entries retroactivos. CHANGELOLG quedaria vacio o solo con paso 7. | Revisar git log para extraer entries de commits existentes. Potencialmente tedioso pero necesario. |
| R5: `TESTING.md` se desincroniza con cambios futuros | **Media** | Documentacion estatica. Si se agregan tests, TESTING.md queda desactualizado. | Incluir en CI: CI verifica que comandos de TESTING.md son ejecutables (smoke test). |
| R6: README.md desactualizado confunde nuevos devs | **Baja** | Dice "Fase 1 — Motor Base". Nuevo developer piensa que proyecto esta en fase inicial. | Actualizar README.md como parte de D7.1. Cambio minimo pero alto impacto en DX. |
| R7: `pytest --cov=src` puede fallar si hay dependencias opcionales (crewai) no instaladas | **Media** | `pyproject.toml` crewai es opcional. Tests que importan crew fallarian si no esta instalado. | Verificar que `uv sync --all-extras` instala crewai. O marcar tests crewai con `@pytest.mark.skipif`. |

---

## 7 Plan de Implementacion

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificacion |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Makefile targets + `fap final-report` | FULLSTACK/DX | Media | 2h | Ninguna | verificar: `make test-all` ejecuta todos los pasos; `make test-fast` pasa en <30s; `fap final-report` genera markdown |
| 1 | Crear `TESTING.md` con documentacion completa | FULLSTACK/DOC | Media | 2h | Tarea 0 | verificar: README.md referencia TESTING.md; comandos en TESTING.md son ejecutables uno por uno |
| 2 | Fix Makefile: targets faltantes + compatibilidad Windows | CODE | Media | 1.5h | Tarea 0 | verificar: `make test`, `make test-all`, `make test-fast`, `make lint`, `make coverage` funcionan en Windows y WSL |
| 3 | Generar reporte cobertura (`pytest --cov=src --cov-report=html`) | CODE | Baja | 0.5h | Pasos 0-6 implementados | verificar: htmlcov/index.html existe; cobertura global >75% |
| 4 | Actualizar `fap phase-close` para Fase VI (testing) | CODE | Media | 2h | Tareas 0-3 | verificar: `fap phase-close testing --dry-run` muestra cambios correctos; `fap phase-close testing --certify` pasa |
| 5 | Crear `CHANGELOG` con entries de Fase VI | DOC | Baja | 1h | Git log (pasos 0-6 commits) | verificar: CHANGELOG tiene entrada por paso (0-7) con commit hash y resumen |
| 6 | Actualizar `phase-state.md` + `proyecto-config.json` | DOC | Baja | 0.5h | Tareas 0-5 | verificar: phase-state.md marca 8/8 pasos, CERRADA; config.json phase.current_step actualizado |
| 7 | Update `test_step.py` — agregar paso 7 placeholder | CODE | Baja | 0.3h | Tarea 0 | verificar: `fap test-step 7` no da error "Paso '7' no definido" |
| 8 | Validacion final end-to-end | FULLSTACK | Baja | 1h | Tareas 0-7 | verificar: criterios 5 pasan todos; `fap phase-close --certify` reporta PASS |

### Detalles de implementacion por tarea

**Tarea 0 — Makefile targets:**

```makefile
# ── Testing targets ─────────────────────────────────────────────
.PHONY: test test-fast test-all coverage

test-all: lint test test-cov
	@echo "Completado: lint → test → coverage"

test-fast:
	@$(PYTEST) tests/unit/ tests/integration/ -x -q --no-header

coverage:
	@$(PYTEST) tests/ --cov=src --cov-report=term-missing --cov-report=html -q --no-header
	@echo "Cobertura global >75% requerida. Revisar htmlcov/index.html"
```

Fix compatibilidad Windows:
- Reemplazar `.venv/bin/python` → `uv run python` o `python`
- Reemplazar `find . -type d -name "__pycache__" -exec rm -rf {} +` → `Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse`
- Reemplazar `pkill -f "uvicorn"` → `Get-Process | Where-Object { $_.CommandLine -match "uvicorn" } | Stop-Process`

**Tarea 1 — TESTING.md estructura:**

```markdown
# Testing Guide — FluxAgentPro-v2

## Suite Actual
~455 tests (unit + integration + e2e + stress)

## Comandos por Paso

| Paso | Comando | Archivos |
|------|---------|----------|
| 0 (Baseline) | `fap baseline-check` | tests/conftest.py |
| 1 (Unitarios) | `fap test-step 1` | tests/unit/test_mcp_pool_circuit.py, test_service_connector.py, test_approval_operators.py, test_sanitizer.py |
| 2 (Integracion) | `fap test-step 2` | tests/integration/test_mcp_resilience.py, test_handover_real.py |
| 3 (E2E) | `fap test-step 3` | tests/e2e/test_production_flows.py |
| 4 (Stress) | `fap stress-bench` | tests/stress/test_concurrency.py, test_edge_cases.py |
| 5 (Seguridad) | `fap test-step 5` | tests/unit/test_security_guard.py, test_security_guard_escape.py |
| 6 (Performance) | `fap perf-check` | tests/stress/test_performance.py |
| 7 (Cierre) | `make test-all` | Suite completa |

## Estrategia de Mocking
- **MCPPool:** `unittest.mock.patch("time.time")` por test. `MCPPool.reset()` en fixture `autouse=True`.
- **ServiceConnector:** `patch("httpx.Client")` para HTTP. `mock_service_client` para DB. `patch("src.tools.service_connector.get_secret")` para Vault.
- **Approval:** `DynamicWorkflow(org_id=...)` instancia directa. Metodo sincrono puro.
- **Sanitizer:** `sanitize_output()` import directo. Funcion pura sin IO.
- **SecurityGuard:** Codigo malicioso en strings. RestrictedPython sandbox.
- **Benchmarks:** `time.perf_counter_ns()` sin pytest-benchmark.
```

**Tarea 4 — phase_close.py actualizacion:**

Claves del cambio:
- Detectar `phase == "testing"` y usar logica diferente
- Referenciar `phase-state.md` en vez de `estado-fase.md` 
- Discrepancias: D7-D10 en vez de D1-D6
- Archivar en `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/`

Logica condicional:
```python
if phase == "testing":
    # Usar phase-state.md
    # Resolver D7-D10 (Makefile, TESTING.md, CHANGELOG, coverage)
    # Archivar en DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/
else:
    # Logica existente para Fase V (details4agents)
    # Resolver D1-D6
```

**Tarea 5 — CHANGELOG entries desde git log:**

Extraer commits de fase testing:
```
git log --oneline --since="2026-05-01" --until="2026-05-02"
```

Formato:
```markdown
# Changelog

## Fase VI — Testing (2026-05-01)

### Paso 7: Documentacion y Cierre
- [commit] TESTING.md, Makefile, coverage report, CHANGELOG creados
- [commit] phase-close actualizado para Fase VI
- [commit] phase-state.md marcado como completado

### Paso 6: Performance & Observabilidad
- [commit] 4 benchmarks (P6.1-P6.4) en tests/stress/test_performance.py
- [commit] `fap perf-check` CLI command
```

### Tiempo total estimado: **10.3 horas**

---

## Roadmap

### Issues descubiertas durante analisis que afectan pasos futuros

1. **Makefile no-portable:** `find`, `pkill`, `.venv/bin/*` paths. En Windows nativo (no WSL), Makefile falla. Mitigacion: usar `uv run` que es multiplataforma. Pero `uv` no maneja `find`/`pkill`. Solucion real: migrar a `nox` o `taskipy` que son nativamente multiplataforma. Sugerir para post-certificacion.

2. **README.md desactualizado:** Dice "Fase 1 — Motor Base". Confunde a nuevos desarrolladores. Actualizar como parte de D7.1 es trivial pero alto impacto.

3. **Sin metricas de cobertura previas:** Threshold >75% no verificado. Riesgo R1. Recomendacion: ejecutar `pytest --cov=src` ANTES de cerrar paso 7 para saber si se cumple. Si no, expandir tests existentes o ajustar threshold.

4. **`test_step.py` no cubre todos los pasos:** Pasos 4, 6, 7 no estan en STEP_TEST_FILES. Esto significa que `fap test-step 4`, `fap test-step 6`, `fap test-step 7` fallan. Agregar en Tarea 7.

### Decisiones de diseno

- **`make` vs `fap` CLI:** `make` para CI (simple, universal). `fap` para dev interactivo (detallado, colores, reportes). Ambos coexisten. `make test-all` llama a `fap test-step` internamente O ejecuta pytest directamente — decision del implementador. Recomendacion: make llama directamente a pytest para evitar dependencia circular.
- **TESTING.md vs README.md:** `README.md` es landing page del proyecto. `TESTING.md` es guia especifica de testing. README debe referenciar TESTING.md, no duplicar contenido.
- **CHANGELOG en raiz:** Convencion estandar de proyectos open source. Formato Keep a Changelog.
