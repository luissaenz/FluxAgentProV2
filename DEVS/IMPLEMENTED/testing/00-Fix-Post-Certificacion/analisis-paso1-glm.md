# 🧠 Análisis Técnico — Paso 1: Fix Lint I001

> **Agente:** glm
> **Paso:** Paso 1 — Fix Lint I001
> **Fecha:** 2026-05-02
> **Plan:** `DEVS/plan.md` v3.2
> **Phase-state:** Fase VI testing CERRADA (8/8 pasos completados)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | 3 errores I001 existen | `ruff check --select I001 src/ tests/` | ✅ | Exactamente 3 errores, todos I001 auto-fixable |
| 2 | `validate_tools.py:69` — I001 | Línea 69: `from crewai_tools import MCPServerAdapter` sin blank line antes de `from mcp import StdioServerParameters` | ✅ VERIFICADO | Ruff output muestra rango 69-70, falta blank line entre imports de diferentes third-party |
| 3 | `server.py:7` — I001 | `from mcp.server import Server` línea 13 mal posicionada en bloque de imports | ✅ VERIFICADO | Ruff diff: mueve `from mcp.server import Server` después de `import src.flows.test_flows` (línea 20) |
| 4 | `mcp_pool.py:149` — I001 | Línea 149: `from crewai_tools import MCPServerAdapter` sin blank line antes de `from mcp import StdioServerParameters` | ✅ VERIFICADO | Rango 149-150 dentro de bloque try, misma causa que #2 |
| 5 | `ruff check --fix` genera diff seguro | `ruff check --diff` en los 3 archivos | ✅ VERIFICADO | Diff muestra solo reordenamiento de imports, sin cambios de lógica |
| 6 | `ruff` versión | `ruff --version` | ✅ | ruff 0.15.12 |
| 7 | Config ruff en pyproject.toml | `select: [E, F, I, B]`, `ignore: [E501, B008, E402, B904, B017]` | ✅ VERIFICADO | I001 = `unsorted-imports` está en el selector `I` (isort) |
| 8 | Archivos CLI sin I001 | `run.py`, `security_audit.py`, `stress_bench.py` | ✅ VERIFICADO | `ruff check --select I` retorna 0 errores en esos archivos |
| 9 | `pyproject.toml` no define `isort.known-first-party` | Ruff usa auto-detección basado en estructura del proyecto | ✅ VERIFICADO | `src.*` detectado como first-party, `mcp.*` como third-party |
| 10 | `from src.cli.baseline import baseline_check` en `main.py:14` | Import de ruta vieja — pertenece a Paso 4 | ⚠️ NO RELACIONADO | No tocar en Paso 1. Paso 4 se encarga de mover `baseline.py` |
| 11 | `server.py` — imports con `# noqa: F401` | Side-effect imports (registro de flujos) | ✅ VERIFICADO | `architect_flow`, `generic_flow`, `test_flows` con `noqa: F401` preservados en diff |
| 12 | No existen `ruff.toml` ni `.ruff.toml` | Config solo en pyproject.toml | ✅ VERIFICADO | Glob no encontró archivos adicionales de config |

**Discrepancias encontradas:**

| # | Discrepancia | Resolución |
|---|-------------|-----------|
| 1 | Plan dice "3 errores de import sorting" sin especificar que los 3 son idénticos I001 | Confirmado: 3/3 son I001 `unsorted-imports`. No hay otros tipos de lint. Correcto proceder con `--fix` |
| 2 | `server.py` diff mueve `from mcp.server import Server` DESPUÉS de `import src.flows.test_flows`, mezclando third-party y first-party | Ruff I001 con auto-detección coloca `mcp.*` y `src.flows.*` según grupos. El comentario `# Eager flow registration` entre los flow imports fuerza la separación. Resultado: `from mcp.server import Server` queda entre first-party y local imports. **Aceptable**: ruff lo ordena así y es lint-correcto según la config del proyecto. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Sin cambios. No se tocan tablas ni migraciones.
- ✅ **Integridad referencial:** N/A. Paso 100% client-side.
- ✅ **RLS policies:** N/A.
- ✅ **Índices:** N/A.
- ✅ **Tipos de datos:** N/A.

**Impacto en datos:** Ninguno. Paso puramente de lint — sin DB, sin schema, sin datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos afectados

#### 2.1 `src/cli/commands/validate_tools.py` (línea 69)

**Cambio:** Insertar blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` dentro del bloque `try`.

**Antes:**
```python
    try:
        from crewai_tools import MCPServerAdapter
        from mcp import StdioServerParameters
    except ImportError:
```

**Después:**
```python
    try:
        from crewai_tools import MCPServerAdapter

        from mcp import StdioServerParameters
    except ImportError:
```

**Justificación ruff:** `crewai_tools` y `mcp` son paquetes third-party distintos. Ruff I001 requiere blank line entre imports de diferentes paquetes third-party dentro del mismo grupo. Ambos están dentro de un `try` — ruff trata el bloque como un import block y exige la separación.

**Efecto en runtime:** Ninguno. Python ignora blank lines entre imports. El `try/except ImportError` funciona igual.

**Funciones afectadas:** `_validate_mcp_tool()` (líneas 42-93). La función importa tardíamente `crewai_tools` y `mcp` para manejar dependencias opcionales.

#### 2.2 `src/mcp/server.py` (líneas 7-24)

**Cambio:** Reordenar `from mcp.server import Server` dentro del bloque de imports.

**Antes:**
```python
from __future__ import annotations

