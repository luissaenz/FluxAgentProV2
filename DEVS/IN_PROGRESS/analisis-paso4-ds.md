# Análisis Técnico — Paso 4: Mover `baseline.py` a `src/cli/commands/`

**Agente:** ds
**Fecha:** 2026-05-02
**Fuente:** plan.md v3.2 — Paso 4 (Tareas 4.1, 4.2, 4.3)
**Fase:** testing — Hotfix Post-Certificación

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/baseline.py` existe | glob `src/cli/baseline.py` | ✅ | archivo existe, 207 líneas |
| 2 | `src/cli/commands/baseline_check.py` NO existe | glob `src/cli/commands/baseline_check.py` | ✅ | NO existe — target libre |
| 3 | `src/cli/main.py` importa `baseline_check` | grep en `src/cli/main.py:14` | ✅ | `from src.cli.baseline import baseline_check` |
| 4 | `baseline_check()` es el nombre de la función | leída `baseline.py:122` | ✅ | `def baseline_check(...)` — NO `run()` |
| 5 | `app.command("baseline-check")` registrado | `main.py:57` | ✅ | `app.command("baseline-check")(baseline_check)` |
| 6 | `src/cli/commands/` dir existe y tiene comandos | ls `src/cli/commands/` | ✅ | 21 entries, patrón consistente |
| 7 | Comandos en `commands/` importan función por nombre | `validate_tools.py:97` | ✅ | `def validate_tools_command(...)` importado como tal |
| 8 | `src.cli.baseline` referenciado en otro lado | grep `src.cli.baseline` | ✅ | Solo en `main.py:14` y comentario en `check_env.py:6` |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan Tarea 4.2 dice `from src.cli.baseline import run as baseline_check` (ANTES) pero código real usa `from src.cli.baseline import baseline_check`. Función se llama `baseline_check`, no `run`. | Import actual = `from src.cli.baseline import baseline_check`. DESPUÉS debe ser `from src.cli.commands.baseline_check import baseline_check` (sin alias `as`, mantener nombre original). |
| D2 | Plan Tarea 4.2 dice DESPUÉS: `from src.cli.commands.baseline_check import run as baseline_check` — esto fallaría porque la función no se llama `run`. | DESPUÉS correcto: `from src.cli.commands.baseline_check import baseline_check` |
| D3 | `check_env.py:6` tiene comentario `analisis-FINAL.md referencia src/cli/commands/baseline_check.py que no existe`. Este archivo será creado por Paso 4. | Post-move, ese comentario será obsoleto (el archivo existirá). Opcional: limpiar comentario. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**N/A** — Paso 4 no toca DB, migraciones, RLS ni schema. Sin impacto en datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos afectados

| Archivo | Acción | Estado actual |
|---|---|---|
| `src/cli/baseline.py` | MOVER a `src/cli/commands/baseline_check.py` | 207 líneas, 1 función pública `baseline_check()` + helpers privados |
| `src/cli/main.py` | MODIFICAR import (línea 14) | `from src.cli.baseline import baseline_check` |

### Funciones en `baseline.py`

| Nombre | Visibilidad | Firma | Descripción |
|---|---|---|---|
| `_run_cmd` | Privada | `(cmd: list[str], timeout: int = 120) -> tuple[bool, str]` | Ejecuta subprocess con timeout |
| `_check_p0_1_importability` | Privada | `() -> tuple[bool, str]` | P0.1: pytest --collect-only |
| `_check_p0_2_existing_suite` | Privada | `() -> tuple[bool, str]` | P0.2: pytest excluyendo latency |
| `_check_p0_3_lint` | Privada | `() -> tuple[bool, str]` | P0.3: ruff check |
| `_check_p0_4_tool_registry` | Privada | `() -> tuple[bool, str]` | P0.4: list_tools() |
| `_check_p0_5_fixtures` | Privada | `() -> tuple[bool, str]` | P0.5: pytest --fixtures |
| `baseline_check` | **Pública** | `(audit_tools: bool = typer.Option(False, "--audit-tools", ...)) -> None` | Entry point del comando CLI |

### Patrón existente a seguir

**Comando de referencia:** `src/cli/commands/validate_tools.py`
- Archivo en `src/cli/commands/validate_tools.py`
- Función pública: `def validate_tools_command(...) -> None`
- Import en `main.py`: `from src.cli.commands.validate_tools import validate_tools_command`
- Registro: `app.command("validate-tools")(validate_tools_command)`

**Patrón para `baseline_check.py`:**
- Ubicación: `src/cli/commands/baseline_check.py`
- Función pública: `baseline_check` (nombre existente, sin cambios)
- Import: `from src.cli.commands.baseline_check import baseline_check`
- Registro: `app.command("baseline-check")(baseline_check)` (sin cambios, línea 57)

### Imports exactos

```python
# ANTES (main.py:14):
from src.cli.baseline import baseline_check

