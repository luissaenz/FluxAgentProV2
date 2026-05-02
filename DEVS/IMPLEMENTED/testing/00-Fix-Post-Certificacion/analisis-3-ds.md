# Análisis Técnico — Paso 3: Alinear nombres de pasos en TESTING.md

**Agente:** ds
**Fecha:** 2026-05-02
**Origen:** `plan.md` Paso 3
**Tipo:** Documentación (hotfix post-certificación)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | TESTING.md existe | glob TESTING.md → encontrado | ✅ | `D:\Develop\Personal\FluxAgentPro-v2\TESTING.md` |
| 2 | Línea 66: `### Paso 3: Validacion de Seguridad Profunda` | read TESTING.md:66 | ✅ | Coincide con plan — requiere cambio |
| 3 | Línea 72: `### Paso 4: Hardening de API Publica` | read TESTING.md:72 | ✅ | Coincide con plan — requiere cambio |
| 4 | Línea 78: `### Paso 5: Tests de Regresion E2E` | read TESTING.md:78 | ✅ | Coincide con plan — requiere cambio |
| 5 | plan.md nombres correctos para Paso 3 | plan.md:126 | ✅ | `E2E — Flujos Completos con Mocks` |
| 6 | plan.md nombres correctos para Paso 4 | plan.md:127 | ✅ | `Estrés y Condiciones de Borde` |
| 7 | plan.md nombres correctos para Paso 5 | plan.md:128 | ✅ | `Seguridad — Hardening` |
| 8 | phase-state.md Paso 4 nombre | phase-state.md:21,195 | ⚠️ | Usa `Tests de Estrés y Robustez` ≠ plan.md |
| 9 | phase-state.md Paso 5 nombre | phase-state.md:22,196 | ⚠️ | Usa `Tests de Seguridad` ≠ plan.md |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | phase-state.md Paso 4 = "Tests de Estrés y Robustez" | plan.md dice "Estrés y Condiciones de Borde". plan.md manda → TESTING.md alineado con plan.md. phase-state.md requiere actualización separada (fuera de este paso). |
| D2 | phase-state.md Paso 5 = "Tests de Seguridad" | plan.md dice "Seguridad — Hardening". plan.md manda → TESTING.md alineado con plan.md. phase-state.md requiere actualización separada. |

---

## 1️⃣ Análisis de Datos

N/A. Paso puramente documentación — sin tablas, migraciones, RLS ni schema.

---

## 2️⃣ Análisis de Código

N/A. Paso puramente documentación — sin funciones, clases, imports ni patrones de código.

---

## 3️⃣ Análisis de Backend

N/A. Paso puramente documentación — sin endpoints, middleware, flujos ni contratos.

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo

```
plan.md (source of truth) → TESTING.md (docs) → developer lee nombres correctos
```

Cadena unidireccional. 3 reemplazos de string. Sin impacto en runtime, tests ni lógica.

### Coherencia

- ❌ `phase-state.md` usa nombres distintos para Paso 4 y 5. Ver D1, D2.
- plan.md corrige TESTING.md para alinear consigo mismo. phase-state.md queda desincronizado.
- **Impacto:** Bajo. phase-state.md es archivo de estado, no guía de testing. Developer confía en TESTING.md + plan.md para ejecución.

### DX & Tooling

```
### Herramienta Propuesta: fap sync-step-names
- **Qué automatiza:** Verifica que nombres de pasos en TESTING.md coinciden con plan.md secciones. Escanea headings `### Paso N:` y compara contra plan.md. Reporta diferencias.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:** `fap sync-step-names --check` (dry-run) o `fap sync-step-names --apply` (auto-fix)
- **Impacto:** Elimina verificación manual post-renombre. Previene desincronización futura.
- **Prioridad:** Baja — paso solo toca 3 líneas. Herramienta útil si hay más renombres.
```

### Gaps

- phase-state.md nombres para Paso 4 y 5 divergen de plan.md. No bloqueante pero arrastra inconsistencia.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DOCS] TESTING.md:66 → `### Paso 3: E2E — Flujos Completos con Mocks`
✅ [DOCS] TESTING.md:72 → `### Paso 4: Estrés y Condiciones de Borde`
✅ [DOCS] TESTING.md:78 → `### Paso 5: Seguridad — Hardening`
✅ [DX] `grep "### Paso 3:" TESTING.md` output exacto
✅ [DX] `grep "### Paso 4:" TESTING.md` output exacto
✅ [DX] `grep "### Paso 5:" TESTING.md` output exacto
✅ [DOCS] Ningún otro heading `### Paso N:` alterado
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| phase-state.md desincronizado con plan.md (Paso 4 y 5) | Baja | plan.md usa nombres distintos a phase-state.md. Paso 3 solo toca TESTING.md. | Documentar en análisis. Ajustar phase-state.md en paso futuro o tarea separada. |
| Renombre parcial — solo algunas líneas corregidas | Baja | Error humano al editar. | Verificar 3 líneas exactas cambiadas. Gate: diff muestra solo 3 cambios. |
| Overflow a otros headings | Baja | Reemplazo global por error. | Usar cambio línea específica, no sed global. Ver con diff. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** sync-step-names | `src/cli/commands/sync_step_names.py` | `def run(check: bool = True, apply: bool = False) -> list[str]` | `src/cli/commands/test_step.py :: app.command()` | DX | Baja | 0.3h | Ninguna | → verificar: `uv run python -m src.cli.main sync-step-names --help` sin error |
| 1 | Renombrar Paso 3 en TESTING.md | `TESTING.md:66` | Antes: `### Paso 3: Validacion de Seguridad Profunda` → Después: `### Paso 3: E2E — Flujos Completos con Mocks` | — | DOCS | Baja | 0.05h | Ninguna | → verificar: `grep -n "### Paso 3:" TESTING.md` → `E2E — Flujos Completos con Mocks` |
| 2 | Renombrar Paso 4 en TESTING.md | `TESTING.md:72` | Antes: `### Paso 4: Hardening de API Publica` → Después: `### Paso 4: Estrés y Condiciones de Borde` | — | DOCS | Baja | 0.05h | Ninguna | → verificar: `grep -n "### Paso 4:" TESTING.md` → `Estrés y Condiciones de Borde` |
| 3 | Renombrar Paso 5 en TESTING.md | `TESTING.md:78` | Antes: `### Paso 5: Tests de Regresion E2E` → Después: `### Paso 5: Seguridad — Hardening` | — | DOCS | Baja | 0.05h | Ninguna | → verificar: `grep -n "### Paso 5:" TESTING.md` → `Seguridad — Hardening` |
| 4 | Verificar diff total | — | — | — | DOCS | Baja | 0.05h | Tareas 1-3 | → verificar: diff muestra solo 3 líneas cambiadas |

**Tiempo total estimado:** 0.5h (0.2h sin DX tooling)

> **Nota:** Tarea 0 (DX) opcional para este paso. Paso 3 tan pequeño que herramienta automatizada agrega más overhead del que ahorra. Priorizar Tareas 1-4 directo.

---

## 🔮 Roadmap

- Sincronizar `phase-state.md` nombres Paso 4 y 5 con `plan.md` — paso aparte o incluido en próximo hotfix.
- `fap sync-step-names` podría integrarse en `fap phase-close` como verificación de consistencia entre docs.
