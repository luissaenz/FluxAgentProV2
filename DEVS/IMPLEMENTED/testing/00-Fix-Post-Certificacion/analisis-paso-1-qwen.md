# Análisis Técnico — Paso 1: Fix Lint I001

**Agente:** qwen
**Paso:** Paso 1 — Fix Lint I001
**Fecha:** 2026-05-02
**Versión plan:** v3.2

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ruff` como dev dependency | `proyecto-config.json` → `dependencies.dev` | ✅ | `ruff>=0.8.0` presente |
| 2 | `ruff check src/ tests/` retorna 3 errores I001 | Ejecución directa | ✅ | 3 errores, todos fixable con `--fix` |
| 3 | `validate_tools.py:69` imports desordenados | Lectura archivo línea 68-70 | ✅ | `crewai_tools` antes que `mcp` — orden alfabético incorrecto |
| 4 | `server.py:7-24` import block desordenado | Lectura archivo línea 7-24 | ✅ | `__future__` OK, stdlib OK, pero third-party `mcp.server` mezclado con relative imports `.config`, `.flow_to_tool`, `.tools` sin separación |
| 5 | `mcp_pool.py:149-150` imports desordenados | Lectura archivo línea 148-151 | ✅ | `crewai_tools` antes que `mcp` — mismo patrón que validate_tools.py |
| 6 | Comando `lint_fix` definido | `proyecto-config.json` → `commands.lint_fix` | ✅ | `uv run ruff check --fix src/ tests/` |
| 7 | Comando `lint` definido | `proyecto-config.json` → `commands.lint` | ✅ | `uv run ruff check src/ tests/` |
| 8 | Archivos NO existen ya como fixeados | Lectura directa de los 3 archivos | ✅ | Imports siguen desordenados — fix no aplicado |
| 9 | Convención import_style | `proyecto-config.json` → `conventions.import_style` | ✅ | `absolute (from src.xxx.yyy import Zzz)` — aplica a imports de proyecto, no a third-party sorting |
| 10 | Phase-state confirma lint 0 previo | `phase-state.md` línea 88 | ✅ | `Lint: 0 errores (ruff check src/ tests/)` — estado previo era limpio |

**Discrepancias encontradas:**

1. **D1:** `server.py` tiene imports relativos (`.config`, `.flow_to_tool`, `.tools`) mezclados con imports absolutos de third-party (`mcp.server`). Ruff I001 detecta bloque completo como desordenado, no solo los relativos. → **Resolución:** `ruff check --fix` reordena todo el bloque correctamente separando: `__future__` → stdlib → third-party → relative.

2. **D2:** `validate_tools.py` y `mcp_pool.py` comparten mismo patrón de error: `from crewai_tools import MCPServerAdapter` antes que `from mcp import StdioServerParameters`. Orden alfabético correcto: `crewai_tools` > `mcp` (c > m), pero ruff espera `mcp` antes que `crewai_tools` porque usa isort con orden de sección. → **Resolución:** `ruff check --fix` aplica orden isort correcto automáticamente.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No aplica.** Paso 1 no toca schema, tablas, migraciones ni datos. Es puramente linting de código fuente.

- ✅ Tablas tocadas: Ninguna
- ✅ Columnas agregadas/modificadas: Ninguna
- ✅ RLS policies: Ninguna
- ✅ Índices: Ninguno
- ✅ Tipos de datos: No aplica

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos afectados

| Archivo | Líneas | Tipo de error | Complejidad |
|---|---|---|---|
| `src/cli/commands/validate_tools.py` | 69-70 | I001: import block desordenado (inline imports dentro de try/except) | Baja |
| `src/mcp/server.py` | 7-24 | I001: import block desordenado (bloque completo de módulo) | Baja |
| `src/tools/mcp_pool.py` | 149-150 | I001: import block desordenado (inline imports dentro de try/except) | Baja |

### Patrones identificados

**validate_tools.py:69-70** — imports inline dentro de bloque try/except:
```python
# ANTES (desordenado):
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# DESPUÉS (ruff --fix):
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter
```
Ruff/isort ordena alfabéticamente: `mcp` < `crewai_tools`.

**server.py:7-24** — bloque de imports a nivel módulo:
```python
# ANTES (desordenado):
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
from .flow_to_tool import build_flow_tools
from .tools import get_static_tools, handle_tool_call

