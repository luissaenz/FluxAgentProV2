# 🧠 Análisis Técnico — Paso 3: Alinear nombres de pasos en TESTING.md

> **Agente:** glm
> **Fecha:** 2026-05-02
> **Origen:** `plan.md` Paso 3 (Hotfix post-certificación)
> **Tipo:** Corrección documental — desincronización de nombres

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `TESTING.md` existe | glob `TESTING.md` | ✅ VERIFICADO | `D:\Develop\Personal\FluxAgentPro-v2\TESTING.md` — 126 líneas |
| 2 | TESTING.md:66 contiene `### Paso 3: Validacion de Seguridad Profunda` | read TESTING.md:66 | ✅ VERIFICADO | Línea exacta confirmada. Requiere reemplazo. |
| 3 | TESTING.md:72 contiene `### Paso 4: Hardening de API Publica` | read TESTING.md:72 | ✅ VERIFICADO | Línea exacta confirmada. Requiere reemplazo. |
| 4 | TESTING.md:78 contiene `### Paso 5: Tests de Regresion E2E` | read TESTING.md:78 | ✅ VERIFICADO | Línea exacta confirmada. Requiere reemplazo. |
| 5 | TESTING.md:70 descripción Paso 3: `Tests E2E de flujos de produccion con validacion de seguridad.` | read TESTING.md:70 | ❌ DISCREPANCIA | Descripción menciona "validacion de seguridad" → debería describir E2E con mocks. Texto "con validacion de seguridad" hereda del nombre incorrecto. |
| 6 | TESTING.md:76 descripción Paso 4: `Tests de estres (concurrencia) + edge cases.` | read TESTING.md:76 | ✅ VERIFICADO | Descripción alineada con contenido real del Paso 4 (stress tests). No requiere cambio. |
| 7 | TESTING.md:82 descripción Paso 5: `Tests de seguridad: security_guard + escape analysis.` | read TESTING.md:82 | ✅ VERIFICADO | Descripción alineada con contenido real del Paso 5 (SE5.x). No requiere cambio. |
| 8 | plan.md nombre correcto Paso 3 | plan.md:126 | ✅ VERIFICADO | `E2E — Flujos Completos con Mocks` |
| 9 | plan.md nombre correcto Paso 4 | plan.md:127 | ✅ VERIFICADO | `Estrés y Condiciones de Borde` |
| 10 | plan.md nombre correcto Paso 5 | plan.md:128 | ✅ VERIFICADO | `Seguridad — Hardening` |
| 11 | `CHANGELOG.md` contiene los mismos 3 nombres incorrectos | grep `CHANGELOG.md` | ❌ DISCREPANCIA | Líneas 28, 32, 36: `Paso 5 — Tests de Regresion E2E`, `Paso 4 — Hardening de API Publica`, `Paso 3 — Validacion de Seguridad Profunda`. No incluido en scope del plan pero misma desincronización. |
| 12 | `phase-state.md` nombres Paso 4 y 5 | phase-state.md:20-22 | ⚠️ NO VERIFICABLE | Usa `Paso 4: Tests de Estrés y Robustez` y `Paso 5: Seguridad — Hardening`. Diverge de plan.md ("Estrés y Condiciones de Borde"). Coincide parcialmente con IMPLEMENTED folder naming. |
| 13 | `test_step.py` mapeo Paso 3 → archivos correctos | test_step.py:35-37 | ✅ VERIFICADO | Paso 3 → `tests/e2e/test_production_flows.py` (E2E). Correcto. |
| 14 | `test_step.py` mapeo Paso 4 → archivos correctos | test_step.py:38-41 | ✅ VERIFICADO | Paso 4 → `tests/stress/test_concurrency.py` + `test_edge_cases.py`. Correcto. |
| 15 | `test_step.py` mapeo Paso 5 → archivos correctos | test_step.py:42-45 | ✅ VERIFICADO | Paso 5 → `tests/unit/test_security_guard.py` + `test_security_guard_escape.py`. Correcto. |
| 16 | `fap test-step 3` CLI output correcto | test_step.py:147 | ⚠️ NO VERIFICABLE | Hardcodea `Paso 7: Documentacion y Cierre`. Pasos 3-6 usan genérico `Paso {step}: X archivos de test`. Sin nombres hardcodeados para pasos 3-5. |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | TESTING.md:70 descripción Paso 3 contiene "con validacion de seguridad" — hereda del nombre incorrecto. Debería describir E2E con mocks. | Extender corrección: reemplazar descripción por `Tests E2E: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover (E3.3).` Alineado con phase-state.md:20. |
| D2 | CHANGELOG.md líneas 28, 32, 36 tienen los mismos 3 nombres incorrectos. Plan solo corrige TESTING.md. | Fuera de scope. Documentar. Recomendar corrección separada o incluirla como Tarea adicional si el implementador lo considera seguro. |
| D3 | phase-state.md Paso 4 usa "Tests de Estrés y Robustez" vs plan.md "Estrés y Condiciones de Borde". Nombres divergen. | Fuera de scope. phase-state.md no se modifica en este paso. Documentar para corrección futura. La carpeta IMPLEMENTED usa `04-Tests-de-Estres-y-Robustez/` como nombre de folder. |
| D4 | test_step.py no muestra nombres de paso para pasos 3-6. Solo paso 7 tiene nombre hardcodeado. | Sin impacto. Los comandos `fap test-step N` muestran "Paso N: X archivos de test". No hay strings de nombres incorrectos en código. |

