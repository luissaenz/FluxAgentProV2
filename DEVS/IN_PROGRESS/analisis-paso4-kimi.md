# Análisis Técnico — Paso 4: Mover `baseline.py` a `src/cli/commands/`

> **Agente:** kimi
> **Paso:** 4
> **Fecha:** 2026-05-02
> **Origen:** `DEVS/plan.md` v3.2
> **Fase:** testing — Hotfix post-certificación

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/cli/baseline.py` existe | read file | ✅ | 207 líneas, función `baseline_check()` exportada |
| 2 | `src/cli/commands/baseline_check.py` NO existe | `ls src/cli/commands/` | ✅ | No aparece en listado (21 archivos, ninguno `baseline_check`) |
| 3 | `src/cli/main.py` importa `baseline_check` desde `src.cli.baseline` | read main.py:14 | ✅ | `from src.cli.baseline import baseline_check` |
| 4 | `src/cli/main.py` registra comando `"baseline-check"` | read main.py:57 | ✅ | `app.command("baseline-check")(baseline_check)` |
| 5 | Patrón CLI: archivos en `commands/` son `snake_case.py` | `ls src/cli/commands/` | ✅ | `check_env.py`, `lint_fix.py`, `perf_check.py`, etc. |
| 6 | No hay `__init__.py` en `src/cli/commands/` | glob `src/cli/commands/__init__.py` | ✅ | Archivo no encontrado |
| 7 | No hay tests unitarios para baseline | glob `tests/**/test_baseline*.py` | ✅ | 0 resultados |
| 8 | `check_env.py` ya documenta que `baseline_check.py` no existe en `commands/` | read check_env.py:6-8 | ✅ | Docstring: "analisis-FINAL.md referencia src/cli/commands/baseline_check.py que no existe" |
| 9 | `baseline.py` usa `typer.Option` para flags | read baseline.py:123 | ✅ | `audit_tools: bool = typer.Option(False, "--audit-tools", ...)` |
| 10 | `baseline.py` usa `typer.Exit(code=1)` para errores | read baseline.py:207 | ✅ | `raise typer.Exit(code=1)` |
| 11 | `baseline.py` usa Rich `Console` + `Table` | read baseline.py:18-19, 178 | ✅ | Consistente con `check_env.py`, `perf_check.py`, etc. |
| 12 | `PROJECT_ROOT` en `baseline.py` usa `parent.parent.parent` | read baseline.py:23 | ✅ | `Path(__file__).resolve().parent.parent.parent` |
| 13 | Función principal se llama `baseline_check`, no `run` | read baseline.py:122 | ❌ | Plan.md asume `run as baseline_check`; código real exporta `baseline_check` directamente |
| 14 | Todos los comandos en `commands/` importan desde `src.xxx` vía absolutos | read check_env.py:15-18 | ✅ | `from dotenv import load_dotenv`, `from rich.console import Console` |

**Discrepancias encontradas:**

1. **Import en `main.py` — plan asume alias `run as baseline_check`:**
   - Plan.md Tarea 4.2 propone:
     ```python
     from src.cli.baseline import run as baseline_check
     # →
     from src.cli.commands.baseline_check import run as baseline_check
     ```
   - **Código real:** `from src.cli.baseline import baseline_check` (línea 14). La función ya se llama `baseline_check`.
   - **Resolución:** Actualizar import a `from src.cli.commands.baseline_check import baseline_check` (sin alias `run as`).

2. **`PROJECT_ROOT` requiere ajuste de nivel tras el move:**
   - Actual: `Path(__file__).resolve().parent.parent.parent` → 3 niveles arriba de `src/cli/baseline.py` = raíz.
   - Tras mover a `src/cli/commands/baseline_check.py`: 3 niveles = `src/`, no raíz. Necesita 4 niveles (`parent.parent.parent.parent`).
   - **Plan.md no lo menciona.**
   - **Resolución:** Cambiar a `Path(__file__).resolve().parents[3]` (4 niveles arriba desde `commands/`) o factorizar constante compartida en `src/cli/__init__.py` (no recomendado — fuera de scope).

3. **`check_env.py` ya anticipaba esta inconsistencia:**
   - El docstring de `check_env.py` (línea 6-8) documenta que `analisis-FINAL.md` referenciaba `src/cli/commands/baseline_check.py` como inexistente. Esto confirma que la desalineación estructural era conocida pero no corregida en implementaciones previas.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

> **Resultado:** N/A — Paso puramente estructural. No toca schema de DB, migraciones, RLS ni índices.

- Sin tablas afectadas.
- Sin cambios de schema.
- Sin impacto en datos existentes.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/Clases a mover

**Archivo origen:** `src/cli/baseline.py`
**Archivo destino:** `src/cli/commands/baseline_check.py`

| Función | Firma exacta | Tipo |
|---|---|---|
| `baseline_check` | `def baseline_check(audit_tools: bool = typer.Option(False, "--audit-tools", help="Incluye auditoria detallada de tools")) -> None:` | Pública (registrada en Typer) |
| `_run_cmd` | `def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:` | Privada |
| `_check_p0_1_importability` | `def _check_p0_1_importability() -> tuple[bool, str]:` | Privada |
| `_check_p0_2_existing_suite` | `def _check_p0_2_existing_suite() -> tuple[bool, str]:` | Privada |
| `_check_p0_3_lint` | `def _check_p0_3_lint() -> tuple[bool, str]:` | Privada |
| `_check_p0_4_tool_registry` | `def _check_p0_4_tool_registry() -> tuple[bool, str]:` | Privada |
| `_check_p0_5_fixtures` | `def _check_p0_5_fixtures() -> tuple[bool, str]:` | Privada |

### Patrones

- **Patrón a seguir:** `src/cli/commands/check_env.py` (docstring con metadatos DX, `typer.Option`, `Console`, `Table`, `typer.Exit(code=1)`).
- **Patrón a seguir (Rich + subprocess):** `src/cli/commands/perf_check.py` o `src/cli/commands/stress_bench.py` — ambos ejecutan subprocesses y reportan con Rich.
- **Consistencia:** 100% de comandos CLI viven en `src/cli/commands/` excepto `baseline.py`. Moverlo cierra la excepción.

### Imports

- `from __future__ import annotations`
- `import subprocess`
- `from pathlib import Path`
- `import typer`
- `from rich.console import Console`
- `from rich.table import Table`
- `from src.tools.registry import tool_registry` (usado dinámicamente en P0.4 y audit_tools)

### Calidad

- **Cohesión:** Alta — todo el módulo hace una sola cosa: ejecutar checks P0.1-P0.5.
- **Acoplamiento:** Bajo — solo depende de `subprocess`, `typer`, `rich`, y `src.tools.registry` (lazy import dentro de funciones).
- **Complejidad ciclomática:** Baja — flujo lineal secuencial con acumulación de resultados.

### Ajustes necesarios al mover

1. `PROJECT_ROOT` debe usar `.parents[3]` (4 niveles) en lugar de `.parent.parent.parent` (3 niveles).
2. Docstring debe actualizar ruta (`src/cli/commands/baseline_check.py`).
3. No se requiere cambio de firma ni lógica.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

> **Resultado:** N/A — Cambio de CLI puro. No toca endpoints HTTP, middleware, auth/authz ni contratos de servicio.

- Sin APIs creadas/modificadas.
- Sin middleware involucrado.
- Sin flujos backend → frontend afectados.

El comando `fap baseline-check` ejecuta subprocesses locales (`uv run pytest`, `uv run ruff`) y accede a `tool_registry.list_tools()` en memoria. Todo ocurre en el host del desarrollador.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
Usuario ejecuta: fap baseline-check
    ↓
src/cli/main.py resuelve import → src/cli/commands/baseline_check.py
    ↓
baseline_check() ejecuta:
    P0.1: uv run pytest --collect-only
    P0.2: uv run pytest tests/ -k "not latency"
    P0.3: uv run ruff check src/ tests/
    P0.4: tool_registry.list_tools() (en-proceso)
    P0.5: uv run pytest --fixtures
    ↓
Reporte consolidado en Rich Table + exit code 0/1
```