# DESPUÉS (ruff --fix):
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
from .flow_to_tool import build_flow_tools
from .tools import get_static_tools, handle_tool_call
```
El problema real: ruff isort agrupa imports en secciones (`__future__` → stdlib → third-party → local). El bloque actual tiene imports de `src.flows.*` (third-party del proyecto) antes que imports relativos (`.config`, `.flow_to_tool`, `.tools`). Ruff reordena: `src.flows.*` va en sección third-party, los `.` van en sección local.

**mcp_pool.py:149-150** — mismo patrón que validate_tools.py:
```python
# ANTES:
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# DESPUÉS:
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter
```

### Firmas/functions afectadas

Ninguna firma cambia. Solo reordenamiento de imports. No hay funciones/clases nuevas ni modificadas.

### Imports exactos post-fix

**validate_tools.py** (dentro de `_validate_mcp_tool`, línea ~69):
```python
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter
```

**server.py** (nivel módulo, línea ~7):
```python
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
from .flow_to_tool import build_flow_tools
from .tools import get_static_tools, handle_tool_call
```

**mcp_pool.py** (dentro de `_connect`, línea ~149):
```python
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter
```

### Calidad

- Complejidad ciclomática: No cambia (0 nuevas branches)
- Mantenibilidad: Mejora marginal — imports ordenados facilitan lectura
- Cohesión/acoplamiento: Sin cambio

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/endpoints

No se crean, modifican ni eliminan endpoints.

### Middleware

No se modifica middleware.

### Flujos de datos

Sin cambio. Los imports reordenados no alteran runtime behavior. Python resuelve imports por nombre, no por orden dentro del bloque.

### Contratos

Sin cambio. Interfaces públicas de los 3 archivos permanecen idénticas.

### Error handling

Sin cambio.

**Único riesgo:** Si algún import tiene side-effect de registro (como `import src.flows.architect_flow` que registra flows), el orden de ejecución dentro del bloque podría理论上 afectar el orden de registro. Pero en este caso:
- `server.py` los imports de flows ya están agrupados juntos — ruff no los separa de otros flows
- Los imports inline en `validate_tools.py` y `mcp_pool.py` son dentro de try/except — solo se ejecutan en runtime cuando se necesita

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

DB → Backend → Frontend → UX: **Sin impacto.** Fix puramente cosmético de linting.

### Coherencia

Plan dice "Eliminar 3 errores de import sorting" → ruff I001 confirma exactamente 3 errores → alineación 100%.

### Gaps

Ninguno. Paso es autocontenido y trivial.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: Pre-commit hook ruff I001
- **Qué automatiza:** Detecta y auto-fixea imports desordenados ANTES de que lleguen al repo. Evita que errores I001 se filtren en CI.
- **Tipo:** pre-commit hook
- **Cómo se usa:** `git commit` → hook ejecuta `ruff check --fix` automáticamente. Si hay cambios, commit se aborta para que el dev revise el diff.
- **Impacto para el usuario final:** Nunca más necesita ejecutar `ruff check --fix` manualmente antes de commit. CI nunca falla por I001.
- **Prioridad:** Tarea 0 — configurar antes de merge del fix
```

**Configuración propuesta:**
```yaml
# .pre-commit-config.yaml (nuevo archivo)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `ruff check src/ tests/` retorna 0 errores I001
✅ [CODE] `ruff check src/ tests/` retorna 0 errores totales
✅ [CODE] `validate_tools.py` imports reordenados (línea ~69)
✅ [CODE] `server.py` imports reordenados (línea ~7-24)
✅ [CODE] `mcp_pool.py` imports reordenados (línea ~149)
✅ [CODE] Ningún import eliminado ni agregado — solo reordenamiento
✅ [DX] Pre-commit hook ruff configurado (si se implementa Tarea 0)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `ruff --fix` reordena imports rompiendo side-effects | Baja | Imports con side-effect (registro de flows en server.py) podrían cambiar orden de ejecución | Verificar que `import src.flows.*` permanecen agrupados tras fix. Test `fap baseline-check` confirma importabilidad |
| Fix introduce nuevos lint errors | Baja | Ruff fix podría crear conflictos con otras reglas | Ejecutar `ruff check src/ tests/` post-fix para confirmar 0 errores |
| Pre-commit hook bloquea commits legítimos | Media | Hook con `--exit-non-zero-on-fix` aborta commit si hay cambios auto-aplicados | Configurar hook para auto-commit cambios o usar `--fix-only` sin abort |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Pre-commit hook ruff | `.pre-commit-config.yaml` | repos → ruff hook con `--fix --exit-non-zero-on-fix` | — | DX | Baja | 0.1h | Ninguna | → verificar: `git commit --allow-empty -m "test"` ejecuta hook sin errores |
| 1 | Ejecutar auto-fix ruff I001 | `src/cli/commands/validate_tools.py`, `src/mcp/server.py`, `src/tools/mcp_pool.py` | Solo reordenamiento de imports — sin cambio de firmas | `ruff check --fix` (auto-fix built-in) | CODE | Baja | 0.05h | Tarea 0 | → verificar: `ruff check src/ tests/` retorna 0 errores |
| 2 | Validar importabilidad post-fix | — | — | — | FULLSTACK | Baja | 0.05h | Tarea 1 | → verificar: `uv run python -c "from src.cli.commands.validate_tools import validate_tools_command; from src.mcp.server import server; from src.tools.mcp_pool import MCPPool"` sin errores |
| 3 | Validar baseline-check | — | — | — | FULLSTACK | Baja | 0.05h | Tarea 2 | → verificar: `uv run python -m src.cli.main baseline-check` ejecuta sin errores |

**Tiempo total estimado:** 0.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Configurar ruff isort rules explícitas en `pyproject.toml` para controlar orden de secciones (future-proof)
- Agregar `ruff check` como step en CI pipeline (GitHub Actions)
- Extender pre-commit hook para incluir `ruff-format` + `pytest --collect-only`
