# 🏛️ Análisis FINAL — Paso 4: Mover `baseline.py` a `src/cli/commands/`

> **Unificador:** Arquitecto Senior
> **Paso:** 4 — Hotfix Post-Certificación
> **Fecha:** 2026-05-02
> **Origen:** Unificación de 4 análisis (kimi, glm, qwen, ds)
> **Fase:** testing — Hotfix post-certificación

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score |
|:---|:---|:---|:---|:---|:---|
| kimi | ✅ 14 elementos verificados | 3 (import alias, PROJECT_ROOT, check_env.py) | ✅ `validate_cli_structure.py` | ✅ Líneas exactas, docstring check_env.py:6-8 | 4.0 |
| glm | ✅ 14 elementos verificados | 4 (D1-D4: import alias, nombre función, PROJECT_ROOT, check_env.py) | ❌ No propone (justifica: paso trivial) | ✅ Verificación en vivo (`uv run python -c`), Patrones PROJECT_ROOT en commands/ | 4.5 |
| qwen | ✅ 12 elementos verificados | 2 (PROJECT_ROOT, docstring ruta) | ✅ `fap move-cli-cmd` / `validate_cli_move.py` | ✅ Firma línea 122 completa | 3.5 |
| ds | ✅ 8 elementos verificados | 3 (D1-D3: import alias, nombre función, check_env.py) | ⚠️ Reutiliza `fap baseline-check` existente como verificación (no crea herramienta nueva) | ✅ grep único punto import | 3.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Plan asume `run as baseline_check` → función real es `baseline_check` directamente | kimi, glm, ds | ✅ `baseline.py:122` → `def baseline_check(...)` | Import sin alias: `from src.cli.commands.baseline_check import baseline_check` |
| 2 | Plan DESPUÉS dice `import run as baseline_check` → incorrecto, función no se llama `run` | glm, ds | ✅ Refuerza D1 | Import correcto: `from src.cli.commands.baseline_check import baseline_check` |
| 3 | `PROJECT_ROOT` usa 3 niveles (`parent.parent.parent`) → necesita 4 niveles post-move | kimi, glm, qwen, ds | ✅ `baseline.py:23` → 3 niveles; `lint_fix.py:16`, `security_audit.py:22` → `parents[3]` (4 niveles) | Cambiar `parent.parent.parent` → `parents[3]` post-move |
| 4 | `check_env.py:7` referencia `baseline_check.py` como inexistente → post-move existirá | kimi, glm, ds | ✅ Leído en código | Opcional: limpiar docstring. No bloqueante |
| 5 | Docstring línea 1 dice `src/cli/baseline.py` → debe actualizarse a nueva ruta | qwen | ✅ Línea 1 verificada | Actualizar docstring a `src/cli/commands/baseline_check.py` |
| 6 | Solo `main.py:14` importa `src.cli.baseline` → único punto de cambio | glm, ds | ✅ Grep confirmado: solo línea 14 y comentario check_env.py:7 | Cambio único en `main.py:14` |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Mover `src/cli/baseline.py` a `src/cli/commands/baseline_check.py`, eliminando la única inconsistencia estructural del CLI y normalizando la disposición de comandos.
- **Correcciones al plan:** (1) Plan Tarea 4.2 asume `from src.cli.baseline import run as baseline_check` → código real usa `from src.cli.baseline import baseline_check` (sin alias). (2) Plan no menciona ajuste de `PROJECT_ROOT` post-move. (3) Plan DESPUÉS usa nombre función incorrecto (`run as baseline_check`).
- **DX seleccionada:** `validate_cli_structure.py` (script de validación). Detecta comandos CLI en `main.py` cuyo módulo no esté bajo `src/cli/commands/`. Previene futuras desalineaciones como la corregida aquí. Fusión: kimi propuso AST parsing; qwen propuso validación post-move → combinado en script que valida estructura completa pre/post.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Ejecutar `validate_cli_structure.py` → detecta `baseline.py` fuera de `commands/`
2. Mover `src/cli/baseline.py` → `src/cli/commands/baseline_check.py`
3. Corregir `PROJECT_ROOT` de 3 a 4 niveles en archivo movido
4. Actualizar docstring línea 1 con nueva ruta
5. Cambiar import en `main.py:14` → `from src.cli.commands.baseline_check import baseline_check`
6. Eliminar `src/cli/baseline.py` original
7. Verificar: `uv run python -m src.cli.main baseline-check --help` → exit 0
8. Verificar: `ruff check src/ tests/` → 0 errores

### Edge Cases MVP

