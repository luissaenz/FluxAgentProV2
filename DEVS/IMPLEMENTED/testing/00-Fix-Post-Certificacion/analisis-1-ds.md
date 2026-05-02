# Análisis Técnico — Paso 1: Fix Lint I001

**Agente:** ds
**Fecha:** 2026-05-02
**Origen:** `DEVS/plan.md` — Paso 1 (Fix Lint I001)
**Fase:** testing — Hotfix post-certificación

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/commands/validate_tools.py` existe | `ls src/cli/commands/` | ✅ | archivo existe, 220 líneas |
| 2 | `src/mcp/server.py` existe | `ls src/mcp/` | ✅ | archivo existe, 89 líneas |
| 3 | `src/tools/mcp_pool.py` existe | `ls src/tools/` | ✅ | archivo existe, 212 líneas |
| 4 | Regla I001 activa en `pyproject.toml` | `select = ["E", "F", "I", "B"]` | ✅ | I incluido en lint select |
| 5 | fixable enabled | `fixable = ["ALL"]` | ✅ | ALL fixable |
| 6 | Ruff >= 0.8.0 instalado | `pyproject.toml:52` | ✅ | `ruff>=0.8.0` en dev deps |
| 7 | I001 error en validate_tools.py:69 | `ruff check --select I001 --diff` | ✅ | `from crewai_tools`/`from mcp` sin blank line separator |
| 8 | I001 error en server.py:13 | `ruff check --select I001 --diff` | ✅ | `from mcp.server import Server` mal posicionado respecto a `mcp.server.stdio` |
| 9 | I001 error en mcp_pool.py:149 | `ruff check --select I001 --diff` | ✅ | mismo patrón que validate_tools.py |
| 10 | 3 errores I001 totales | `ruff check --select I001 --statistics` | ✅ | 3 errors, 3 fixable |
| 11 | `ruff check src/ tests/` actual | ejecutado contra repo | ✅ | solo 3 I001, 0 otros errores |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | **plan.md línea 77:** dice `src/mcp/server.py:7` pero línea 7 es `from __future__ import annotations`. Error real en línea 13 (`from mcp.server import Server`). Ruff reporta línea 13, no 7. | Corregir plan.md a `server.py:13` o ignorar — el `--fix` no depende de la línea exacta. No bloqueante. |
| D2 | `from crewai_tools import MCPServerAdapter` es **import condicional dentro de try block** (no top-level). Ruff I001 no reordena imports inline — solo pide blank line separator entre grupos. Correcto. | Sin acción. Confirmado que ruff solo pide \n separador, no reordenamiento. |

---

## 1️⃣ Análisis de Datos

**Sin impacto.** No hay tablas, migraciones ni schemas involucrados.

- ✅ Schema: sin cambios
- ✅ Integridad referencial: sin cambios
- ✅ RLS policies: sin cambios
- ✅ Índices: sin cambios
- ✅ Tipos de datos: sin cambios

---

## 2️⃣ Análisis de Código

**Naturaleza del cambio:** Reordenamiento de imports + blank line separators. Cero cambios de lógica.

### Archivo 1: `src/cli/commands/validate_tools.py:69`

**Actual:**
```python
try:
    from crewai_tools import MCPServerAdapter
    from mcp import StdioServerParameters
```

**Fix requerido:** blank line entre grupos de imports:
```python
try:
    from crewai_tools import MCPServerAdapter

    from mcp import StdioServerParameters
```

**Root cause:** `crewai_tools` (ext optional) y `mcp` (direct dep) son grupos de terceros diferentes → necesitan separador.

### Archivo 2: `src/mcp/server.py:13`

**Actual:**
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

import src.flows.architect_flow  # noqa: F401
```

**Fix requerido:** `from mcp.server.stdio` debe preceder a `from mcp.server` alfabéticamente dentro del grupo de terceros. Mover `from mcp.server import Server` después de las líneas `import src.flows.*`:

```python
from mcp.server.stdio import stdio_server

import src.flows.architect_flow  # noqa: F401

# Eager flow registration (mismos que main.py:15-17)
import src.flows.generic_flow  # noqa: F401
import src.flows.test_flows  # noqa: F401
from mcp.server import Server
```

### Archivo 3: `src/tools/mcp_pool.py:149`

Mismo patrón que `validate_tools.py:69`:
```python
try:
    from crewai_tools import MCPServerAdapter

    from mcp import StdioServerParameters
```

### Patrones existentes verificados

- **Imports inline dentro de try/except:** patrón usado en `validate_tools.py:49-52` (`from src.db.session import get_service_client`), `server.py:46-50` (`import json`, `from mcp.types...`). Consistente.
- **`from __future__ import annotations` primero:** `server.py:7` correcto, PEP 604 compliant.

### Calidad

- Cambio 0% funcional, 100% cosmético (lint)
- Riesgo de regresión: nulo — solo blank lines y orden de imports top-level
- Complejidad ciclomática: sin cambio

---

## 3️⃣ Análisis de Backend

**Sin impacto.** No hay endpoints, middleware, contratos ni flujos de datos modificados.

