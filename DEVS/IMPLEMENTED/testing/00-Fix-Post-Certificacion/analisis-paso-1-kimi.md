# Análisis Técnico — Paso 1: Fix Lint I001

> **Agente:** kimi  
> **Paso:** 1 (Fix Lint I001)  
> **Fecha:** 2026-05-02  
> **Destino:** `DEVS/IN_PROGRESS/analisis-paso-1-kimi.md`

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/commands/validate_tools.py` existe | `ls src/cli/commands/` | ✅ | archivo presente, 220 líneas |
| 2 | `src/mcp/server.py` existe | `ls src/mcp/` | ✅ | archivo presente, 89 líneas |
| 3 | `src/tools/mcp_pool.py` existe | `ls src/tools/` | ✅ | archivo presente, 212 líneas |
| 4 | Error I001 en `validate_tools.py:69` | `ruff check src/ tests/` | ✅ | bloque `from crewai_tools` / `from mcp` desordenado |
| 5 | Error I001 en `server.py:7` | `ruff check src/ tests/` | ✅ | bloque import global desordenado (`mcp.server` vs `src.flows`) |
| 6 | Error I001 en `mcp_pool.py:149` | `ruff check src/ tests/` | ✅ | bloque `from crewai_tools` / `from mcp` desordenado |
| 7 | Exactamente 3 errores I001, ningún otro lint error | `ruff check src/ tests/` | ✅ | output: "Found 3 errors. [*] 3 fixable" |
| 8 | Los 3 errores son auto-fixables | `ruff check --diff` | ✅ | diff generado para los 3 archivos sin conflictos |
| 9 | `pyproject.toml` configura ruff con `select = ["E", "F", "I", "B"]` | `cat pyproject.toml:96-98` | ✅ | I (isort) activo |
| 10 | `pyproject.toml` `target-version = "py312"` | `cat pyproject.toml:94` | ✅ | coherente con stack |
| 11 | `pyproject.toml` `line-length = 88` | `cat pyproject.toml:93` | ✅ | coherente con formateo actual |
| 12 | `src/cli/main.py` importa `baseline_check` desde `src.cli.baseline` | `cat src/cli/main.py:14` | ✅ | Pendiente de alineación con Paso 4 (move) |
| 13 | `src/cli/commands/` es directorio de comandos CLI | `ls src/cli/commands/` | ✅ | 16 archivos `.py` |
| 14 | No existe comando CLI `lint` ni `lint-fix` | `grep -r "app.command.*lint" src/cli/` | ✅ | ningún match |

**Discrepancias encontradas:**

1. **Phase-state.md asume lint 0 global** — línea 88 indica "Lint 0 errores (`ruff check src/ tests/`)". Código actual tiene 3 errores I001.  
   **Resolución:** Ejecutar `ruff check --fix` en este paso. Actualizar phase-state.md en cierre del hotfix.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Estado:** No aplica. Este paso no modifica schema, tablas, columnas, RLS ni índices.

- ❌ Ninguna tabla tocada.
- ❌ Ninguna migración requerida.
- ❌ Ningún tipo de dato afectado.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos modificados

#### `src/cli/commands/validate_tools.py`

- **Funciones/clases:** Sin cambios de firma. `validate_tools_command`, `_validate_single_tool`, `_validate_bundle_tools`, `_validate_agent_tools`, `_validate_mcp_tool`, `_validate_regular_tool`, `_parse_mcp_prefix`, `_print_results` permanecen iguales.
- **Cambio de imports (línea 68-70):**
  ```python
  # ANTES (I001):
      from crewai_tools import MCPServerAdapter
      from mcp import StdioServerParameters
  # DESPUÉS (fix ruff):
      from crewai_tools import MCPServerAdapter

      from mcp import StdioServerParameters
  ```
  Ruff inserta línea en blanco entre imports de paquetes distintos (`crewai_tools` vs `mcp`) para cumplir agrupación por secciones (stdlib / third-party / first-party / local).
- **Patrón existente:** `src/tools/mcp_pool.py:149` y otros archivos con imports condicionales de `crewai_tools` + `mcp` muestran mismo patrón desordenado.

#### `src/mcp/server.py`

- **Funciones/clases:** Sin cambios. `main()`, `handle_list_tools()`, `handle_call_tool()` permanecen iguales.
- **Cambio de imports (línea 7-24):**
  ```python
  # ANTES (I001):
  from __future__ import annotations

  import argparse
  import asyncio
  import logging

  from mcp.server import Server
  from mcp.server.stdio import stdio_server

  import src.flows.architect_flow  # noqa: F401
  import src.flows.generic_flow  # noqa: F401
  import src.flows.test_flows  # noqa: F401

  from .config import MCPConfig
  # DESPUÉS (fix ruff):
  from __future__ import annotations

  import argparse
  import asyncio
  import logging

  from mcp.server.stdio import stdio_server

  import src.flows.architect_flow  # noqa: F401
  import src.flows.generic_flow  # noqa: F401
  import src.flows.test_flows  # noqa: F401
  from mcp.server import Server

  from .config import MCPConfig
  ```
  Ruff reordena: `mcp.server.stdio` (third-party) va antes de imports `src.flows.*` (first-party). `mcp.server import Server` se mueve después de los imports `src.flows.*` porque ruff clasifica `src.flows` como first-party y `mcp.server` como third-party, requiriendo orden: stdlib → third-party → first-party → local.
- **Patrón de referencia:** Archivos sin errores I001 en `src/api/routes/` mantienen orden: `from fastapi ...` → `from src...` → `from . ...`.

#### `src/tools/mcp_pool.py`

- **Funciones/clases:** Sin cambios. `MCPPool.get_tools()`, `_is_circuit_open()`, `_record_failure()`, `_reset_circuit_breaker()`, `_safe_close()`, `close()`, `reset()` permanecen iguales.
- **Cambio de imports (línea 148-150):**
  ```python
  # ANTES (I001):
              from crewai_tools import MCPServerAdapter
              from mcp import StdioServerParameters
  # DESPUÉS (fix ruff):
              from crewai_tools import MCPServerAdapter

              from mcp import StdioServerParameters
  ```
  Igual que `validate_tools.py`: línea en blanco entre imports de paquetes distintos.
- **Patrón de referencia:** Mismo patrón que `validate_tools.py` — fix idéntico.

### Modularidad y calidad

- **Cohesión:** Alta. Cada archivo mantiene responsabilidad única; solo cambia orden de imports.
- **Acoplamiento:** Sin cambios. Ninguna firma de función ni dependencia lógica alterada.
- **Duplicación:** No introduce duplicación. Reutiliza patrón de fix automático de ruff.
- **Mantenibilidad:** Mejora legibilidad de bloques de import y consistencia con resto del codebase.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Estado:** No aplica. Este paso no crea ni modifica endpoints, middleware, contratos entre servicios ni flujos de datos backend → frontend.

- ❌ Ningún endpoint nuevo o modificado.
- ❌ Ningún middleware afectado.
- ❌ Ningún contrato de servicio alterado.
- ❌ Error handling sin cambios.

**Nota:** Los imports condicionales (`try/except ImportError`) en `validate_tools.py` y `mcp_pool.py` se preservan exactamente; ruff solo reordena dentro del bloque, no altera semántica de fallback.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

No hay flujo funcional nuevo. Este paso es puramente de higiene de código. El impacto en UX es indirecto: codebase consistente → menos fricción en reviews → velocidad de desarrollo mayor.

### Gaps / Fricción

- El desarrollador debe recordar ejecutar `ruff check --fix` manualmente antes de commitear. No hay automatización CI/local que lo impida.
- Phase-state.md reporta lint 0 pero código actual no lo tiene → riesgo de drift documentado vs real.

### DX & Tooling (OBLIGATORIO)

```markdown
### Herramienta Propuesta: `fap lint-fix`
- **Qué automatiza:** Ejecución de `ruff check --fix` sobre `src/` y `tests/` sin que el desarrollador recuerde paths ni flags. Evita errores I001 (y otros auto-fixables) en CI.
- **Tipo:** Comando CLI (`fap lint-fix`)
- **Cómo se usa:**
  ```bash
  uv run python -m src.cli.main lint-fix        # fix auto
  uv run python -m src.cli.main lint-fix --check  # solo check, sin fix (para CI)
  ```