- **Import roto:** Si símbolo `baseline_check` no coincide → `ModuleNotFoundError` inmediato al ejecutar Typer app. Detección: verificación inline post-move.
- **PROJECT_ROOT incorrecto:** Si no se ajusta a 4 niveles → `baseline_check` ejecuta `uv run pytest` desde `src/` en lugar de raíz → subprocess falla. Detección: test funcional.
- **Archivo original no eliminado:** Si `baseline.py` persiste → import ambiguo. Detección: `ls src/cli/baseline.py` debe fallar.
- **`__pycache__` stale:** Python puede cachear bytecode viejo. Mitigación: eliminar `__pycache__` post-move.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### Archivo 1: `src/cli/baseline.py` → MOVER → `src/cli/commands/baseline_check.py`

- **Ruta real:** `src/cli/commands/baseline_check.py`
- **Tipo de cambio:** Mover + modificar 2 líneas internas
- **Descripción:** Archivo completo movido. Contenido idéntico salvo:
  - Línea 1: docstring `"""src/cli/baseline.py...` → `"""src/cli/commands/baseline_check.py...`
  - Línea 23: `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` → `PROJECT_ROOT = Path(__file__).resolve().parents[3]`
- **Función pública:** `def baseline_check(audit_tools: bool = typer.Option(False, "--audit-tools", help="Incluye auditoria detallada de tools")) -> None`
- **Funciones privadas:** `_run_cmd()`, `_check_p0_1_importability()`, `_check_p0_2_existing_suite()`, `_check_p0_3_lint()`, `_check_p0_4_tool_registry()`, `_check_p0_5_fixtures()`
- **Patrón a seguir:** `src/cli/commands/lint_fix.py` — estructura comando en `commands/`, `parents[3]` para PROJECT_ROOT

#### Archivo 2: `src/cli/main.py` → MODIFICAR línea 14

- **Ruta real:** `src/cli/main.py`
- **Tipo de cambio:** Modificación (1 línea)
- **Descripción:** Cambiar import de `src.cli.baseline` a `src.cli.commands.baseline_check`
- **Cambio exacto:**
  ```python
  # ANTES (línea 14):
  from src.cli.baseline import baseline_check
  # DESPUÉS:
  from src.cli.commands.baseline_check import baseline_check
  ```
- **Sin alias `as`:** La función se llama `baseline_check` en origen y destino.

#### Archivo 3: `src/cli/baseline.py` → ELIMINAR

- **Ruta real:** `src/cli/baseline.py`
- **Tipo de cambio:** Eliminación
- **Descripción:** Archivo original eliminado tras mover. Verificar que no existe.

#### Archivo 4 (opcional): `src/cli/commands/check_env.py` → MODIFICAR docstring obsoleto

