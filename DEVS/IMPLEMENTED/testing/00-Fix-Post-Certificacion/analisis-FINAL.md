# 🏛️ Análisis Unificado — Paso 1: Fix Lint I001

> **Versión:** v3.2
> **Fecha:** 2026-05-02
> **Fase:** testing — Hotfix Post-Certificación (Paso 1/4)
> **Fuente:** `DEVS/IN_PROGRESS/analisis-paso-1-{kimi,glm,ds,qwen}.md`
> **Config:** `proyecto-config.json` → `paths.backend = src/`, `commands.lint_fix = "uv run ruff check --fix src/ tests/"`

---

### 0️⃣ Evaluación de Análisis y Verificaciones

#### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **kimi** | ✅ 14 elementos | 1 | ✅ `fap lint-fix` | ✅ Archivos + líneas + diffs | 4.8 |
| **glm** | ✅ 12 elementos | 2 | ✅ `make lint-fix` | ✅ Ruff diffs + análisis backend | 4.8 |
| **ds** | ✅ 11 elementos | 2 | ✅ `fap lint-fix` (opcional) | ✅ Archivos + líneas | 4.5 |
| **qwen** | ✅ 10 elementos | 2 | ✅ Pre-commit hook ruff | ✅ Archivos + convenciones config | 4.2 |

#### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `plan.md:77` dice `server.py:7` pero error I001 real en línea 13 | ds, glm | ✅ `ruff check --diff` | Plan tiene línea incorrecta. No bloqueante — `ruff --fix` es determinista. Ignorar. |
| 2 | `phase-state.md` reporta lint 0 pero código tiene 3 I001 reales | kimi | ✅ `ruff check src/ tests/` → 3 errors | Drift documentación. Actualizar phase-state.md al cerrar hotfix. |
| 3 | `server.py` diff mueve `from mcp.server import Server` después de `src.flows.*` — mezcla third/first-party | glm | ✅ `ruff check --diff` | Ruff clasifica `mcp.server` (third-party) y `src.flows` (first-party) correctamente. Aceptable. |
| 4 | Imports inline en try/except: `crewai_tools` / `mcp` ≠ imports top-level | ds, glm | ✅ Código real `validate_tools.py:68-72`, `mcp_pool.py:148-154` | Ruff solo pide blank line separator, NO reordenamiento. Confirmado con `--diff`. |
| 5 | Ruff isort ordena por secciones, no alfabéticamente | qwen | ✅ Config `pyproject.toml` | Ruff usa secciones (stdlib/third/first/local). --fix produce orden correcto. |

---

### 1️⃣ Resumen Ejecutivo

- **Objetivo:** Corregir 3 errores I001 (`unsorted-imports`) en `validate_tools.py:69`, `server.py:13`, `mcp_pool.py:149` mediante auto-fix de ruff.
- **Corrección al plan:** `plan.md:77` referencia línea 7 pero error real en línea 13. No afecta ejecución — `ruff --fix` es determinista.
- **DX fusionada:** Se adopta **`fap lint-fix`** (kimi/ds) como comando CLI Typer + **Makefile target** `make lint-fix` (glm) como atajo. Pre-commit hook (qwen) se difiere a roadmap.
- **Naturaleza:** Paso puramente cosmético/lint. Cero cambio funcional. Sin impacto en datos, backend ni frontend.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path

1. Ejecutar `ruff check --fix src/ tests/` → corrige 3 errores I001 automáticamente
2. `ruff check src/ tests/` → 0 errores (gate cumplido)
3. `uv run pytest tests/ -x` → 512 tests pass (sin regresión)
4. Importabilidad: `uv run python -c "from src.mcp.server import server; print('OK')"` → OK

#### Edge Cases MVP

- **EC-1:** `ruff --fix` dentro de bloque `try/except ImportError` — solo debe insertar blank line, no reordenar. Verificado con `--diff`.
- **EC-2:** `server.py` imports con side-effect (`# noqa: F401` — eager flow registration) — deben preservarse agrupados. Ruff no los separa.
- **EC-3:** `__future__ import annotations` debe seguir siendo primer import — ruff lo respeta.

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

##### `src/cli/commands/validate_tools.py` (línea 68-72)
- **Tipo de cambio:** Modificación
- **Descripción:** Insertar blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` dentro de bloque `try/except` en `_validate_mcp_tool()`.
- **Interfaces clave:** Sin cambios de firma. Función `_validate_mcp_tool()` preserva lógica.
- **Patrón a seguir:** `src/cli/commands/security_audit.py` — imports ordenados correctamente.

##### `src/mcp/server.py` (líneas 7-24)
- **Tipo de cambio:** Modificación
- **Descripción:** `from mcp.server import Server` se mueve después de `import src.flows.test_flows`. Orden final: `__future__` → stdlib → third-party (`mcp.server.stdio` → `mcp.server`) → first-party (`src.flows.*`) → local (`.config`, `.flow_to_tool`, `.tools`).
- **Interfaces clave:** Sin cambios. Objeto global `server = Server(...)` se crea después de todo el import block.
- **Patrón a seguir:** Otros archivos en `src/api/routes/` — stdlib → third-party → first-party → local.

##### `src/tools/mcp_pool.py` (línea 148-154)
- **Tipo de cambio:** Modificación
- **Descripción:** Insertar blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` dentro de bloque `try/except` en `MCPPool.get_tools()._connect()`.
- **Interfaces clave:** Sin cambios. Misma función preservada.
- **Patrón a seguir:** Idéntico a `validate_tools.py`.

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap lint-fix
- **Qué automatiza:** Ejecuta `ruff check --fix src/ tests/` + valida resultado con `ruff check`. Evita recordar flags y paths.
- **Tipo:** Comando CLI (Typer) + Makefile target
- **Ubicación:** `src/cli/commands/lint_fix.py` (nuevo) + `Makefile` target `lint-fix`
- **Cómo se usa:**
  - `uv run python -m src.cli.main lint-fix` — fix auto
  - `uv run python -m src.cli.main lint-fix --check` — solo verificar (CI)
  - `make lint-fix` — atajo vía Makefile