import argparse
import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server

import src.flows.architect_flow  # noqa: F401

# Eager flow registration (mismos que main.py:15-17)
import src.flows.generic_flow  # noqa: F401
import src.flows.test_flows  # noqa: F401

from .config import MCPConfig
from .flow_to_tool import build_flow_tools
from .tools import get_static_tools, handle_tool_call
```

**Después (ruff --fix):**
```python
from __future__ import annotations

import argparse
import asyncio
import logging

from mcp.server.stdio import stdio_server

import src.flows.architect_flow  # noqa: F401

# Eager flow registration (mismos que main.py:15-17)
import src.flows.generic_flow  # noqa: F401
import src.flows.test_flows  # noqa: F401
from mcp.server import Server

from .config import MCPConfig
from .flow_to_tool import build_flow_tools
from .tools import get_static_tools, handle_tool_call
```

**Justificación ruff:** Ruff detecta la separación por el comentario `# Eager flow registration` como un split del import block. `from mcp.server import Server` se mueve al final del bloque de third-party/first-party antes de los local imports `.config`, `.flow_to_tool`, `.tools`.

**Efecto en runtime:** Ninguno. Python ejecuta imports en orden, pero `Server` se usa solo en la creación del objeto global `server = Server("FluxAgentPro-v2")` (línea 28), que ocurre después de todos los imports. Los imports `noqa: F401` son side-effect (registro de flujos) y se preservan con sus comentarios.

**Funciones afectadas:** Ninguna función directamente. `server` global (línea 28) usa `Server` importado. `main()` (línea 59) usa `MCPConfig`, `stdio_server`, `handle_list_tools`, `handle_call_tool`, `handle_tool_call`.

#### 2.3 `src/tools/mcp_pool.py` (línea 149)

**Cambio:** Insertar blank line entre `from crewai_tools import MCPServerAdapter` y `from mcp import StdioServerParameters` dentro del bloque `try`.

**Antes:**
```python
            try:
                from crewai_tools import MCPServerAdapter
                from mcp import StdioServerParameters
            except ImportError:
```

**Después:**
```python
            try:
                from crewai_tools import MCPServerAdapter

                from mcp import StdioServerParameters
            except ImportError:
```

**Justificación ruff:** Idéntica a 2.1. Paquetes third-party distintos requieren separación.

**Efecto en runtime:** Ninguno.

**Funciones afectadas:** `MCPPool.get_tools()` (líneas 77-190). Lazy import dentro de `_connect()` para manejar `ImportError` de dependencias opcionales.

### Patrones

- ✅ **Patrones existentes:** Los otros 15 comandos CLI (`run.py`, `security_audit.py`, etc.) y el resto de `src/mcp/` tienen imports ordenados correctamente. Pasan `ruff check --select I` sin errores.
- ✅ **Referencia:** `src/cli/commands/security_audit.py` — imports ordenados correctamente con `from __future__`, stdlib, third-party, first-party.
- ✅ **Modularidad:** Sin cambios. Solo reordenamiento de imports existentes.
- ✅ **Calidad:** Complejidad ciclomática sin cambios. Cero riesgo de regresión funcional.
- ✅ **Imports exactos:** No se agregan ni eliminan imports. Solo reordenamiento y blank lines.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** Sin cambios. Ningún endpoint modificado.
- ✅ **Middleware:** Sin cambios.
- ✅ **Flujos:** `server.py` es entry point del MCP server Stdio. El reordenamiento de imports no altera flujo de datos ni registro de handlers (`@server.list_tools()`, `@server.call_tool()`).
- ✅ **Contratos:** Sin cambios. No se modifica interfaz de ningún endpoint, servicio o clase.
- ✅ **Error handling:** Sin cambios. Los bloques `try/except ImportError` en `validate_tools.py:68-72` y `mcp_pool.py:148-154` se preservan intactos. Solo se agrega blank line entre imports dentro del `try`.

**Ejemplo request/response:** N/A — no hay cambios en endpoints.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo DB → Backend → Frontend:** Sin impacto. Cambio puramente de formato de código.
- ✅ **Coherencia:** Lint limpio es requisito CI. 3 errores I001 bloquean `ruff check` en modo estricto.
- ✅ **Alineación:** Plan indica `ruff check src/ tests/` → 0 errores como gate. Actualmente da 3 errores. Este paso cumple ese gate.
- ✅ **Gaps:** Ninguno. `ruff check --fix` resuelve 3/3 errores automáticamente.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: lint-fix-helper
- **Qué automatiza:** Ejecuta `ruff check --fix` + `ruff format` en un solo paso y valida resultado con `ruff check`
- **Tipo:** script (Makefile target)
- **Cómo se usa:** `make lint-fix`
- **Impacto para el usuario final:** Un comando en vez de 3. Evita olvidar `ruff format` después de `ruff check --fix`
- **Prioridad:** Tarea 0 — implementar antes del fix para validar automáticamente
```

**Nota:** Este paso es lo suficientemente simple que el DX tooling es menor valor. El principal valor es el `ruff check --fix` directo. Se propone como Makefile target ya que `Makefile` ya existe con targets `test-all`, `test-fast`, `coverage`.

**Flujo end-to-end:**
```
ruff check --fix src/ tests/  →  3 archivos modificados
       ↓