- ✅ APIs/endpoints: sin cambios
- ✅ Middleware: sin cambios
- ✅ Flujos: sin cambios
- ✅ Contratos: sin cambios
- ✅ Error handling: sin cambios

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo

```
src/cli/commands/validate_tools.py     → import orden corregido (blank line)
src/mcp/server.py                      → import orden corregido (move line)
src/tools/mcp_pool.py                  → import orden corregido (blank line)
         ↓
ruff check src/ tests/                 → 0 errores I001
```

**Sin impacto en UX, frontend, ni flujo end-to-end.**

### DX & Tooling

```
### Herramienta Propuesta: fap lint-fix
- **Qué automatiza:** Ejecuta `ruff check --fix src/ tests/` y reporta resultados. Evita que el desarrollador recuerde el comando exacto o lo busque en docs.
- **Tipo:** comando CLI (Typer)
- **Cómo se usa:** `fap lint-fix` → ejecuta auto-fix + muestra diff resumen
- **Impacto para el usuario final:** Elimina tarea manual de correr ruff con flags. Un comando, cero flags que recordar.
- **Prioridad:** Baja (el comando raw ya existe en Makefile como `make lint` con `ruff check`, y `ruff check --fix` es trivial)
```

**Nota:** Tarea 0 de DX es opcional para este paso — el fix raw `ruff check --fix src/ tests/` es suficientemente simple. La herramienta propuesta es un nice-to-have, no un blocker.

### Coherencia plan vs arquitectura

✅ Plan es correcto: el fix es `ruff check --fix` → elimina 3 I001 errors.
✅ No hay dependencias externas, DB, ni servicios involucrados.
✅ Riesgo de romper algo: cero (los imports corregidos son top-level o inline condicionales sin side effects).

---

## 5️⃣ Criterios de Aceptación

```
✅ [LINT] ruff check src/ tests/ retorna 0 errores I001
✅ [LINT] Los 3 archivos modificados compilan sin error de import
✅ [CODE] validate_tools.py: blank line entre crewai_tools y mcp
✅ [CODE] server.py: from mcp.server import Server movido post stdio
✅ [CODE] mcp_pool.py: blank line entre crewai_tools y mcp
✅ [DX] Sin regresión en otros checks (E, F, B rules)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Ruff --fix mueve import a posición incorrecta | Baja | `ruff --fix` es determinista para I001 | Verificar con `ruff check` post-fix. Si falla, revert y manual |
| `from __future__ import annotations` mal ubicado post-fix | Baja | Ruff respeta `__future__` como first import | Revisión visual post-fix. En server.py línea 7 ya está correcto |
| Import inline dentro de try/exept se reordena incorrectamente | Baja | Ruff no reordena imports inline (solo top-level) | Confirmado con `--diff` — solo añade blank line, no reordena |

---

## 7️⃣ Plan de Implementación

> **Nota:** Paso 1 es atómico por naturaleza — un solo `ruff check --fix` cubre los 3 errores simultáneamente. Pero segmentado por archivo + verificación para consistencia con metodología.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX Tooling (opcional):** crear comando `fap lint-fix` | `src/cli/commands/lint_fix.py` | `app.command("lint-fix")` → ejecuta `ruff check --fix src/ tests/` vía subprocess | `src/cli/commands/security_audit.py` (Typer command pattern) | DX | Baja | 0.15h | Ninguna | → `ruff check src/ tests/` retorna 0 |
| 1 | Fix I001 en `validate_tools.py:69` | `src/cli/commands/validate_tools.py` | Línea 69-70: blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` | — | CODE | Baja | 0.02h | Ninguna | → `ruff check src/cli/commands/validate_tools.py --select I001` → 0 errors |
| 2 | Fix I001 en `server.py:13` | `src/mcp/server.py` | Mover `from mcp.server import Server` (línea 13) después de los `import src.flows.*` (líneas 16-20). Orden: `mcp.server.stdio` → `src.flows.*` → `mcp.server` → `from .*` | — | CODE | Baja | 0.02h | Ninguna | → `ruff check src/mcp/server.py --select I001` → 0 errors |
| 3 | Fix I001 en `mcp_pool.py:149` | `src/tools/mcp_pool.py` | Línea 149-150: blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` | Mismo patrón que Tarea 1 | CODE | Baja | 0.02h | Ninguna | → `ruff check src/tools/mcp_pool.py --select I001` → 0 errors |
| 4 | Verificación global | — | — | — | LINT | Baja | 0.02h | Tareas 1-3 | → `ruff check src/ tests/` → 0 errors total |

**Tiempo total estimado:** 0.23h (14 min)

**Orden de ejecución:** Tareas 1-3 independientes, pueden ejecutarse en paralelo. Tarea 4 es verificación post-fix. Tarea 0 (DX) es opcional y debe ir primero si se implementa.

### Test de atomicidad

Cada tarea toca un solo archivo. Ninguna requiere decisión de diseño. Todas las interfaces están especificadas al detalle (qué línea modificar y cómo). ✅ Correctamente segmentado.