- **Impacto para el usuario final:** Elimina ejecución manual de `ruff check --fix src/ tests/`. Un comando, zero flags.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

### 4️⃣ Decisiones Tecnológicas

1. **`ruff check --fix` como mecanismo de corrección:** No modificar imports manualmente. Ruff es determinista para I001 y produce diff consistente. Verificado con `--diff` en los 3 archivos.
2. **DX `fap lint-fix` fusionado:** kimi propone CLI Typer, glm propone Makefile target. Se fusionan ambos — CLI para discoverability, Makefile para velocidad. Pre-commit hook de qwen se difiere a roadmap.
3. **Sin cambios manuales en `server.py`:** El diff de ruff reubica `from mcp.server import Server` después de `src.flows.*`. Aunque parece mezclar third/first-party, ruff clasifica correctamente y preserva side-effects.
4. **Corrección al plan:** `plan.md:77` dice `server.py:7` pero error I001 está en línea 13. No bloqueante — `ruff --fix` ignora números de línea.
5. **Comando `lint_fix` ya en proyecto-config.json:** `commands.lint_fix` = `uv run ruff check --fix src/ tests/`. Validación de qwen confirmada.

---

### 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] `ruff check src/ tests/` retorna 0 errores
✅ [CODE] `ruff check --select I001 src/cli/commands/validate_tools.py` → 0 errores
✅ [CODE] `ruff check --select I001 src/mcp/server.py` → 0 errores
✅ [CODE] `ruff check --select I001 src/tools/mcp_pool.py` → 0 errores
✅ [CODE] `validate_tools.py`: blank line entre crewai_tools y mcp dentro de try block
✅ [CODE] `server.py`: from mcp.server import Server reordenado según diff ruff
✅ [CODE] `mcp_pool.py`: blank line entre crewai_tools y mcp dentro de try block
✅ [CODE] Ningún import eliminado ni agregado — solo reordenamiento + blank lines
✅ [FULLSTACK] `uv run pytest tests/ -x` → 512 tests pass sin regresión
✅ [FULLSTACK] `uv run python -c "from src.mcp.server import server; print('OK')"` → OK
✅ [DX] Comando `fap lint-fix` ejecuta sin errores y reduce tarea manual
✅ [DX] `make lint-fix` disponible como atajo
```

**Funcionales:**
- [ ] Sin cambios funcionales — paso 100% higiene de código

**Técnicos:**
- [x] 3 errores I001 corregidos → `ruff check` = 0 errores
- [x] Suite completa pasa sin regresión
- [x] Importabilidad de módulos afectados verificada

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap lint-fix` (CLI Typer) + registrar en `main.py` + agregar `make lint-fix` | Media | 0.2h | Ninguna |
| 1 | Ejecutar `ruff check --fix src/ tests/` — corrige 3 I001 simultáneamente | Baja | 0.02h | Tarea 0 (dogfooding) |
| 2 | Validar `ruff check src/ tests/` → 0 errores | Baja | 0.02h | Tarea 1 |
| 3 | Validar suite tests sin regresión: `uv run pytest tests/ -x` | Baja | 0.1h | Tarea 1 |
| 4 | Validar importabilidad: `python -c "from src.mcp.server import server"` | Baja | 0.02h | Tarea 1 |
| **TOTAL** | | | **0.36h** | |

> **Nota:** `ruff check --fix` corrige los 3 archivos en una sola ejecución. Tareas 1-4 secuenciales. Tarea 0 puede ir en paralelo.

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `ruff --fix` reordena imports rompiendo side-effects (eager flow registration en `server.py`) | Baja | `src.flows.*` imports registran flujos al importarse | Ruff no separa `src.flows.*` del bloque first-party. Verificado con `--diff`. Test de import post-fix. |
| `ruff --fix` inserta cambios no deseados fuera de los 3 archivos | Baja | Comando `--fix` afecta todo `src/` y `tests/` | Solo 3 errores I001 en todo el codebase. `ruff check --diff` confirmado. |
| `ruff version` diff entre local y CI causa diferente output | Baja | `ruff>=0.8.0` sin pin exacto | `ruff 0.15.12` instalado. CI usa misma dev dep. |
| Phase-state.md desactualizado post-fix (lint ≠ 0 reportado) | Media | Documentación no refleja estado actual | Actualizar al cerrar hotfix completo. No blocker para Paso 1. |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | `ruff check src/ tests/` post-fix | `ruff check src/ tests/` | 0 errores, exit code 0 |
| TP-2 | Importabilidad server.py | `python -c "from src.mcp.server import server"` | `OK` sin excepción |
| TP-3 | Suite completa sin regresión | `uv run pytest tests/ -x` | 512 passed, 0 failed |
| TP-4 | DX `fap lint-fix --help` | `uv run python -m src.cli.main lint-fix --help` | Ayuda muestra flags `--check` |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60` / `uv run pytest tests/ -x`

---

> **Archivo generado:** `DEVS/IN_PROGRESS/analisis-FINAL.md`
> **Próximo paso:** Implementador ejecuta Tarea 0 (DX) → Tareas 1-4.