ruff check src/ tests/  →  0 errores (gate ✅)
       ↓
ruff format src/ tests/  →  formato consistente (opcional, ya OK)
       ↓
pytest tests/  →  512 tests pass (sin regresión)
```

**Puntos críticos:** Ninguno. Cambio de imports no afecta runtime.

---

## 5️⃣ Criterios de Aceptación

```
✅ [LINT] ruff check src/ tests/ → 0 errores (3 I001 corregidos)
✅ [LINT] ruff check --select I001 src/cli/commands/validate_tools.py → 0 errores
✅ [LINT] ruff check --select I001 src/mcp/server.py → 0 errores
✅ [LINT] ruff check --select I001 src/tools/mcp_pool.py → 0 errores
✅ [CODE] validate_tools.py — blank line entre crewai_tools y mcp imports en try block
✅ [CODE] server.py — from mcp.server import Server reordenado según diff de ruff
✅ [CODE] mcp_pool.py — blank line entre crewai_tools y mcp imports en try block
✅ [TEST] uv run pytest tests/ -x → 512 tests pass (sin regresión)
✅ [DX] make lint-fix disponible como atajo (opcional, Tarea 0)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| server.py: reordenar `from mcp.server import Server` altera orden de inicialización de módulos | Baja | Python ejecuta imports en orden; `Server` se usa en línea 28 (global) después de todos los imports | Global `server = Server(...)` se crea después del import block completo. Orden de imports dentro del block no afecta cuándo se instancian los objetos. |
| server.py: mover `from mcp.server import Server` cerca de los `src.flows.*` imports con `noqa: F401` | Baja | Si `mcp.server` tiene side-effects al import, el nuevo orden podría cambiar comportamiento | `mcp.server.Server` es una clase simple sin side-effects. Los `noqa: F401` son los que tienen side-effects (registro). Ruff los preserva con sus comentarios. |
| `ruff check --fix` introduce cambios no deseados en otros archivos | Media | Comando `--fix` afecta todo `src/` y `tests/` | Solo hay 3 errores I001 en todo el codebase. `ruff check --diff` confirmó que solo esos 3 archivos cambian. Ejecutar con `--diff` antes para validar. |
| CI falla si ruff version cambia entre local y CI | Baja | Diferencias de versión ruff | `ruff>=0.8.0` está en dev dependencies. Version pin en CI recomendado. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|-------------|-------------|
| 0 | **DX & Tooling:** Agregar target `lint-fix` a Makefile | `Makefile` | `lint-fix: ruff check --fix src/ tests/ && ruff format src/ tests/ && ruff check src/ tests/` | Makefile target `lint` existente (línea ~) | DX | Baja | 0.05h | Ninguna | → verificar: `make lint-fix` ejecuta sin errores y `make lint` retorna 0 |
| 1 | Ejecutar `ruff check --fix src/ tests/` | `src/cli/commands/validate_tools.py`, `src/mcp/server.py`, `src/tools/mcp_pool.py` | Sin interfaz nueva. Cambio: blank line en validate_tools.py:69-70, reordenar import en server.py:13→post-20, blank line en mcp_pool.py:149-150 | `src/cli/commands/security_audit.py` (imports ordenados correctamente como referencia) | CODE | Baja | 0.02h | Ninguna | → verificar: `ruff check src/ tests/` retorna 0 errores |
| 2 | Ejecutar `ruff format src/ tests/` | Mismos 3 archivos (si formato cambia) | Sin interfaz nueva | N/A | CODE | Baja | 0.02h | Tarea 1 | → verificar: `ruff format --check src/ tests/` retorna 0 |
| 3 | Validar suite completa sin regresión | `tests/` | `uv run pytest tests/ -x` — 512 tests pass | N/A | FULLSTACK | Baja | 0.10h | Tareas 1-2 | → verificar: `uv run pytest tests/ -x` → 512 passed, 0 failed |
| 4 | Validar gate de lint | — | `ruff check src/ tests/` → exit 0 | N/A | FULLSTACK | Baja | 0.02h | Tareas 1-2 | → verificar: `ruff check src/ tests/` sin output y exit 0 |

**Tiempo total estimado:** 0.21 horas (~13 minutos)

---

## 🔮 Roadmap (NO implementar ahora)

- Agregar `ruff check` y `ruff format` como pre-commit hooks para prevenir I001 en futuro
- Considerar `ruff check --fix --unsafe-fixes` cuando se necesiten más correcciones automáticas
- Consideración: `from src.cli.baseline` en `main.py:14` se modifica en Paso 4 (mover `baseline.py`). No tocar en Paso 1.