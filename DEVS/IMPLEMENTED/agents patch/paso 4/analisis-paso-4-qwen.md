# Análisis Técnico — Paso 4: Mover `baseline.py` a `src/cli/commands/`

**Agente:** qwen
**Paso:** paso 4
**Fecha:** 2026-05-02
**Versión plan:** v3.2

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/baseline.py` existe | glob + lectura completa | ✅ | 207 líneas, función `baseline_check()` |
| 2 | `src/cli/commands/` existe | ls directorio | ✅ | 21 archivos `.py` existentes |
| 3 | `src/cli/commands/baseline_check.py` NO existe | glob pattern | ✅ | No aparece en listado |
| 4 | `src/cli/main.py` import línea 14 | lectura línea 14 | ✅ | `from src.cli.baseline import baseline_check` |
| 5 | Registro comando línea 57 | lectura línea 57 | ✅ | `app.command("baseline-check")(baseline_check)` |
| 6 | Patrón comando existente | `check_env.py` lectura | ✅ | Función `check_env()` con typer.Options, Rich table, typer.Exit |
| 7 | Imports en `baseline.py` | líneas 12-19 | ✅ | `subprocess`, `pathlib`, `typer`, `rich.console`, `rich.table` |
| 8 | Firma `baseline_check()` | línea 122-126 | ✅ | `def baseline_check(audit_tools: bool = typer.Option(False, "--audit-tools", help="...")) -> None` |
| 9 | `PROJECT_ROOT` cálculo | línea 23 | ✅ | `Path(__file__).resolve().parent.parent.parent` — funcionará tras move (3 niveles arriba = raíz) |
| 10 | Funciones internas P0.1-P0.5 | líneas 43-119 | ✅ | `_check_p0_1_importability()` a `_check_p0_5_fixtures()` |
| 11 | `_run_cmd()` helper | líneas 26-40 | ✅ | `subprocess.run` con timeout, capture_output, cwd |
| 12 | Comando funciona actualmente | `baseline-check --help` ejecutado | ✅ | Output Typer correcto, muestra opciones |

**Discrepancias encontradas:**

1. **⚠️ `PROJECT_ROOT` cálculo post-move:** Línea 23 usa `Path(__file__).resolve().parent.parent.parent`. Tras mover de `src/cli/baseline.py` a `src/cli/commands/baseline_check.py`, el path relativo cambia: ahora necesita 4 niveles (`parent.parent.parent.parent`) para llegar a raíz del proyecto. **Resolución:** actualizar a 4 niveles o usar constante compartida.
2. **⚠️ Docstring línea 1:** Dice `"""src/cli/baseline.py` — debe actualizarse a nueva ruta tras move.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Sin impacto en datos.** Paso puramente estructural (move archivo CLI). No toca DB, schema, migraciones, RLS.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Artefactos afectados

**Archivo origen:** `src/cli/baseline.py` (207 líneas)
- Función principal: `baseline_check(audit_tools: bool = typer.Option(False, "--audit-tools", help="...")) -> None`
- Helpers internos: `_run_cmd()`, `_check_p0_1_importability()`, `_check_p0_2_existing_suite()`, `_check_p0_3_lint()`, `_check_p0_4_tool_registry()`, `_check_p0_5_fixtures()`
- Constante: `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent`
- Imports: `subprocess`, `pathlib.Path`, `typer`, `rich.console.Console`, `rich.table.Table`

**Archivo destino:** `src/cli/commands/baseline_check.py` (nuevo)
- Mismo contenido, con ajustes:
  - Docstring ruta actualizada
  - `PROJECT_ROOT` → 4 niveles: `Path(__file__).resolve().parent.parent.parent.parent`

**Archivo modificado:** `src/cli/main.py`
- Línea 14: cambiar `from src.cli.baseline import baseline_check` → `from src.cli.commands.baseline_check import baseline_check`

### Patrones existentes

**Patrón a seguir:** `src/cli/commands/check_env.py`
- Estructura: docstring con ruta → imports → constantes privadas → función comando con typer.Options → Rich table output → typer.Exit en error
- Naming: `snake_case.py` para archivos, misma convención que resto de `commands/`
- Imports: absolutos desde `src.*`

### Cohesión / Acoplamiento

- `baseline.py` autocontenido. Sin dependencias externas más allá de stdlib + typer + rich.
- `_check_p0_4_tool_registry()` importa `src.tools.registry` — dependencia lógica, no estructural. Se mantiene.
- Move no introduce acoplamiento nuevo. Reduce inconsistencia estructural.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin impacto en APIs/endpoints.** Comando CLI puro. No expone rutas HTTP.

**Flujo CLI:**
```
fap baseline-check → main.py app.command("baseline-check") → baseline_check() → ejecuta P0.1-P0.5 → Rich table → exit code 0/1
```

**Post-move, flujo idéntico.** Solo cambia import path en `main.py`.

**Error handling:**
- `_run_cmd()` captura `TimeoutExpired` + `Exception` genérica → retorna `(False, str(e))`
- `baseline_check()` usa `typer.Exit(code=1)` si algún sub-paso falla
- Post-move: mismo comportamiento

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
DB → (no toca)
Backend → (no toca)
CLI → main.py import → baseline_check() → P0.1-P0.5 checks → Rich table → gate pass/fail
UX → usuario ejecuta `fap baseline-check`, ve tabla consolidada, sabe si puede continuar
```

### Coherencia

- Move alinea `baseline.py` con patrón de `commands/` — consistencia estructural mejorada.
- `main.py` ya importa otros 20 comandos desde `commands/`. `baseline_check` era el único outlier en `src/cli/` directo.

### DX & Tooling (OBLIGATORIO)

### Herramienta Propuesta: `fap move-cli-cmd` (validador post-move)
- **Qué automatiza:** Verifica que un comando CLI movido funciona correctamente tras cambio de ubicación — importa desde nueva ruta, ejecuta `--help`, confirma registro en Typer app.
- **Tipo:** script de validación / comando CLI auxiliar
- **Cómo se usa:** `python scripts/validate_cli_move.py baseline-check src.cli.commands.baseline_check baseline_check`
- **Impacto para usuario final:** Elimina verificación manual post-move. Detecta imports rotos antes de commit.
- **Prioridad:** Tarea 0 — ejecutar antes de confirmar move completado

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `src/cli/baseline.py` ya no existe en ubicación original
✅ [CODE] `src/cli/commands/baseline_check.py` existe con mismo contenido + PROJECT_ROOT corregido a 4 niveles
✅ [CODE] `src/cli/main.py` línea 14 importa desde `src.cli.commands.baseline_check`
✅ [BACKEND] `fap baseline-check --help` ejecuta sin errores desde nueva ubicación
✅ [FULLSTACK] Comando registra como `baseline-check` en Typer app (línea 57 main.py sin cambios)
✅ [DX] Script validación move ejecuta sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `PROJECT_ROOT` cálculo incorrecto post-move | Alta | `parent.parent.parent` apunta a `src/` no raíz | Tarea 2 cambia a 4 niveles. Verificar con `--help` |
| Import en `main.py` no actualizado | Media | Olvido de cambiar línea 14 | Tarea 3 incluye cambio explícito + verificación |
| `__pycache__` stale causa import desde ubicación vieja | Baja | Python cachea bytecode | Ejecutar `find . -type d -name __pycache__ -exec rm -rf {} +` post-move |
| Otros archivos importan `src.cli.baseline` | Baja | Búsqueda necesaria para confirmar | grep `from src.cli.baseline` → solo `main.py` |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Script validación move CLI | `scripts/validate_cli_move.py` | `def validate_move(cmd_name: str, import_path: str, fn_name: str) -> bool` | `src/cli/commands/check_env.py` (estructura script standalone) | DX | Baja | 0.25h | Ninguna | → verificar: `uv run python scripts/validate_cli_move.py baseline-check src.cli.commands.baseline_check baseline_check` retorna 0 |
| 1 | Mover archivo `baseline.py` → `baseline_check.py` | `src/cli/commands/baseline_check.py` | contenido idéntico a `src/cli/baseline.py` | `src/cli/commands/check_env.py` (ubicación en commands/) | CODE | Baja | 0.05h | Tarea 0 | → verificar: `src/cli/baseline.py` no existe, `src/cli/commands/baseline_check.py` existe |
| 2 | Corregir `PROJECT_ROOT` en nuevo archivo | `src/cli/commands/baseline_check.py` línea 23 | `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent` | — | CODE | Baja | 0.05h | Tarea 1 | → verificar: `PROJECT_ROOT` resuelve a `D:\Develop\Personal\FluxAgentPro-v2` |
| 3 | Actualizar docstring ruta | `src/cli/commands/baseline_check.py` línea 1 | `"""src/cli/commands/baseline_check.py — Implementation...` | `src/cli/commands/check_env.py` línea 1 | CODE | Baja | 0.05h | Tarea 1 | → verificar: docstring dice `src/cli/commands/baseline_check.py` |
| 4 | Actualizar import en `main.py` | `src/cli/main.py` línea 14 | `from src.cli.commands.baseline_check import baseline_check` | `src/cli/main.py` líneas 15-34 (mismo patrón) | CODE | Baja | 0.05h | Tarea 1 | → verificar: `uv run python -c "from src.cli.commands.baseline_check import baseline_check"` sin error |
| 5 | Eliminar archivo original | `src/cli/baseline.py` | `rm src/cli/baseline.py` | — | CODE | Baja | 0.05h | Tareas 2-4 | → verificar: `ls src/cli/baseline.py` retorna error |
| 6 | Verificar comando funciona | — | — | — | FULLSTACK | Baja | 0.1h | Tareas 1-5 | → verificar: `uv run python -m src.cli.main baseline-check --help` muestra output Typer |
| 7 | Limpiar `__pycache__` stale | — | `find . -type d -name __pycache__ -exec rm -rf {} +` | — | CODE | Baja | 0.05h | Tarea 5 | → verificar: `uv run python -m src.cli.main baseline-check --help` sin warning import |

**Tiempo total estimado:** 0.65h

---

## 🔮 Roadmap (NO implementar ahora)

- Unificar `PROJECT_ROOT` en constante compartida (`src/cli/config.py` ya existe) — evitar cálculo duplicado en cada comando.
- Agregar `__init__.py` explícito en `src/cli/commands/` si no existe (verificar).
- Crear test unitario para `baseline_check()` — actualmente sin cobertura directa.

---

**Idioma de respuesta:** Español 🇪🇸
