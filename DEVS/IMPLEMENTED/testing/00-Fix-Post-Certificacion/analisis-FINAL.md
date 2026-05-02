# 🏛️ ANÁLISIS UNIFICADO FINAL — Paso 3: Alinear nombres de pasos en TESTING.md

> **Versión:** v3.2 — Hotfix post-certificación Fase VI (testing)
> **Fecha:** 2026-05-02
> **Agentes unificados:** ds · glm · kimi · qwen
> **Origen:** `DEVS/plan.md` Paso 3 (Tarea 3.1)
> **Destino:** `DEVS/IN_PROGRESS/analisis-FINAL.md`

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:-------|:---------------:|:------------------------:|:------------:|:----------------:|:-----------:|
| **ds** | ✅ | 2 (phase-state.md Paso 4/5 divergen) | ✅ `fap sync-step-names` | ✅ Líneas exactas, 9 items verificados | 3.5 |
| **glm** | ✅ | 4 (D1-D4: descripción TESTING.md:70 + CHANGELOG.md + phase-state + test_step.py) | ✅ `fap check-docs` | ✅ 16 items — más exhaustivo. Detectó descripción + CHANGELOG que nadie más vio | **4.8** |
| **kimi** | ✅ | 2 (phase-state.md Paso 4/5 divergen) | ✅ `validate_docs.py` script | ✅ Estructura 4 etapas clara, 12 items verificados | 4.0 |
| **qwen** | ✅ | 2 (plan.md sin Paso 5 explícito; plan.md nombres ≠ fase real) | ✅ `sync_step_names.py` script | ✅ Insight crítico: plan.md hotfix names ≠ carpetas reales. Ruido: items irrelevantes de otros pasos | 4.0 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|-------------|---------|-------------------------|------------|
| 1 | **plan.md Tarea 3.1 propone nombres para Pasos 4-5 que NO coinciden con la fase real.** plan.md dice Paso 4 = "Estrés y Condiciones de Borde", Paso 5 = "Seguridad — Hardening". Pero carpeta IMPLEMENTED `04-Tests-de-Estres-y-Robustez/` y `05-Tests-de-Seguridad/` + phase-state.md muestran nombres distintos. | **qwen** (insight principal), **ds/glm/kimi** (documentaron divergencia) | ✅ `DEVS/IMPLEMENTED/testing/04-Tests-de-Estres-y-Robustez/` y `DEVS/IMPLEMENTED/testing/05-Tests-de-Seguridad/` existen + `DEVS/phase-state.md:21-22` | Usar **phase-state.md + carpetas IMPLEMENTED** como fuente de verdad. plan.md hotfix contiene error de naming para Pasos 4 y 5. Código real gana. |
| 2 | **TESTING.md:70 descripción Paso 3 incorrecta** — dice "Tests E2E de flujos de produccion con validacion de seguridad." heredando del nombre viejo. | **glm** (único) | ✅ `TESTING.md:70` leída y confirmada | Corregir descripción: `Tests E2E: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover (E3.3).` |
| 3 | **CHANGELOG.md líneas 28, 32, 36 tienen mismos nombres incorrectos.** plan.md no lo incluye en scope. | **glm** (único) | ✅ `CHANGELOG.md:28,32,36` leídas y confirmadas | Extender scope: corregir CHANGELOG.md. Misma desincronización, mismo fix. 3 reemplazos. |
| 4 | **phase-state.md Paso 4 = "Tests de Estrés y Robustez", Paso 5 = "Tests de Seguridad — Hardening".** Plan.md hotfix no actualizó phase-state.md. | **ds, glm, kimi, qwen** (todos) | ✅ `DEVS/phase-state.md:21-22` | phase-state.md NO se modifica en este paso. Documentar para futura sincronización. phase-state.md ya está correcto para la fase real. |
| 5 | **plan.md no tiene sección explícita "Paso 5".** Salta de Paso 4 a "Criterios de Aceptación MVP". La tabla Tarea 3.1 define el reemplazo pero no hay heading Paso 5 en plan.md. | **qwen** (único) | ✅ `DEVS/plan.md` leído completo. Sección §Paso 4 → §Criterios sin §Paso 5 | Sin impacto. La tabla Tarea 3.1 es suficiente como especificación de reemplazo. No requiere acción. |
| 6 | **test_step.py no usa nombres de pasos (solo números).** Sin riesgo de desincronización funcional. | **glm** (verificación test_step.py:35-45), **kimi** (test_step.py:21-50) | ✅ `src/cli/commands/test_step.py:21-50` — `STEP_TEST_FILES` indexado por int | Confirmado: sin impacto. Nombres son solo display. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Corregir desincronización de nombres de pasos en TESTING.md contra la fuente de verdad real (phase-state.md + carpetas IMPLEMENTED).

