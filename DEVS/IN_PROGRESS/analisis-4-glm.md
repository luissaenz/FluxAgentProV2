# Análisis Técnico — Paso 4: Mover `baseline.py` a `src/cli/commands/`

> **Agente:** glm
> **Paso:** Paso 4 — Mover `baseline.py` a `src/cli/commands/`
> **Plan ref:** `DEVS/plan.md` §Paso 4
> **Phase-state ref:** `DEVS/phase-state.md` §Fase VI — testing

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/baseline.py` existe | glob `src/cli/baseline.py` | ✅ | 207 líneas, 1 función pública + 6 helpers |
| 2 | `src/cli/commands/baseline_check.py` NO existe | glob `src/cli/commands/baseline_check.py` | ✅ | No encontrado — target libre |
| 3 | Import en `main.py:14` | `from src.cli.baseline import baseline_check` | ✅ | Única referencia al módulo viejo |
| 4 | Registro en `main.py:57` | `app.command("baseline-check")(baseline_check)` | ✅ | Comando registrado correctamente |
| 5 | Función se llama `baseline_check` | `baseline.py:122` → `def baseline_check(...)` | ✅ | NO se llama `run` |
| 6 | `PROJECT_ROOT` en `baseline.py:23` | `Path(__file__).resolve().parent.parent.parent` | ✅ | 3 niveles — necesita 4 después del move |
| 7 | Patrón `PROJECT_ROOT` en `commands/` | `lint_fix.py:16` → `parents[3]` | ✅ | 4 niveles — correcto para commands/ |
| 8 | Patrón `PROJECT_ROOT` en `security_audit.py:22` | `Path(__file__).resolve().parents[3]` | ✅ | Mismo patrón 4 niveles |
| 9 | `baseline_check` importable | `uv run python -c "from src.cli.baseline import baseline_check; print('OK:', baseline_check.__name__)"` | ✅ | Salida: `OK: baseline_check` |
| 10 | `check_env.py:6-7` referencia a `baseline_check.py` | `analisis-FINAL.md referencia src/cli/commands/baseline_check.py que no existe` | ⚠️ | Comentario obsoleto post-move |
| 11 | `src/cli/__init__.py` NO existe | glob | ✅ | No existe — los módulos se importan por path absoluto |
| 12 | `src/cli/commands/__init__.py` NO existe | glob | ✅ | Ídem — namespace packages |
| 13 | No hay tests unitarios de `baseline.py` | grep `baseline` en `tests/` | ✅ | 0 tests directos de baseline |
| 14 | Plan Tarea 4.2: `from src.cli.baseline import run as baseline_check` | Verificación contra código real | ❌ | **DISCREPANCIA** — ver D1 |

**Discrepancias encontradas:**

| ID | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan Tarea 4.2 dice ANTES: `from src.cli.baseline import run as baseline_check` pero código real usa `from src.cli.baseline import baseline_check`. La función NO se llama `run`, se llama `baseline_check` directamente. No hay alias `as`. | ANTES real: `from src.cli.baseline import baseline_check`. DESPUÉS: `from src.cli.commands.baseline_check import baseline_check`. Sin alias `as`. |
| D2 | Plan Tarea 4.2 dice DESPUÉS: `from src.cli.commands.baseline_check import run as baseline_check` — nombre de función incorrecto. | DESPUÉS correcto: `from src.cli.commands.baseline_check import baseline_check`. El símbolo exportado es `baseline_check`, no `run`. |
| D3 | `baseline.py:23` usa `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` (3 niveles). Post-move a `commands/` necesita 4 niveles. Plan no menciona este cambio. | Cambiar a `Path(__file__).resolve().parents[3]` o `.parent.parent.parent.parent`. Patrón existente en `commands/`: mix de `parents[3]` y `.parent.parent.parent.parent`. Ambos correctos. |
| D4 | `check_env.py:6-7` tiene comentario que dice `baseline_check.py` no existe. Post-move, existirá. | Opcional: limpiar comentario. No bloqueante. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Paso 4 es puramente estructural (mover archivo). No hay cambios de schema, DB, ni RLS.

- ✅ **Sin cambios de DB:** Ninguna tabla tocada
- ✅ **Sin migraciones:** N/A
- ✅ **Sin RLS/índices:** N/A

**Impacto en datos existentes:** Ninguno.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos afectados

| Archivo | Acción | Detalle |
|---|---|---|
| `src/cli/baseline.py` | MOVER → `src/cli/commands/baseline_check.py` | 207 líneas. Renombrar archivo, ajustar `PROJECT_ROOT`. Contenido idéntico salvo línea 23. |
| `src/cli/main.py:14` | MODIFICAR import | `from src.cli.baseline import baseline_check` → `from src.cli.commands.baseline_check import baseline_check` |

### Funciones en `baseline.py`

| Función | Visibilidad | Firma | Rol |
|---|---|---|---|
| `_run_cmd` | Privada | `(cmd: list[str], timeout: int = 120) -> tuple[bool, str]` | Ejecuta subprocess con timeout |
| `_check_p0_1_importability` | Privada | `() -> tuple[bool, str]` | Verifica P0.1 |
| `_check_p0_2_existing_suite` | Privada | `() -> tuple[bool, str]` | Verifica P0.2 |
| `_check_p0_3_lint` | Privada | `() -> tuple[bool, str]` | Verifica P0.3 |
| `_check_p0_4_tool_registry` | Privada | `() -> tuple[bool, str]` | Verifica P0.4 |
| `_check_p0_5_fixtures` | Privada | `() -> tuple[bool, str]` | Verifica P0.5 |
| `baseline_check` | **Pública** | `(audit_tools: bool = typer.Option(False, "--audit-tools", help="Incluye auditoria detallada de tools")) -> None` | Entry point del comando CLI |

### Cambios internos necesarios en `baseline_check.py`

Único cambio interno: línea 23 de `baseline.py`:

```python
# ANTES (3 niveles — correcto para src/cli/baseline.py):
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# DESPUÉS (4 niveles — correcto para src/cli/commands/baseline_check.py):
PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