- **Ruta real:** `src/cli/commands/check_env.py`
- **Tipo de cambio:** Modificación (docstring, líneas 6-7)
- **Descripción:** Limpiar comentario que dice `baseline_check.py que no existe`. Post-move, el archivo existirá.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: validate_cli_structure
- **Qué automatiza:** Detecta comandos CLI registrados en `main.py` cuyo módulo de origen NO esté bajo `src/cli/commands/`. Previene desalineaciones estructurales.
- **Tipo:** script / validador
- **Ubicación:** `scripts/validate_cli_structure.py`
- **Cómo se usa:** `python scripts/validate_cli_structure.py` o integrado en CI
- **Impacto para el usuario final:** El mantenedor no necesita verificar manualmente que todo comando nuevo esté en `commands/`. El validador falla si detecta drift. Para este paso, detecta `baseline.py` fuera de `commands/`.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Import sin alias:** La función se llama `baseline_check` en ambos lados. No usar `as`. Resolución: `from src.cli.commands.baseline_check import baseline_check`.
2. **`parents[3]` para PROJECT_ROOT:** Patrón ya usado en `lint_fix.py:16` y `security_audit.py:22`. Preferir `.parents[3]` sobre `.parent.parent.parent.parent` por brevedad y consistencia.
3. **No renombrar función:** Mantener `baseline_check` como nombre. Plan incorrecto al sugerir `run as baseline_check`.
4. **Eliminar archivo original:** No dejar duplicado en `src/cli/baseline.py`. Move = mv + rm, no cp.
5. **⚠️ El plan dice `from src.cli.baseline import run as baseline_check` pero el código real usa `from src.cli.baseline import baseline_check`. Se implementa según código real.**
6. **⚠️ El plan no menciona ajuste de `PROJECT_ROOT` post-move. Código real requiere cambio de 3→4 niveles. Se implementa el ajuste.**

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] `src/cli/commands/baseline_check.py` existe con contenido de baseline.py + PROJECT_ROOT corregido a parents[3] + docstring actualizado
✅ [CODE] `src/cli/baseline.py` original eliminado (no existe en filesystem)
✅ [CODE] `src/cli/main.py:14` importa desde `src.cli.commands.baseline_check` (sin alias `as`)
✅ [CODE] `src/cli/main.py:57` registra `app.command("baseline-check")(baseline_check)` sin cambios
✅ [BACKEND] `uv run python -m src.cli.main baseline-check --help` ejecuta sin ModuleNotFoundError
✅ [BACKEND] `uv run python -m src.cli.main baseline-check` ejecuta P0.1-P0.5 con PROJECT_ROOT correcto
✅ [FULLSTACK] `fap baseline-check` funciona idéntico a antes del move
✅ [LINT] `ruff check src/ tests/` → 0 errores
✅ [DX] `python scripts/validate_cli_structure.py` ejecuta sin errores y detecta drift estructural
```

**Funcionales:**
- [ ] Comando `fap baseline-check` ejecuta checks P0.1-P0.5 con salida Rich table + exit code 0/1
- [ ] Flag `--audit-tools` funciona correctamente post-move

**Técnicos:**
- [ ] `python -c "from src.cli.commands.baseline_check import baseline_check"` exit 0
- [ ] `ls src/cli/baseline.py` falla (archivo no existe)
- [ ] `ls src/cli/commands/baseline_check.py` existe
- [ ] PROJECT_ROOT resuelve a `D:\Develop\Personal\FluxAgentPro-v2` desde nueva ubicación

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `validate_cli_structure.py` — detecta drift de estructura CLI | Baja | 0.15h | Ninguna |
| 1 | Mover `baseline.py` → `commands/baseline_check.py` + corregir `PROJECT_ROOT` + docstring | Baja | 0.05h | Tarea 0 |
| 2 | Actualizar import en `main.py:14` → `from src.cli.commands.baseline_check import baseline_check` | Baja | 0.02h | Tarea 1 |
| 3 | Eliminar `src/cli/baseline.py` | Baja | 0.01h | Tarea 1 |
| 4 | Limpiar `__pycache__` stale | Baja | 0.01h | Tarea 3 |
| 5 | (Opcional) Limpiar docstring obsoleto en `check_env.py:6-7` | Baja | 0.01h | Tarea 1 |
| 6 | Verificar integridad E2E: `uv run python -m src.cli.main baseline-check --help` + `ruff check src/ tests/` | Baja | 0.05h | Tareas 1-4 |
| **TOTAL** | | | **0.30h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `PROJECT_ROOT` apunta a `src/` post-move | Alta | 3 niveles sube solo hasta `src/` desde `commands/` | Cambiar a `parents[3]`. Verificar con `uv run python -m src.cli.main baseline-check` |
| Import con alias `run as` del plan rompe módulo | Alta | Plan asume función `run`; código real usa `baseline_check` | Usar import directo sin alias: `from src.cli.commands.baseline_check import baseline_check` |
| `baseline.py` original no eliminado → import ambiguo | Media | Olvido de `rm` tras `mv` | Verificación inline: `ls src/cli/baseline.py` debe fallar |
| `__pycache__` stale causa import desde ruta vieja | Baja | Python cachea bytecode | Limpiar `__pycache__` tras move. Verificación funcional post-move |
| Docstring obsoleto en `check_env.py:6-7` | Muy Baja | Post-move, `baseline_check.py` existirá | Opcional: limpiar comentario. No bloquea |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Import desde nueva ruta funciona | `uv run python -c "from src.cli.commands.baseline_check import baseline_check"` | Exit 0, sin `ModuleNotFoundError` |
| TP-2 | Comando CLI ejecuta con help | `uv run python -m src.cli.main baseline-check --help` | Output Typer con opciones del comando |
| TP-3 | PROJECT_ROOT resuelve correctamente | Ejecutar `baseline_check` con `--audit-tools` en proyecto | Checks P0.1-P0.5 ejecutan desde raíz del proyecto (no desde `src/`) |
| TP-4 | Archivo viejo no existe | `ls src/cli/baseline.py` | Error: archivo no encontrado |
| TP-5 | Lint sin errores | `uv run ruff check src/ tests/` | Exit 0 |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60` / `uv run ruff check src/ tests/`

---

**Idioma de respuesta:** Español 🇪🇸