**Correcciones críticas al plan:** plan.md Tarea 3.1 propone nombres incorrectos para Pasos 4 y 5. Usa "Estrés y Condiciones de Borde" y "Seguridad — Hardening" cuando la fase real archivó "Tests de Estrés y Robustez" y "Tests de Seguridad — Hardening". Se corrige TESTING.md contra fase real, no contra plan.md erróneo.

**Herramienta DX seleccionada:** `fap sync-step-names` — fusión de propuestas ds (nombre) + glm (scope multi-doc: TESTING.md + CHANGELOG.md) + kimi (validación) + qwen (source configurable). Ver §3.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path
1. Plan.md detecta nombres incorrectos en TESTING.md (Paso 3-5)
2. Análisis unificado resuelve que fuente de verdad real = phase-state.md + carpetas IMPLEMENTED
3. Se corrigen 3 headings en TESTING.md (líneas 66, 72, 78)
4. Se corrige 1 descripción en TESTING.md (línea 70)
5. Se corrigen 3 entradas en CHANGELOG.md (líneas 28, 32, 36)
6. Se crea herramienta DX `fap sync-step-names` para prevenir recurrencia
7. Diff muestra exactamente 7 líneas cambiadas (4 TESTING.md + 3 CHANGELOG.md)

### Edge Cases MVP
- **Descripción desalineada:** Si solo se cambian headings, línea 70 contradice heading nuevo de Paso 3 → corregir ambas
- **CHANGELOG.md ignorado:** Si no se corrige, inconsistencia documental persiste post-fix → incluir en scope
- **Phase-state.md no se toca:** Es archivo de estado, no guía de testing. Su divergencia con plan.md es problema separado

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| Ruta real | Tipo cambio | Descripción | Interfaces clave | Patrón a seguir |
|-----------|-------------|-------------|-----------------|-----------------|
| `TESTING.md` (raíz) | Modificación | 3 headings + 1 descripción corregidos | `### Paso N: [nombre]` | Formato markdown H3 existente |
| `CHANGELOG.md` (raíz) | Modificación | 3 entries corregidos (líneas 28, 32, 36) | `#### Paso N — [nombre]` | Formato markdown H4 existente |
| `src/cli/commands/sync_step_names.py` | Creación | Herramienta DX CLI para validar/fix nombres de pasos multi-doc | `def run(check: bool, fix: bool, source: str) -> int` | `src/cli/commands/perf_check.py` — patrón Typer `app.command()` |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap sync-step-names
- **Qué automatiza:** Verifica/corrige nombres de pasos en TESTING.md y CHANGELOG.md contra fuente de verdad configurable (plan.md o phase-state.md). Escanea headings `### Paso N:` y `#### Paso N —` y compara.
- **Tipo:** CLI command (Typer)
- **Ubicación:** `src/cli/commands/sync_step_names.py`
- **Cómo se usa:**
  - `fap sync-step-names --check` → dry-run: lista discrepancias, exit 0 si ok, 1 si drift
  - `fap sync-step-names --fix` → aplica correcciones a TESTING.md + CHANGELOG.md
  - `fap sync-step-names --source phase-state` → usa phase-state.md como verdad (default)
  - `fap sync-step-names --source plan` → usa plan.md como verdad