### Coherencia

- Decisión de mover a `commands/` es coherente con convención `cli_pattern` de `proyecto-config.json`: "Typer app in src/cli/main.py — commands via app.command() or app.add_typer()".
- Todos los demás comandos ya están en `commands/`; `baseline.py` es la única excepción. Eliminar excepción reduce carga cognitiva.

### Gaps / Fricción

- **Fricción detectada:** No hay test unitario que valide que `baseline-check` se registre correctamente. Si el import en `main.py` se rompe, se detecta solo en ejecución manual o en `pytest --collect-only` (que ya es P0.1, pero P0.1 corre el comando desde subprocess, no testea el import de main.py directamente).
- **Fricción detectada:** `PROJECT_ROOT` hardcodeado por niveles de directorio es frágil ante refactors de estructura. Ya se romperá con este move.

### DX & Tooling (OBLIGATORIO)

```markdown
### Herramienta Propuesta: `validate_cli_structure`
- **Qué automatiza:** Detecta comandos CLI registrados en `main.py` cuyo módulo de origen NO esté bajo `src/cli/commands/`. Previene desalineaciones estructurales como la que corrige este paso.
- **Tipo:** script / validador
- **Cómo se usa:** `python scripts/validate_cli_structure.py` o integrado en `fap validate-architect-output`
- **Impacto para el usuario final:** El mantenedor/devenv no necesita recordar manualmente que todo comando nuevo debe ir en `commands/`. El validador falla en CI si alguien registra un comando desde fuera de `src/cli/commands/`.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso (es < 20 líneas de AST parsing).
```

---

## 5️⃣ Criterios de Aceptación

Lista binaria (sí/no), verificable:

