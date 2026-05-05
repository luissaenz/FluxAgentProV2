# Análisis Unificado — Paso 8: Sincronizar proyecto-config con fase activa

**Fecha:** 2026-05-05
**Paso:** 08-sincronizar-proyecto-config-con-fase-activa
**Fase:** patch_agents
**Origen:** Sugerencia 🟡 validación — Paso 3: Tool Calling Real

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **kimi** | ✅ | 4 | ✅ `config-sync` | ✅ 17 elem, lineas exactas | 4.5 |
| **grok** | ✅ | 3 | ✅ `fap sync-config` | ✅ 8 elem, referencias linea | 4.0 |
| **laguna** | ✅ | 6 | ✅ `fap sync-config` | ✅ 14 elem + git diff + referencias | 4.8 |
| **hy3** | ✅ | 3 | ✅ `fap sync-config` | ⚠️ 5 elem, mínimo detalle | 3.0 |
| **mm2.7** | ✅ | 5 | ❌ (dijo "ninguna") | ⚠️ 6 elem, parcial | 3.0 |
| **ds** | ✅ | 6 | ✅ `fap sync-config` | ✅ 14 elem + git diff + referencias | 4.8 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `phase.current_step` = `"04-flow-execute-con-llm-real"` no refleja último paso completado | **TODOS** | ✅ `proyecto-config.json:120` | → `"06-ExcelWriterTool"` (commit `7827d78`, paso 6 plan.md implementado) |
| 2 | `pipeline.plan_json_steps_total` = `7` no refleja Paso 8 agregado a plan.md | kimi, laguna, ds | ✅ `proyecto-config.json:130` | → `8` |
| 3 | `pipeline.plan_json_steps_pending` = `3` desactualizado | kimi, laguna, ds, grok | ✅ `proyecto-config.json:131` | → `4` (pasos 04, 05, 07, 08 pendientes) |
| 4 | `plan.json` no incluye step 08 | kimi, laguna, ds | ✅ `DEVS/plan.json:6` (solo 7 pasos) | → Agregar step 08 a `plan.json` |
| 5 | `phase-state.md` §2 afirma config tiene `phase_name: "testing"` (ya corregido en `7827d78`) | kimi, laguna, ds | ✅ `proyecto-config.json:119` vs `phase-state.md:124,129,131,358` | → Actualizar phase-state.md §2 referencias obsoletas |
| 6 | `validacion_exists` malinterpretado | mm2.7 vs resto | ✅ `pipeline.validacion_exists: false` correcto | → Se mantiene `false`. mm2.7 confunde validación Paso 7 con Paso 8 |
| 7 | `plan_json_steps_done` malinterpretado | mm2.7 vs resto | ✅ `4` = pasos 1,2,3,6 implementados | → Se mantiene `4`. Paso 7 solo analizado, no implementado |

---

## 1️⃣ Resumen Ejecutivo

Objetivo: Sincronizar `proyecto-config.json` con estado real de fase `patch_agents`. Corregir `current_step`, contadores pipeline, agregar step 08 a `plan.json`, limpiar referencias obsoletas en `phase-state.md`. Desincronización documentada desde commit `64cf7c5` persiste en 4 campos de config. Herramienta DX seleccionada: **`fap sync-config`** (4/6 agentes proponen misma herramienta, voto mayoritario).

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path
1. Ejecutar `fap sync-config --check` → detecta 4 campos desincronizados
2. Ejecutar `fap sync-config --fix` → corrige `current_step`, `plan_json_steps_total`, `plan_json_steps_pending`
3. Agregar manualmente step 08 a `plan.json` (no cubierto por --fix)
4. Actualizar `phase-state.md` §2 referencias obsoletas sobre `phase_name: "testing"`
5. Verificar `ruff check src/ tests/` → 0 errores
6. Verificar `python -c "import json; json.load(open('proyecto-config.json'))"` → parseo válido