- **Impacto para el usuario final:** Elimina verificación manual de 126+ líneas. Previene desincronización futura. CI puede fallar si docs drift.
- **El implementador DEBE usarla** para verificar pre/post fix que 0 discrepancias.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Fuente de verdad = phase-state.md + carpetas IMPLEMENTED:** plan.md hotfix Tarea 3.1 tiene error en nombres Pasos 4-5. Código real (carpetas archivadas) gana.
2. **DX tool ubicada en `src/cli/commands/` no `scripts/`:** Consistencia con resto de herramientas fap. ds/kimi/qwen propusieron scripts, pero glm propuso CLI Typer — más integrado con ecosistema existente.
3. **Scope extendido a CHANGELOG.md:** glm detectó desincronización idéntica en CHANGELOG.md. Incluir en mismo fix — mismo root cause, mismo remedio.
4. **Correcciones al plan:**
   - ⚠️ El plan dice Paso 4 = "Estrés y Condiciones de Borde" pero la fase real usó "Tests de Estrés y Robustez" (carpeta `04-Tests-de-Estres-y-Robustez/`). Se implementa nombre real de la fase.
   - ⚠️ El plan dice Paso 5 = "Seguridad — Hardening" pero la fase real usó "Tests de Seguridad — Hardening" (phase-state.md:22) con carpeta `05-Tests-de-Seguridad/`. Se implementa "Tests de Seguridad — Hardening".
   - ⚠️ El plan no incluye CHANGELOG.md en scope. Se extiende para cubrir desincronización documental completa.
   - ⚠️ El plan no menciona corrección de descripción línea 70. Se incluye para consistencia.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DOCS] TESTING.md:66 → `### Paso 3: E2E — Flujos Completos con Mocks`
✅ [DOCS] TESTING.md:70 → descripción corregida: `Tests E2E: Degraded MCP (E3.1), Approval Gate HITL (E3.2), Multi-step Handover (E3.3).`
✅ [DOCS] TESTING.md:72 → `### Paso 4: Tests de Estrés y Robustez`
✅ [DOCS] TESTING.md:78 → `### Paso 5: Tests de Seguridad — Hardening`
✅ [DOCS] CHANGELOG.md:28 → `#### Paso 5 — Tests de Seguridad — Hardening`
✅ [DOCS] CHANGELOG.md:32 → `#### Paso 4 — Tests de Estrés y Robustez`
✅ [DOCS] CHANGELOG.md:36 → `#### Paso 3 — E2E — Flujos Completos con Mocks`
✅ [DX] `fap sync-step-names --check` ejecuta sin errores y reporta 0 discrepancias post-fix
✅ [DOCS] Ningún otro heading `### Paso N:` o `#### Paso N —` alterado (Pasos 0,1,2,6,7 intactos)
```

**Funcionales:**
- [ ] TESTING.md headings Pasos 3-5 corregidos contra fase real
- [ ] CHANGELOG.md entries Pasos 3-5 corregidos contra fase real
- [ ] Descripción Paso 3 alineada con contenido real (E2E mocks, no seguridad)

**Técnicos:**
- [ ] `fap sync-step-names --check --source phase-state` → exit 0 (0 discrepancias)
- [ ] `fap sync-step-names --fix` → modifica solo archivos esperados
- [ ] `git diff TESTING.md CHANGELOG.md` → exactamente 7 líneas cambiadas

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|-------|:-----------:|:-----------:|:------------:|
| 0 | **DX & Tooling:** `fap sync-step-names` — comando Typer en `src/cli/commands/sync_step_names.py`. Escanea headings en TESTING.md + CHANGELOG.md. Compara contra phase-state.md o plan.md. Flags `--check`/`--fix`/`--source`. | Media | 0.5h | Ninguna |
| 1 | Corregir heading Paso 3 en TESTING.md:66 | Baja | 0.02h | Tarea 0 (dogfooding) |
| 2 | Corregir descripción Paso 3 en TESTING.md:70 | Baja | 0.02h | Tarea 0 |
| 3 | Corregir heading Paso 4 en TESTING.md:72 | Baja | 0.02h | Tarea 0 |
| 4 | Corregir heading Paso 5 en TESTING.md:78 | Baja | 0.02h | Tarea 0 |
| 5 | Corregir CHANGELOG.md:28 (Paso 5) | Baja | 0.02h | Tarea 0 |
| 6 | Corregir CHANGELOG.md:32 (Paso 4) | Baja | 0.02h | Tarea 0 |
| 7 | Corregir CHANGELOG.md:36 (Paso 3) | Baja | 0.02h | Tarea 0 |
| 8 | Verificación final: `fap sync-step-names --check --source phase-state` → exit 0 | Baja | 0.02h | Tareas 0-7 |
| **TOTAL** | | | **0.64h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usarla para verificar pre/post fix.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|--------|:---------:|-------|------------|
| plan.md hotfix usa nombres que no coinciden con fase real archivada | Media | plan.md Tarea 3.1 propone "Estrés y Condiciones de Borde" y "Seguridad — Hardening" pero carpetas reales dicen otra cosa | Resuelto en §4: usar fase real. Documentar corrección al plan. |
| Phase-state.md queda con nombres divergentes del plan.md hotfix | Baja | Paso 3 no modifica phase-state.md. Nombres de fase archivada vs hotfix difieren. | No requiere acción. phase-state.md es registro histórico. Documentar para futura sincro. |
| Edición accidental de otros headings | Baja | Reemplazo global por error | Usar cambio línea específica. Verificar diff = solo 7 líneas. |
| DX tooling overhead > beneficio para paso de 7 líneas | Baja | Paso documental pequeño | Herramienta se amortiza en futuros pasos. Previene recurrencia. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|----|------|-------|-----------------|
| TP-1 | `fap sync-step-names --check --source phase-state` post-fix | Comando CLI | Exit 0. Output: "0 discrepancias encontradas." |
| TP-2 | `fap sync-step-names --check --source plan` post-fix | Comando CLI | Exit 1. Output: Paso 4 y 5 discrepan (plan.md name ≠ fase real). |
| TP-3 | `fap sync-step-names --fix --dry-run` | Comando CLI | Lista cambios propuestos sin modificar archivos. |
| TP-4 | `grep -c "Validacion de Seguridad\|Hardening de API\|Tests de Regresion" TESTING.md CHANGELOG.md` | Shell | Retorna 0 matches en ambos archivos. |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60`