---

## 1️⃣ Análisis de Datos

N/A. Paso documental — sin tablas, migraciones, schema ni RLS.

---

## 2️⃣ Análisis de Código

Sin cambios de código.Solo modificación textual en `TESTING.md`.

Análisis de impacto en código:

- **`test_step.py`:** No contiene strings de nombres de pasos (excepto paso 7). Sin impacto.
- **`src/cli/main.py`:** No referencia nombres de pasos. Sin impacto.
- **No hay imports ni funciones** que dependan de los nombres de headings en TESTING.md.

patrones existentes verificados:
- Phase-state.md usa naming distinto para Paso 4 ("Tests de Estrés y Robustez" vs "Estrés y Condiciones de Borde"). Esto es naming de carpeta archivado vs naming de plan — no genera conflicto de código.
- Carpeta `DEVS/IMPLEMENTED/testing/03-E2E-Flujos-Completos-con-Mocks/` sí usa el nombre correcto.

Verificación: nombres incorrectos existen SOLO en archivos `.md` de documentación (TESTING.md, CHANGELOG.md). No hay impacto en código ejecutable.

---

## 3️⃣ Análisis de Backend

N/A. Paso documental — sin endpoints, middleware, flujos ni contratos afectados.

Sin impacto en APIs, auth, ni servicios.

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo

```
plan.md (fuente de verdad)
  ↓ MOCKUP
TESTING.md (guía de testing para developers)
  ↓ LECTURA
Developer ejecuta `fap test-step 3`
  ↓ SIN IMPACTO
Tests E2E corren correctamente (test_step.py mapea por número, no por nombre)
```

Cadena: `plan.md → TESTING.md (nombres headings) → Developer lee nombre → desarrollador asocia paso con contenido`.

El mapeo numérico en `test_step.py` es por **entero** (3 → archivos E2E). Los nombres de heading son Solo display. No hay impacto funcional.

### Coherencia

- ✅ `fap test-step 3` → archivos E2E correctos (test_production_flows.py)
- ✅ `fap test-step 4` → archivos stress correctos (test_concurrency.py + test_edge_cases.py)
- ✅ `fap test-step 5` → archivos security correctos (test_security_guard.py + test_security_guard_escape.py)
- ❌ Nombres en TESTING.md no coinciden con nombres en plan.md → Developer lee nombre incorrecto y asocia contenido equivocado
- ❌ Descripción Paso 3 en TESTING.md dice "validacion de seguridad" cuando debería decir E2E con mocks
- ❌ CHANGELOG.md tiene los mismos 3 nombres incorrectos (fuera de scope)

### Alineación con plan

plan.md especifica exactamente 3 reemplazos en TESTING.md. El paso es simple y directo. No hay riesgo de que la corrección rompa funcionalidad.