### Edge Cases MVP
- `current_step` podría coincidir con nombre de carpeta IMPLEMENTED (naming inconsistency ya documentada)
- `plan.json` podría regenerarse desde `plan.md` en el futuro → edición manual es temporal
- `phase-state.md` tiene múltiples referencias mezcladas (históricas vs activas) → limpiar solo las que afirman estado actual incorrecto

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| Archivo | Tipo de cambio | Descripción | Interfaces clave | Patrón a seguir |
|---|---|---|---|---|
| `proyecto-config.json` | Modificación | Actualizar `phase.current_step`, `pipeline.plan_json_steps_total`, `pipeline.plan_json_steps_pending` | `phase.current_step`: str → `"06-ExcelWriterTool"`; `pipeline.plan_json_steps_total`: int → `8`; `pipeline.plan_json_steps_pending`: int → `4` | Misma estructura JSON, indent 2, sin trailing commas |
| `DEVS/plan.json` | Modificación | Agregar step 08 al array `steps[]` | `{"id":"08","name":"08-sincronizar-proyecto-config-con-fase-activa","status":"pending","depends_on":["01","02","03","04","05","06","07"]}` | Pasos 01-07 existentes en plan.json |
| `DEVS/phase-state.md` | Modificación | Actualizar líneas 124, 129, 131, 358 que afirman config tiene `phase_name: "testing"` | Edición inline de referencias obsoletas | Ediciones inline existentes |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap sync-config
- **Qué automatiza:** Verifica y corrige desincronización entre proyecto-config.json, phase-state.md y plan.md. Detecta drift en phase_name, current_step, pipeline flags.
- **Tipo:** CLI command (Typer)
- **Ubicación:** src/cli/commands/sync_config.py
- **Cómo se usa:**
  - `fap sync-config --check` → exit 0 si sync, exit 1 si drift, reporta discrepancias
  - `fap sync-config --fix` → aplica correcciones automáticas a proyecto-config.json
  - `fap sync-config --dry-run` → muestra cambios sin aplicar
- **Impacto para el usuario final:** Elimina verificación manual cruzada entre 4 archivos. Previene recurrencia de desincronización que ocurrió 3+ veces (commits 64cf7c5, 349d9eb, 7827d78). Agentes downstream reciben fase correcta.
- **El implementador DEBE usarla** para completar las tareas 1-4 del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **current_step = "06-ExcelWriterTool":** Último paso plan.md implementado en commit `349d9eb`. Los agentes proponen `"06-excel-writer-tool"` (kimi) vs `"06-ExcelWriterTool"` (grok, laguna, ds, hy3, mm2.7). Se adopta `"06-ExcelWriterTool"` por votación mayoritaria y consistencia con nombre original del paso.
2. **Correcciones al plan:** Plan.md §Paso 8 define el objetivo correctamente. No hay contradicciones plan vs código — la desincronización está documentada en phase-state.md §2 desde commit `64cf7c5`.
3. **plan_json_steps_done se mantiene en 4:** Paso 7 (Cierre) solo tiene análisis completado, no implementación. mm2.7 propone `6` pero contradice fase-state.md §5 donde Paso 7 figura como "✅ ANÁLISIS COMPLETADO" (no implementado).
4. **validacion_exists se mantiene false:** El archivo `validacion.md` en `IMPLEMENTED/patch_agents/06-ExcelWriterTool/` corresponde a validación de Paso 7, no de Paso 8.
5. **Herramienta DX fusionada:** `fap sync-config` (4/6 agentes) sobre `config-sync` script de kimi (1/6) y "ninguna" de mm2.7 (1/6). Voto mayoritario.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] proyecto-config.json phase.current_step == "06-ExcelWriterTool"
✅ [DATA] proyecto-config.json pipeline.plan_json_steps_total == 8
✅ [DATA] proyecto-config.json pipeline.plan_json_steps_pending == 4
✅ [DATA] proyecto-config.json pipeline.plan_json_steps_done se mantiene == 4
✅ [DATA] plan.json incluye step 08 con status "pending"
✅ [CODE] proyecto-config.json es JSON válido (python -c "import json; json.load(...)")
✅ [CODE] lint 0 post-cambio (ruff check src/ tests/)
✅ [BACKEND] CLI/scripts que consumen config (phase_close.py) leen values correctos
✅ [FULLSTACK] phase-state.md §2 referencias a phase_name: "testing" actualizadas
✅ [DX] Herramienta fap sync-config --check ejecuta sin errores y detecta drift
```

**Funcionales:**
- [ ] `current_step` refleja último paso completado real (06-ExcelWriterTool)
- [ ] Contadores pipeline reflejan estado real de plan.md de 8 pasos
- [ ] `plan.json` contiene todos los pasos definidos en `plan.md`
- [ ] phase-state.md no contiene afirmaciones falsas sobre config actual

**Técnicos:**
- [ ] JSON parseable sin errores
- [ ] Ruff check 0 errores
- [ ] sync-config --check retorna exit 0 post-fix

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap sync-config` CLI (src/cli/commands/sync_config.py) — flags --check/--fix/--dry-run, detecta drift en phase_name/current_step/pipeline, corrige proyecto-config.json | Media | 1h | Ninguna |
| 1 | Actualizar `phase.current_step` a `"06-ExcelWriterTool"` en proyecto-config.json:120 | Baja | 0.1h | Tarea 0 (opcional) |
| 2 | Actualizar `pipeline.plan_json_steps_total` a 8 y `plan_json_steps_pending` a 4 en proyecto-config.json:130-131 | Baja | 0.1h | Tarea 1 |
| 3 | Agregar step 08 a DEVS/plan.json con status "pending", depends_on todos los pasos previos | Baja | 0.2h | Tareas 1-2 |
| 4 | Actualizar phase-state.md §2 líneas 124, 129, 131, 358 para reflejar que `phase_name` ya no es "testing" | Baja | 0.2h | Tareas 1-3 |
| 5 | Verificar JSON parseo + lint 0 + sync-config --check exit 0 | Baja | 0.2h | Tareas 0-4 |
| **TOTAL** | | | **1.8h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `plan.json` desactualizado perpetúa inconsistencia entre plan.md y tracking machine-readable | Alta | plan.json se edita manualmente, no se regenera desde plan.md | Incluir step 08 manualmente ahora. Roadmap: regeneración automática desde plan.md |
| Agentes downstream leen `current_step` incorrecto y toman decisiones sobre paso equivocado | Alta | Cualquier script/agente que lea `current_step` antes del fix obtendrá valor desactualizado | Corregir ahora. sync-config previene recurrencia |
| phase-state.md §2 discrepancias mezclan referencias históricas con estado actual, confundiendo analistas | Media | phase-state.md no se actualizó cuando config se corrigió parcialmente en `7827d78` | Limpiar referencias obsoletas ahora. Separar histórico de activo en roadmap |
| Nuevos pasos en plan.md sin entrada en plan.json | Media | Sin proceso automatizado, la edición manual de plan.json se olvida | Incluir en definition of done de nuevos pasos |
| Naming inconsistente (06-ExcelWriterTool vs 06-excel-writer-tool) | Baja | Convención de slug no está explicita en config | Unificar usando nombre del paso original del plan.md |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Verificar current_step corregido | `python -c "import json; c=json.load(open('proyecto-config.json')); print(c['phase']['current_step'])"` | `06-ExcelWriterTool` |
| TP-2 | Verificar pipeline counters | `python -c "import json; c=json.load(open('proyecto-config.json')); print(c['pipeline']['plan_json_steps_total'], c['pipeline']['plan_json_steps_pending'])"` | `8 4` |
| TP-3 | Verificar plan.json incluye paso 08 | `python -c "import json; p=json.load(open('DEVS/plan.json')); print(any(s['id']=='08' for s in p['steps']))"` | `True` |
| TP-4 | Verificar JSON config válido | `python -c "import json; json.load(open('proyecto-config.json'))"` | Sin excepción |
| TP-5 | Verificar lint 0 | `uv run ruff check src/ tests/` | `0 errores` |