- **Impacto para el usuario final:** Desarrollador deja de ejecutar `ruff check --fix src/ tests/` manualmente. Comando unificado con resto de DX (`fap security-audit`, `fap perf-check`). Reduce errores de CI por lint.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso. Usar `fap lint-fix` para ejecutar el fix de los 3 archivos.
```

**Patrón a seguir:** `src/cli/commands/security_audit.py` — comando Typer con flags, logging estructurado con `structlog`, exit codes (`0` éxito, `1` errores).

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Ninguna tabla ni migración afectada — N/A verificado
✅ [CODE] `validate_tools.py` sin errores I001 (`ruff check src/cli/commands/validate_tools.py` → 0)
✅ [CODE] `server.py` sin errores I001 (`ruff check src/mcp/server.py` → 0)
✅ [CODE] `mcp_pool.py` sin errores I001 (`ruff check src/tools/mcp_pool.py` → 0)
✅ [BACKEND] Ningún endpoint ni middleware afectado — N/A verificado
✅ [FULLSTACK] Flujo funcional sin cambios — N/A verificado
✅ [DX] Comando `fap lint-fix` ejecuta sin errores y muestra ayuda (`--help`)
✅ [LINT] `ruff check src/ tests/` global retorna 0 errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `ruff --fix` reordena imports de forma que rompe dependencia de inicialización en `server.py` (eager flow registration) | Baja | `src.flows.*` imports tienen side-effect de registro; ruff los mantiene en bloque first-party | Verificar diff antes de commit; diff de ruff no mueve `src.flows.*` respecto a `from mcp.server import Server`, solo separa secciones. Test de import: `python -c "from src.mcp.server import server"` |
| Fix I001 oculta regresión de otros errores (E, F, B) no detectados previamente | Baja | `ruff check` actual solo reporta I001; si hay E/F/B silenciados por cache o entorno, fix no los introduce | Ejecutar `ruff check src/ tests/` post-fix; confirmar 0 errores de todas las categorías |
| Phase-state.md desactualizado (lint 0) genera confusión en auditoría | Media | Documentación no refleja estado real del repo post-hotfix | Actualizar phase-state.md al finalizar hotfix completo (Pasos 0-4) |

---

## 7️⃣ Plan de Implementación

> **Tiempo total estimado:** 0.35h

| # | Tarea | Artefacto | Interfaz exacta / Cambio exacto | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap lint-fix` | `src/cli/commands/lint_fix.py` | `def lint_fix_command(check_only: bool = typer.Option(False, "--check", help="Solo verificar, no fixear")) -> None` | `src/cli/commands/security_audit.py` | DX | Baja | 0.15h | Ninguna | → verificar: `uv run python -m src.cli.main lint-fix --help` ejecuta sin errores |
| 1 | Registrar comando `lint-fix` en CLI | `src/cli/main.py` | Añadir `from src.cli.commands.lint_fix import lint_fix_command` y `app.command("lint-fix")(lint_fix_command)` | Línea 53 `app.command("test-step")(test_step)` | DX | Baja | 0.05h | Tarea 0 | → verificar: `uv run python -m src.cli.main lint-fix --help` muestra ayuda |
| 2 | Fix imports `validate_tools.py` | `src/cli/commands/validate_tools.py` | Insertar línea en blanco entre `from crewai_tools ...` y `from mcp ...` (línea 69-70) | Diff de `ruff check --diff` para este archivo | CODE | Baja | 0.02h | Tarea 1 | → verificar: `ruff check src/cli/commands/validate_tools.py` → 0 errores |
| 3 | Fix imports `server.py` | `src/mcp/server.py` | Reordenar imports según diff ruff: `mcp.server.stdio` antes de `src.flows.*`; `from mcp.server import Server` después de `src.flows.*` (líneas 7-24) | Diff de `ruff check --diff` para este archivo | CODE | Baja | 0.02h | Tarea 1 | → verificar: `ruff check src/mcp/server.py` → 0 errores |
| 4 | Fix imports `mcp_pool.py` | `src/tools/mcp_pool.py` | Insertar línea en blanco entre `from crewai_tools ...` y `from mcp ...` (línea 149-150) | Diff de `ruff check --diff` para este archivo | CODE | Baja | 0.02h | Tarea 1 | → verificar: `ruff check src/tools/mcp_pool.py` → 0 errores |
| 5 | Validar lint global | — | — | — | FULLSTACK | Baja | 0.05h | Tareas 2-4 | → verificar: `ruff check src/ tests/` → 0 errores totales |
| 6 | Test import `server.py` sin regresión | — | — | — | FULLSTACK | Baja | 0.04h | Tarea 3 | → verificar: `uv run python -c "from src.mcp.server import server; print('OK')"` → OK |