Patrón seguido: `lint_fix.py:16`, `security_audit.py:22` usan `parents[3]`. Otros usan `.parent.parent.parent.parent`. Ambos equivalentes. `parents[3]` más compacto.

### Patrón de referencia

**Archivo a seguir:** `src/cli/commands/lint_fix.py`
- Ubicación: `src/cli/commands/`
- Función pública directa: `def lint_fix(check: bool = ..., ...) -> None`
- Import en main.py: `from src.cli.commands.lint_fix import lint_fix`
- Registro: `app.command("lint-fix")(lint_fix)`
- `PROJECT_ROOT` con 4 niveles: `Path(__file__).resolve().parents[3]`

`baseline_check.py` seguirá el mismo patrón exacto.

### Imports de `baseline.py`

```python
from __future__ import annotations
import subprocess
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from src.tools.registry import tool_registry  # línea 84 (import diferido dentro de _check_p0_4)
```

Todos los imports se mantienen iguales. No hay imports relativos. No hay imports al propio módulo.

### Modularidad

- `baseline.py` tiene 0 dependencias circulares
- Solo 1 import interno diferido: `from src.tools.registry import tool_registry` (dentro de `_check_p0_4_tool_registry()`)
- La función `tool_registry.get_metadata()` en línea ~170 también importa dentro del bloque try
- Post-move: estos imports internos siguen funcionando igual (rutas absolutas)

### Calidad

- Complejidad ciclomática baja: `baseline_check()` orquesta 5 sub-checks secuenciales
- Cada sub-check es función privada independiente
- Sin duplicación de código
- Movimiento puro — se mantiene toda la lógica intacta

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/Endpoints

- ✅ **Sin changes de API:** No se crea/elimina/modifica ningún endpoint
- ✅ **Middleware sin cambios:** N/A

### Flujos

1. Usuario ejecuta `fap baseline-check [--audit-tools]`
2. CLI → `typer` → `main.py` → resuelve `baseline_check` desde import
3. `baseline_check()` ejecuta P0.1-P0.5 en secuencia