---

## 📊 Calidad de Aportes por Agente

| Agente | Fortaleza | Debilidad | Aporte neto al FINAL |
|--------|-----------|-----------|---------------------|
| **ds** | Evaluación limpia, 9 verificaciones precisas. Propuesta DX con nombre sólido. | No detectó descripción incorrecta ni CHANGELOG. Sin insight sobre error del plan. | **3.5/5** — Correcto pero superficial. Base sólida, sin hallazgos profundos. |
| **glm** | ✅ **Mejor agente.** 16 verificaciones. Único en detectar D1 (descripción TESTING.md:70) y D3 (CHANGELOG.md). Más exhaustivo en cobertura de archivos (test_step.py, CHANGELOG.md). | Propuesta DX más genérica ("check-docs" vs "sync-step-names"). Sin embargo, scope multi-doc correcto. | **4.8/5** — Dominante. Hallazgos exclusivos que elevan calidad del FINAL. |
| **kimi** | Estructura 4 etapas más clara. Métrica de calidad al final. DX script `validate_docs.py` bien especificado con pseudo-interfaz. | No detectó descripción ni CHANGELOG. Propuesta script-only (no CLI integrado). | **4.0/5** — Sólido y bien estructurado. Le falta profundidad de glm. |
| **qwen** | ✅ **Insight crítico:** plan.md hotfix names no son fuente de verdad válida para Pasos 4-5. Verificó contra carpetas IMPLEMENTED. | Items de verificación contaminados con otros pasos (baseline.py, registry.py). Propuesta usa phase-state.md como source pero no integra CHANGELOG. | **4.0/5** — Insight decisivo que cambió la resolución del FINAL. Sin él, habríamos copiado nombres erróneos del plan. |