> [!IMPORTANT]
> **Ejecución sugerida:** Tarea 0 → 1 → (2,3,4 en paralelo) → 5 → 6.

---

## 🔮 Roadmap (NO implementar ahora)

- **Pre-commit hook:** Configurar `ruff` como pre-commit hook (vía `.pre-commit-config.yaml`) para evitar drift de lint en futuros commits.
- **CI gate:** Añadir `ruff check src/ tests/` como paso obligatorio en pipeline de CI antes de merge.
- **Fase VII:** Evaluar si `ruff format` (en lugar de solo `check`) se integra en `fap lint-fix` para unificar formateo + lint en un solo comando DX.

---

## 🚫 Cumplimiento de Reglas de Oro

- ✅ Análisis basado en código fuente real (14 elementos verificados).
- ✅ Discrepancia detectada: phase-state.md lint 0 vs 3 errores I001 reales.
- ✅ 4 etapas secuenciales cubiertas (data N/A documentado, code, backend N/A documentado, fullstack+DX).
- ✅ ≥ 1 herramienta DX propuesta (`fap lint-fix`).
- ✅ Tareas atómicas: una tarea = un artefacto (archivo o comando).
- ✅ Interfaz exacta / cambio exacto por tarea (diff ruff como especificación).
- ✅ Patrón de referencia explícito (`security_audit.py` para CLI, diff ruff por archivo).
- ✅ Verificación inline por tarea (comando concreto).
- ✅ Suposiciones no verificadas: 0.