Post-move: paso 2 cambia la resolución de import de `src.cli.baseline` a `src.cli.commands.baseline_check`. Flujo idéntico.

### Contratos

- Comando CLI: `fap baseline-check [--audit-tools]`
- Firma Typer: `baseline_check(audit_tools: bool)` → retorna `None` o `typer.Exit(code=1)`
- Output: Rich table + console prints + exit code 0/1

### Error handling

- `_run_cmd()` maneja `TimeoutExpired` y `Exception` genérica con tupla `(bool, str)`
- `_check_p0_4_tool_registry()` usa try/except para errors de import
- Post-move: sin cambios en error handling

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
DB: N/A (baseline no toca DB)
Backend: N/A (CLI tool, no API)
CLI: fap baseline-check → main.py → import → baseline_check() → subprocess + tool_registry
UX: Rich table + pass/fail + GATE check
```

### Coherencia

- ✅ Movimiento puramente organizacional. Comando funciona igual.
- ✅ Consistencia con los otros 20 comandos que YA están en `commands/`
- ✅ `baseline.py` es el ÚNICO archivo suelto en `src/cli/` (no en `commands/`). Moverlo normaliza la estructura.

### Alineación con arquitectura existente

- Convención CLI del proyecto: `src/cli/commands/<comando>.py` con función pública
- `check_env.py`, `lint_fix.py`, `security_audit.py`, etc. — todos en `commands/`
- Este move elimina la única inconsistencia estructural

### Gaps / Friction

- Comentario obsoleto en `check_env.py:6-7`. Post-move, `baseline_check.py` existirá. Baja prioridad.

### DX & Tooling (OBLIGATORIO)

No se propone herramienta DX nueva para este paso. Justificación:

1. El paso es trivial: mover 1 archivo + cambiar 2 líneas (1 import, 1 PROJECT_ROOT)
2. Ya existen herramientas DX (`fap baseline-check` es el propio comando)
3. Agregar tooling para un paso de 2 líneas genera más overhead que valor

Alternativa considerada (rechazada): `fap move-command --from src/cli/baseline.py --to src/cli/commands/baseline_check.py` — demasiado específico, no se reutilizará.

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] src/cli/baseline.py ya NO existe en su ubicación original
✅ [CODE] src/cli/commands/baseline_check.py existe con contenido de baseline.py + PROJECT_ROOT corregido
✅ [CODE] src/cli/main.py:14 importa desde src.cli.commands.baseline_check (sin alias 'as')
✅ [CODE] src/cli/main.py:57 registra app.command("baseline-check")(baseline_check) sin cambios
✅ [CODE] uv run python -m src.cli.main baseline-check --help funciona sin errores de import
✅ [CODE] uv run python -c "from src.cli.commands.baseline_check import baseline_check" exit 0
✅ [STRUCTURE] src/cli/ ya no contiene archivos de comando sueltos (solo main.py, config.py, utils.py)
✅ [LINT] ruff check src/ tests/ → 0 errores
✅ [TEST] Suite existente (512 tests) sigue pasando — no hay tests unitarios de baseline
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Import roto si nombre de función no coincide | **Alta** | Plan asume `run()` pero código tiene `baseline_check()` | D1 detectada en §0. Usar nombre real `baseline_check`, NO alias `run`. DESPUÉS: `from src.cli.commands.baseline_check import baseline_check` |
| `PROJECT_ROOT` apunta a directorio incorrecto post-move | Alta | Path de 3 niveles funciona en `src/cli/` pero necesita 4 niveles en `src/cli/commands/` | D3 detectada. Cambiar `.parent.parent.parent` → `.parents[3]` |
| Línea olvidada en `main.py:57` | Baja | Si se cambia el símbolo importado accidentalmente | No tocar línea 57. El símbolo `baseline_check` se resuelve del nuevo import automáticamente |
| `check_env.py:6` comentario obsoleto | Muy Baja | Post-move, `baseline_check.py` existirá | Opcional limpiar. No bloquea funcionalidad |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX:** (No procede) | — | — | — | — | — | — | — | — |
| 1 | Mover `baseline.py` → `commands/baseline_check.py` + corregir `PROJECT_ROOT` | `src/cli/commands/baseline_check.py` | Contenido idéntico a `baseline.py` excepto línea 23: `PROJECT_ROOT = Path(__file__).resolve().parents[3]` | `src/cli/commands/lint_fix.py` (estructura de comando en `commands/`, `parents[3]` para PROJECT_ROOT) | CODE | Baja | 0.05h | Ninguna | → verificar: `ls src/cli/commands/baseline_check.py` existe AND `ls src/cli/baseline.py` NO existe |
| 2 | Actualizar import en `main.py` | `src/cli/main.py:14` | ANTES: `from src.cli.baseline import baseline_check` → DESPUÉS: `from src.cli.commands.baseline_check import baseline_check` | `src/cli/main.py:15` — `from src.cli.commands.check_env import check_env` (mismo patrón) | CODE | Baja | 0.02h | Tarea 1 | → verificar: `uv run python -m src.cli.main baseline-check --help` ejecuta sin errores |
| 3 | Eliminar `src/cli/baseline.py` | `src/cli/baseline.py` | Archivo eliminado | — | CODE | Baja | 0.01h | Tarea 1 | → verificar: `ls src/cli/baseline.py` falla (archivo no existe) |
| 4 | Verificar integridad post-move | — | — | — | FULLSTACK | Baja | 0.05h | Tareas 1-3 | → verificar: `uv run python -c "from src.cli.commands.baseline_check import baseline_check"` exit 0 AND `uv run ruff check src/ tests/` → 0 errores |

**Notas de implementación:**

1. **Tarea 1:** Usar `mv src/cli/baseline.py src/cli/commands/baseline_check.py`. Luego editar línea 23: cambiar `parent.parent.parent` → `parents[3]`. La función se mantiene como `baseline_check` — NO renombrar a `run`.

2. **Tarea 2:** Línea exacta a cambiar en `main.py:14`:
   ```python
   # ANTES:
   from src.cli.baseline import baseline_check
   # DESPUÉS:
   from src.cli.commands.baseline_check import baseline_check
   ```
   Línea 57 (`app.command("baseline-check")(baseline_check)`) NO necesita cambios — el símbolo `baseline_check` se resuelve del nuevo import.

3. **Tarea 3:** Si se usó `mv`, el archivo original ya no existe. Si se usó `cp`, eliminar manualmente.

4. **Opcional (baja prioridad):** Limpiar comentario en `check_env.py:6-7` que dice `baseline_check.py` no existe. Post-move, existirá.

**Tiempo total estimado:** 0.13 horas (∼8 minutos)

---

## 🔮 Roadmap (NO implementar ahora)

- Refactor `PROJECT_ROOT` a utilidad compartida (ej: `src/cli/utils.py:get_project_root()`) para eliminar duplicación entre 20 comandos.
- Consistencia `parents[3]` vs `.parent.parent.parent.parent` — estandarizar a uno solo en todo `commands/`.
- Agregar test unitario para `fap baseline-check` que verifique funcionamiento post-move.

---

## 🚫 Reglas de Oro — Verificación

- ✅ Análisis basado en código fuente real (no supuestos del plan)
- ✅ §0 completada antes de §1-6
- ✅ 4 discrepancias detectadas (D1-D4)
- ✅ 14 elementos verificados en §0 (umbral: ≥8 para 2-3 archivos)
- ✅ Etapas cubiertas: data, code, backend, fullstack+DX
- ✅ 9 criterios de aceptación verificables
- ✅ 4 riesgos identificados (1 alto, 1 alto, 1 bajo, 1 muy bajo)
- ✅ Tareas atómicas (1 artefacto por tarea)
- ✅ Interfaz exacta por tarea (sin inferencias)
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea
- ✅ DX: no se propone herramienta — paso es trivialmente simple