# DESPUÉS:
from src.cli.commands.baseline_check import baseline_check
```

### Modularidad

- Mover a `commands/` alinea con patrón de los otros 20 comandos
- `baseline.py` actual tiene 0 dependencias circulares
- No introduce nuevo acoplamiento — solo cambia path de import
- No hay duplicación de código

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**N/A** — Paso 4 no toca API, middleware, endpoints ni flujos backend. Solo CLI.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Usuario: fap baseline-check --audit-tools
  → main.py registra baseline_check (cmd) 
  → import desde src.cli.commands.baseline_check
  → ejecuta checks P0.1-P0.5
  → reporte Rich table en consola
  → exit code 0/1
```

Sin cambios en UX ni en flujo de datos DB → Backend → Frontend. Solo refactor estructural.

### Coherencia

- Paso 4 es puramente estructural: mover archivo suelto `src/cli/baseline.py` a `src/cli/commands/` donde viven los otros 20 comandos.
- Consistencia con `conventions.cli_pattern`: `commands via app.command()`.
- Todos los demás comandos están en `commands/` — `baseline.py` es el único fuera de lugar.

### Herramienta Propuesta: Script de verificación post-move

```
### Herramienta Propuesta: fap baseline-check (ya existe)
- **Qué automatiza:** Ya es herramienta DX existente. Post-move, verificar que siga funcionando.
- **Tipo:** comando Typer existente
- **Cómo se usa:** `uv run python -m src.cli.main baseline-check --help`
- **Impacto para el usuario final:** Cero — el comando debe funcionar idéntico tras el move.
- **Prioridad:** Tarea 0 — ejecutar verificación inmediatamente después del move + import update.
```

---

## 5️⃣ Criterios de Aceptación