```
✅ [CODE] Archivo `src/cli/baseline.py` movido a `src/cli/commands/baseline_check.py`
✅ [CODE] Función `baseline_check()` conserva firma exacta: `def baseline_check(audit_tools: bool = typer.Option(False, "--audit-tools", help="Incluye auditoria detallada de tools")) -> None`
✅ [CODE] `PROJECT_ROOT` en archivo movido apunta correctamente a raíz del proyecto (4 niveles parent desde `commands/`)
✅ [CODE] `src/cli/baseline.py` original eliminado (no duplicado)
✅ [CODE] Import en `src/cli/main.py` actualizado a `from src.cli.commands.baseline_check import baseline_check`
✅ [CODE] Comando `"baseline-check"` sigue registrado en `main.py` vía `app.command("baseline-check")(baseline_check)`
✅ [BACKEND] `uv run python -m src.cli.main baseline-check --help` ejecuta sin `ModuleNotFoundError`
✅ [BACKEND] `uv run python -m src.cli.main baseline-check` ejecuta P0.1-P0.5 sin errores de path
✅ [FULLSTACK] `fap baseline-check` (vía entrypoint configurado) funciona idéntico a antes del move
✅ [LINT] `ruff check src/cli/commands/baseline_check.py src/cli/main.py` → 0 errores
✅ [DX] (Opcional) Script `validate_cli_structure.py` detecta desalineaciones estructurales futuras
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `PROJECT_ROOT` apunta a `src/` en lugar de raíz tras el move | Alta | `parent.parent.parent` desde `commands/` sube solo hasta `src/` | Ajustar a `.parents[3]` (4 niveles) antes del primer test. Verificación inline en tarea. |
| Alias `run as baseline_check` del plan rompe import | Media | Plan asume función `run`; código real usa `baseline_check` | Usar import directo `from src.cli.commands.baseline_check import baseline_check` en main.py. |
| `baseline.py` original no se elimina y queda código muerto | Baja | Olvido de `git rm` o `del` tras `mv` | Verificación inline: `test -f src/cli/baseline.py` debe fallar (no existe). |
| Comando `fap baseline-check` falla en CI tras move por import circular o path | Baja | `main.py` importa `baseline_check` en tiempo de carga; si el nuevo path tiene error, CLI no arranca | Ejecutar `uv run python -m src.cli.main baseline-check --help` inmediatamente tras cambio de import. |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. **Una tarea = un artefacto**
> 2. **Interfaz completa en la tarea**
> 3. **Patrón de referencia explícito**
> 4. **Verificación inline**
> 5. **Test de atomicidad**

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** `validate_cli_structure.py` | `scripts/validate_cli_structure.py` | `def main() -> int:` (exit 0=OK, 1=drift) | — | DX | Baja | 0.1h | Ninguna | → verificar: `python scripts/validate_cli_structure.py` ejecuta sin error y detecta `baseline.py` fuera de `commands/` |
| 1 | Mover `baseline.py` a `commands/baseline_check.py` | `src/cli/commands/baseline_check.py` | Misma firma §2; `PROJECT_ROOT = Path(__file__).resolve().parents[3]` | `src/cli/commands/check_env.py` (estructura docstring + typer + rich) | CODE | Baja | 0.05h | Tarea 0 | → verificar: `test -f src/cli/commands/baseline_check.py` (existe) y `test -f src/cli/baseline.py` (no existe) |
| 2 | Actualizar import en `main.py` | `src/cli/main.py` | Línea 14: `from src.cli.commands.baseline_check import baseline_check` | Patrón existente en main.py (líneas 15-34) | CODE | Baja | 0.05h | Tarea 1 | → verificar: `uv run python -m src.cli.main baseline-check --help` imprime ayuda sin `ModuleNotFoundError` |
| 3 | Validar ejecución end-to-end | — | — | — | FULLSTACK | Baja | 0.05h | Tareas 1-2 | → verificar: `uv run python -m src.cli.main baseline-check` ejecuta P0.1-P0.5 sin errores de path |

**Tiempo total estimado:** 0.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Refactor `PROJECT_ROOT`:** Factorizar en `src/cli/_project_root.py` o `src/config.py` para evitar hardcodeo por niveles de directorio. Beneficia todos los comandos CLI.
- **Test unitario de registro CLI:** Agregar `tests/unit/test_cli_registration.py` que importe `main.py` y verifique que todos los comandos resuelvan sin errores. Previene rotura silenciosa de imports.
- **Autodiscover de comandos:** En lugar de imports manuales en `main.py`, usar `importlib` para cargar automáticamente todo módulo en `src/cli/commands/`. Reduce fricción al agregar nuevos comandos.

---

## 🚫 Reglas de Oro

- ✅ Análisis accionable y específico.
- ✅ TODO verificado contra código (14 elementos verificados > umbral de 8 para 1-2 archivos).
- ✅ 3 discrepancias detectadas (plan asume `run`, `PROJECT_ROOT` no mencionado, inconsistencia conocida documentada en `check_env.py`).
- ✅ Código gana sobre plan cuando hay discrepancia.
- ✅ Tareas atómicas (1 artefacto por tarea).
- ✅ Interfaz exacta por tarea.
- ✅ Verificación inline por tarea.
- ✅ ≥ 1 herramienta DX propuesta.

---

**Idioma de respuesta:** Español 🇪🇸