Comando para ejecutar tests: `uv run pytest tests/unit/ -v --timeout=60`

---

## 📊 Calidad de Aportes por Análisis

| Agente | Score | Fortaleza | Debilidad | Veredicto |
|---|---|---|---|---|
| **kimi** | 4.5/5 | Verificación exhaustiva (17 elem). Detectó D-04 (phase_completed fantasma). DX propia (`config-sync`). | Propuesta DX como script standalone vs CLI integrado. | ✅ Aprobado |
| **grok** | 4.0/5 | Clara identificación de 3 discrepancias core. Estimación realista (1.5h). | Solo 8 elem verificados. No detectó D4 (plan.json) ni D5 (phase-state.md stale). | ✅ Aprobado |
| **laguna** | 4.8/5 | Máximo detalle: 14 elem + git diff. 6 discrepancias (D1-D6). Tablas de campos exactas. | Casi idéntico a ds (comparten estructura). | ✅ Aprobado — mejor calidad |
| **hy3** | 3.0/5 | Conciso. DX tool correcta. | Solo 5 elem verificados. Sin tabla de discrepancias detallada. Mínimo análisis de etapas. | ⚠️ Aceptable — le falta profundidad |
| **mm2.7** | 3.0/5 | Detectó 5 discrepancias. | **No propuso DX tool** (viola regla obligatoria). Malinterpretó `validacion_exists` y `plan_json_steps_done`. | ❌ Rechazado — errores de interpretación + falta DX |
| **ds** | 4.8/5 | Idéntico a laguna en estructura y profundidad. 14 elem, 6 discrepancias. | Casi idéntico a laguna (posible derivación). | ✅ Aprobado — mejor calidad |

**Resumen:** laguna y ds aportan la mejor calidad (4.8). kimi aporta profundidad única (D-04). grok sólido pero menos profundo. hy3 funcional pero mínimo. mm2.7 rechazado por omitir DX tool obligatoria y errores de interpretación en contadores.