```yaml
✅ [CODE] src/cli/baseline.py movido a src/cli/commands/baseline_check.py sin cambios de contenido
✅ [CODE] `from src.cli.commands.baseline_check import baseline_check` en main.py reemplaza import anterior
✅ [FULLSTACK] `uv run python -m src.cli.main baseline-check --help` muestra help sin errores
✅ [FULLSTACK] `uv run python -m src.cli.main baseline-check` ejecuta checks completos
✅ [CODE] `src/cli/baseline.py` ya no existe en su ubicación original
✅ [LINT] `ruff check src/` → 0 errores tras cambios
⚠️ [DX] Comentario en `check_env.py:6` que referenciaba `baseline_check.py` como inexistente queda obsoleto (opcional limpiar)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Import roto si nombre de función no coincide | **Alta** | Plan asume `run()` pero código tiene `baseline_check()` | D1 detectada en §0. Usar nombre real `baseline_check`, no alias `run`. |
| Otro código importa `src.cli.baseline` | Baja | Dependencia no detectada en grep | Verificado: solo `main.py:14`. `grep src.cli.baseline` confirma único punto. |
| `check_env.py` comentario queda desactualizado | Muy Baja | Comentario en línea 6 dice "baseline_check.py no existe" | Post-move existe. Opcional pero no bloqueante. |

---

## 7️⃣ Plan de Implementación

> **Reglas:** 1 tarea = 1 artefacto. Interfaz exacta. Patrón explícito. Verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **Verificar línea base pre-move** | — | `uv run python -m src.cli.main baseline-check --help` | — | DX | Baja | 0.01h | Ninguna | → verificar: comando funciona ANTES del move, output esperado |
| 1 | **Mover `baseline.py` a `commands/baseline_check.py`** | `src/cli/commands/baseline_check.py` | Contenido idéntico a `src/cli/baseline.py`. Función pública: `def baseline_check(audit_tools: bool = False) -> None` | `src/cli/commands/validate_tools.py` (archivo en commands/ con función pública) | CODE | Baja | 0.02h | Tarea 0 | → verificar: `ls src/cli/commands/baseline_check.py` existe + `src/cli/baseline.py` ya no existe |
| 2 | **Actualizar import en `main.py`** | `src/cli/main.py:14` | ANTES: `from src.cli.baseline import baseline_check` → DESPUÉS: `from src.cli.commands.baseline_check import baseline_check` | `src/cli/main.py:15` — `from src.cli.commands.check_env import check_env` (mismo patrón de import) | CODE | Baja | 0.02h | Tarea 1 | → verificar: `uv run python -m src.cli.main baseline-check --help` sin errores de import |
| 3 | **Verificar post-move** | — | `uv run python -m src.cli.main baseline-check --audit-tools` + `ruff check src/` | — | DX | Baja | 0.05h | Tareas 1-2 | → verificar: comando funciona + lint 0 + criterios de §5 cumplidos todos |

**Tiempo total estimado:** 0.1h

### Notas de implementación

1. **Tarea 1:** Usar `mv src/cli/baseline.py src/cli/commands/baseline_check.py`. NO renombrar función `baseline_check` a `run`.
2. **Tarea 2:** Cambio exacto en `main.py:14`:
   ```python
   # ANTES
   from src.cli.baseline import baseline_check
   # DESPUÉS
   from src.cli.commands.baseline_check import baseline_check
   ```
   La línea 57 (`app.command("baseline-check")(baseline_check)`) NO necesita cambios — el símbolo `baseline_check` se resuelve del nuevo import.
3. **No olvidar:** Mover archivo ANTES de actualizar import. Orden: Tarea 1 → Tarea 2.
4. **Opcional (baja prioridad):** Limpiar comentario en `check_env.py:6` que dice `analisis-FINAL.md referencia src/cli/commands/baseline_check.py que no existe`.

---

## 🔮 Roadmap

- **check_env.py:6** — comentario sobre `baseline_check.py` no existente quedará obsoleto post-fix. Limpiar en mantenimiento futuro.
- Ningún otro paso depende de Paso 4. Es independiente (ver `plan.md` Protocolo de Ejecución: "Pasos 1-4 en cualquier orden").

---

### Métrica de Calidad

| Métrica | Resultado |
|---|---|
| `proyecto-config.json` leído | ✅ |
| Elementos verificados (§0) | 8/8 (≥8 umbral mínimo para 1-2 archivos afectados) |
| Discrepancias detectadas | 3 (D1, D2, D3) |
| Secciones completadas | 8/8 (0-7) |
| Etapas cubiertas | 4/4 (data N/A, code, backend N/A, fullstack+DX) |
| Criterios de aceptación | 6 (1 por sub-paso, verificables) |
| Riesgos identificados | 3 (técnico, integración, legacy) |
| Tareas atómicas (1 artefacto) | 100% |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito | 100% |
| Verificación inline por tarea | 100% |
| Suposiciones no verificadas | 0 |
| Propuesta DX / Tooling | 1 (fap baseline-check existente, verificación pre/post-move) |
| Estimación de tiempo | 0.1h total |