### Gaps

1. **TESTING.md:70 descripción Paso 3** menciona "validacion de seguridad" — si Solo se corrigen headings, la descripción queda desalineada con el nuevo nombre "E2E — Flujos Completos con Mocks". Developer lee heading corregido pero descripción habla de seguridad. Recomendación: corregir descripción también.
2. **CHANGELOG.md** tiene 3 líneas con nombres incorrectos (28, 32, 36). Plan no lo incluye pero la inconsistencia permanece tras el fix.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap check-docs
- **Qué automatiza:** Verifica consistencia de nombres de pasos entre TESTING.md, CHANGELOG.md y plan.md. Escanea headings `### Paso N:` y compara contra fuente de verdad.
- **Tipo:** Comando CLI (Typer)
- **Cómo se usa:** `fap check-docs` → lista discrepancias. `fap check-docs --fix` → auto-corrige contra plan.md
- **Impacto para el usuario final:** Previene desincronización futura entre docs de testing y plan. Elimina verificación manual.
- **Prioridad:** Para este paso → Tarea 0 opcional. Paso Solo toca 3 líneas + 1 descripción. Overhead de crear comando > beneficio para 4 edits. Justificado Solo si hay más renombres en futuro.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DOCS] TESTING.md:66 → `### Paso 3: E2E — Flujos Completos con Mocks`
✅ [DOCS] TESTING.md:72 → `### Paso 4: Estrés y Condiciones de Borde`
✅ [DOCS] TESTING.md:78 → `### Paso 5: Seguridad — Hardening`
✅ [DOCS] TESTING.md:70 → descripción Paso 3 corregida: menciona E2E con mocks, no "validacion de seguridad"
✅ [DX] `grep -n "### Paso 3:" TESTING.md` output contiene `E2E — Flujos Completos con Mocks`
✅ [DX] `grep -n "### Paso 4:" TESTING.md` output contiene `Estrés y Condiciones de Borde`
✅ [DX] `grep -n "### Paso 5:" TESTING.md` output contiene `Seguridad — Hardening`
✅ [DOCS] Ningún otro heading `### Paso N:` alterado (0, 1, 2, 6, 7 permanecen igual)
✅ [DOCS] `fap test-step 3` sigue mapeando a tests/e2e/test_production_flows.py
✅ [DOCS] `fap test-step 4` sigue mapeando a tests/stress/ correctos
✅ [DOCS] `fap test-step 5` sigue mapeando a tests/unit/test_security_guard*.py correctos
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Descripción Paso 3 queda desalineada con nombre corregido | Media | TESTING.md:70 dice "validacion de seguridad". Si Solo se cambia heading, descripción contradice nombre nuevo. | Incluir corrección de descripción línea 70 como Tarea adicional. Verificar con diff. |
| CHANGELOG.md permanece con nombres incorrectos | Baja | Plan no incluye CHANGELOG.md en scope. Developer lee CHANGELOG y ve nombres inconsistentes vs TESTING.md corregido. | Corregir CHANGELOG.md como Tarea adicional. 3 reemplazos simples. |
| phase-state.md Paso 4 diverge de plan.md ("Tests de Estrés y Robustez" vs "Estrés y Condiciones de Borde") | Baja | Carpeta IMPLEMENTED usa "Estres-y-Robustez". Nombres de fase archivada no afectan ejecución. | Documentar. Corregir en paso futuro si se requiere consistencia total. No bloqueante. |
| Edición accidental de otros headings | Baja | Reemplazo global por error | Usar reemplazo línea específica. Verificar con diff que Solo 4 líneas cambiadas (3 headings + 1 descripción). |
| Test `fap test-step` se rompe | Muy Baja | Nombres de heading Solo son display. Código mapea por número entero. | Nulo. `test_step.py` Stephens_TEST_FILES usa enteros como key. Sin strings de nombres de pasos. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica:** 1 tarea = 1 artefacto = 1 cambio mínimo. Implementador no decide nada.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** check-docs (OPCIONAL) | `src/cli/commands/check_docs.py` | `def check(step: int = None) -> list[dict]` — escanea headings y compara contra plan.md | `src/cli/commands/test_step.py :: app.command()` | DX | Media | 0.5h | Ninguna | → verificar: `uv run python -m src.cli.main check-docs` ejecuta sin error |
| 1 | Renombrar heading Paso 3 en TESTING.md | `TESTING.md:66` | Antes: `### Paso 3: Validacion de Seguridad Profunda` → Después: `### Paso 3: E2E — Flujos Completos con Mocks` | — | DOCS | Baja | 0.02h | Ninguna | → verificar: `grep -n "### Paso 3:" TESTING.md` output contiene `E2E — Flujos Completos con Mocks` |
| 2 | Corregir descripción Paso 3 en TESTING.md | `TESTING.md:70` | Antes: `Tests E2E de flujos de produccion con validacion de seguridad.` → Después: `Tests E2E: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover (E3.3).` | — | DOCS | Baja | 0.02h | Ninguna | → verificar: `grep -n "validacion de seguridad" TESTING.md` retorna vacío |
| 3 | Renombrar heading Paso 4 en TESTING.md | `TESTING.md:72` | Antes: `### Paso 4: Hardening de API Publica` → Después: `### Paso 4: Estrés y Condiciones de Borde` | — | DOCS | Baja | 0.02h | Ninguna | → verificar: `grep -n "### Paso 4:" TESTING.md` output contiene `Estrés y Condiciones de Borde` |
| 4 | Renombrar heading Paso 5 en TESTING.md | `TESTING.md:78` | Antes: `### Paso 5: Tests de Regresion E2E` → Después: `### Paso 5: Seguridad — Hardening` | — | DOCS | Baja | 0.02h | Ninguna | → verificar: `grep -n "### Paso 5:" TESTING.md` output contiene `Seguridad — Hardening` |
| 5 | Corregir nombres en CHANGELOG.md | `CHANGELOG.md:28,32,36` | Línea 28: `#### Paso 5 — Tests de Regresion E2E` → `#### Paso 5 — Seguridad — Hardening`. Línea 32: `#### Paso 4 — Hardening de API Publica` → `#### Paso 4 — Estrés y Condiciones de Borde`. Línea 36: `#### Paso 3 — Validacion de Seguridad Profunda` → `#### Paso 3 — E2E — Flujos Completos con Mocks` | TESTING.md headings corregidos en Tareas 1, 3, 4 | DOCS | Baja | 0.02h | Tareas 1,3,4 | → verificar: `grep -c "Validacion de Seguridad\|Hardening de API\|Tests de Regresion" CHANGELOG.md` retorna 0 |
| 6 | Verificar diff total — Solo líneas esperadas cambiadas | — | — | — | DOCS | Baja | 0.03h | Tareas 1-5 | → verificar: `git diff TESTING.md CHANGELOG.md` muestra exactamente 7 líneas cambiadas (4 en TESTING.md + 3 en CHANGELOG.md). Ninguna otra línea alterada. |

> **Nota sobre Tarea 0:** DX tooling opcional. Paso toca 7 líneas. Overhead de crear comando > beneficio. Priorizar Tareas 1-6 directo. Incluir Solo si hay proyección de más renombres futuros.

> **Nota sobre Tarea 5 (CHANGELOG.md):** El plan original Solo incluye TESTING.md. Tarea 5 extiende scope a CHANGELOG.md porque las mismas 3 inconsistencias existen ahí. Si el implementador prefiere ceñirse al plan exacto, puede omitir Tarea 5. La inconsistencia documental permanecerá pero es bajo riesgo.

**Tiempo total estimado:** 0.15h (sin DX tooling: 0.13h)

---

## 🔮 Roadmap (NO implementar ahora)

- Corregir nombres en `phase-state.md` líneas 20-22 para alinear con plan.md. Paso aparte — no bloquea funcionamiento.
- `fap check-docs` integrado en `fap phase-close` como verificación automática de consistencia documental entre TESTING.md, CHANGELOG.md y plan.md.
- Estandarizar naming de pasos: plan.md, phase-state.md, TESTING.md, CHANGELOG.md y carpetas IMPLEMENTED en un Solo lugar (proyecto-config.json o diccionario centralizado).