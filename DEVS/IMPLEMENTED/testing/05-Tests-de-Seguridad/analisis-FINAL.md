# 🏛️ Análisis FINAL Unificado — Paso 5: Seguridad — Hardening

**Fase:** VI — testing | **Paso:** 5 — Seguridad | **Fecha:** 2026-05-01
**Fuentes:** `analisis-5-ds.md`, `analisis-5-glm.md`, `analisis-5-kimi2.6.md`, `analisis-5-minim2.7.md`

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **ds** | ✅ 20/20 items | 4 (D1-D4) | ✅ `fap security-audit` | ✅ file:line preciso | **4.5** |
| **glm** | ✅ 22/22 items | 6 (D1-D6) | ✅ `fap test-security` | ✅ file:line preciso + hallazgos extras | **4.8** |
| **kimi2.6** | ✅ 18/18 items | 4 (D1-D4) | ✅ `fap bundle-sec-check` | ✅ con script verify_sec.py | **4.3** |
| **minim2.7** | ❌ 16/17 (error: afirma SE5.1-SE5.12 existen cuando NO) | 3 (D1-D3) | ❌ `security-diagnostic` (básico) | ✅ parcial | **3.5** |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **Plan v3.1: vuln `__import__` en líneas 142/221.** Plan dice inyección directa. Código actual usa `_restricted_import` con allowlist. VULNERABILIDAD YA FIJADA. | ds, glm, kimi2.6, minim2.7 | ✅ `security_guard.py:126-159` | Tests SE5.13-SE5.16 verifican fix. NO re-fixear. Documentar como fix pre-existente. |
| 2 | **SE5.1-SE5.12 no existen.** `test_security_guard.py` NO tiene tests para subprocess, shutil, ctypes, socket, gc, inspect, requests, `__import__()` call, `compile()`, `exec()`, async. | ds, glm, kimi2.6 | ✅ `test_security_guard.py:21-95` | Implementar 12 tests nuevos en archivo existente. ⚠️ minim2.7 erróneamente afirma que existen (fue corregido). |
| 3 | **`test_security_guard_escape.py` no existe.** SE5.17-SE5.18 no implementados. | ds, glm, kimi2.6, minim2.7 | ✅ No existe | Crear archivo con 2 tests de escape. |
| 4 | **SE5.18 hex payload inválido.** `\x69\x6d\x70\x6f\x72\x74\x20\x6f\x73` no es Python válido → SyntaxError directo. Bypass real requiere `exec(hex_decoded)` o `compile(hex_decoded)`. | ds | ✅ SyntaxError directo confirmado | SE5.18 debe testear hex-decoded + exec/compile como bypass, NO hex literal como código. |
| 5 | **`run.py:93` — VULNERABILIDAD ACTIVA.** `safe_env["__import__"] = __import__` inyecta `__import__` real sin restricción. Bypass completo de SecurityGuard desde CLI. | glm | ✅ `src/cli/commands/run.py:93` | **FIX OBLIGATORIO:** Reemplazar con `_create_safe_builtins()` de SecurityGuard. Tarea 5. |
| 6 | **`local_executor.py:51` — VULNERABILIDAD ACTIVA.** `exec(code, {"__builtins__": safe_builtins}, loc)` usa `safe_builtins` de RestrictedPython directamente, SIN `_restricted_import`. | glm | ✅ `src/services/local_executor.py:51` | **FIX OBLIGATORIO:** Usar `SecurityGuard.execute()` o `_create_safe_builtins()`. Tarea 6. |
| 7 | **Suite total: 489 tests.** Plan dice 425, phase-state dice 455. Real: 489. Discrepancia de +64 vs plan. | kimi2.6 | ✅ `pytest --co -q tests/` | Re-baseline obligatorio antes de gate "+N tests". Usar 489 como base real. |
| 8 | **`FORBIDDEN_MODULES` tiene 17 módulos.** Plan lista 11. Código agregó: urllib, http, ftplib, httpx, aiohttp, urllib3. | minim2.7 | ✅ `security_guard.py:19-41` | Código más restrictivo que plan. Discrepancia favorable. Documentar. |
| 9 | **SE5.13-SE5.16 YA EXISTEN** en `test_security_guard.py:101-126`. No duplicar. Son tests de regresión, no diagnóstico de bug activo. | ds, minim2.7 | ✅ `test_security_guard.py:101-126` | Verificar pass en Tarea 4. NO recrear tests. |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Hardening de `SecurityGuard` sandbox. Implementar 14 tests unitarios faltantes (SE5.1-SE5.12, SE5.17-SE5.18), verificar 4 tests de regresión existentes (SE5.13-SE5.16), y corregir 2 vulnerabilidades activas fuera de `security_guard.py`.
- **Correcciones críticas al plan:** (1) Vulnerabilidad `__import__` en `security_guard.py` YA FUE FIJADA — no re-fixear. (2) GLM descubrió 2 vulnerabilidades activas en `run.py:93` y `local_executor.py:51` que el plan no menciona. (3) Suite actual 489 tests ≠ 425 del plan. (4) SE5.18 hex payload como está escrito en plan es syntax-invalid.
- **Decisión DX:** Fusionar propuesta de ds (`fap security-audit` con categorías + JSON) con patrón existente `fap test-step 5`. Nombre final: `fap security-audit` con alias en `fap test-step 5`.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Implementador corre `fap security-audit` → reporta 0/18 pass (baseline antes de escribir tests)
2. Agrega SE5.1-SE5.10 a `test_security_guard.py` (imports prohibidos + calls prohibidos)
3. Agrega SE5.11-SE5.12 a `test_security_guard.py` (async system/non-system)
4. Verifica SE5.13-SE5.16 pasan (regresión: fix `_restricted_import` funciona)
5. Crea `test_security_guard_escape.py` con SE5.17-SE5.18 (escape attempts)
6. Fix `run.py:93` — reemplazar `__import__` crudo por `_restricted_import`
7. Fix `local_executor.py:51` — usar `SecurityGuard.execute()` o `_create_safe_builtins()`
8. Ejecuta `fap security-audit` → 18/18 pass. Lint 0 errores.

### Edge Cases MVP

- SE5.11: `async def` en `is_system=False` → RestrictedPython lanza SyntaxError ≠ SecurityError. Test debe capturar ambos.
- SE5.12: `async def` en `is_system=True` → bypass RestrictedPython, `validate_skill()` retorna True.
- SE5.18: Hex-decoded string + exec/compile debe ser bloqueado. Hex literal solo = SyntaxError directo (no es bypass real).
- Fix `run.py:93`: Asegurar que modo `--danger-no-sandbox` siga funcionando para debugging.
- Fix `local_executor.py:51`: Verificar que `LocalExecutor` sigue ejecutando código válido (io/zipfile/json/math).

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| # | Ruta real | Tipo cambio | Descripción | Interfaces clave | Patrón |
|---|---|---|---|---|---|
| SG-1 | `tests/unit/test_security_guard.py` | Modificación | +12 tests (SE5.1-SE5.12). Usar fixture `guard()` existente. | `guard.validate_skill(code)`, `guard.execute(code)`, `pytest.raises(SecurityError)` | Tests unitarios puros, patrón existente líneas 34-95 |
| SG-2 | `tests/unit/test_security_guard_escape.py` | Creación | +2 tests (SE5.17-SE5.18). Importar `guard` fixture del conftest o crear inline. | `guard.validate_skill()`, `guard.execute()` con `SecurityGuard(is_system=False)` | Archivo nuevo, seguir naming `test_*.py`, patrón de `test_security_guard.py` |
| SG-3 | `src/cli/commands/run.py` | Modificación | Línea 93: reemplazar `safe_env["__import__"] = __import__` con versión restringida. | `SecurityGuard._create_safe_builtins()` o importar `_restricted_import` | Seguridad: no inyectar `__import__` real en sandbox |
| SG-4 | `src/services/local_executor.py` | Modificación | Línea 51: reemplazar exec directo con `SecurityGuard.execute()` | `SecurityGuard(timeout_seconds=30).execute(code)` | Patrón consistente con `import_service.py` y `bundle_manager.py` |
| SG-5 | `src/cli/commands/security_audit.py` | Creación | Comando `fap security-audit`. Ejecuta todos SE5.x con `--category` y `--json`. | Typer command, `pytest.main()` con filtros | Patrón de `src/cli/commands/test_step.py` |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap security-audit
- **Qué automatiza:** Ejecuta TODOS los tests de seguridad (SE5.1-SE5.18) con un solo comando. Reporta breakdown por categoría y output JSON para CI.
- **Tipo:** CLI command (Typer, extensión de `fap`)
- **Ubicación:** `src/cli/commands/security_audit.py`
- **Cómo se usa:**
  ```bash
  fap security-audit                          # corre todos SE5.x
  fap security-audit --category imports       # solo SE5.1-SE5.7
  fap security-audit --category calls         # solo SE5.8-SE5.10
  fap security-audit --category async         # solo SE5.11-SE5.12
  fap security-audit --category escape        # solo SE5.17-SE5.18
  fap security-audit --category regresion     # solo SE5.13-SE5.16
  fap security-audit --json                   # output JSON para CI
  fap test-step 5                             # alias: mismo comportamiento
  ```
- **Impacto para el usuario final:** Desarrolladores de bundles no necesitan conocer los 18 tests individuales. Un comando verifica que su código pasará el sandbox. CI puede integrar `--json` para gates automáticos.
- **El implementador DEBE usarla** para completar las tareas 1-N del paso (dogfooding obligatorio).
```

---

## 4️⃣ Decisiones Tecnológicas

1. **No fixear `security_guard.py`.** Vulnerabilidad `__import__` líneas 142/221 ya corregida con `_restricted_import()` vía `_create_safe_builtins()`. Código actual es seguro. Tests SE5.13-SE5.16 son regresión, no diagnóstico.
2. **`run.py:93` requiere fix.** Inyección directa de `__import__` real en CLI sandbox. Usar `SecurityGuard._create_safe_builtins()` como reemplazo.
3. **`local_executor.py:51` requiere fix.** Exec directo con `safe_builtins` sin `_restricted_import`. Reemplazar con `SecurityGuard.execute()` o wrapper.
4. **SE5.18 redefinido.** Plan original propone hex literal inválido como código. Implementar: hex-decode string → exec/compile → debe ser bloqueado.
5. **Tooling DX fusionado.** Se adopta `fap security-audit` de ds (categorías + JSON) integrado en patrón `fap test-step 5` de glm. `fap bundle-sec-check` de kimi se difiere a roadmap.
6. **Re-baseline 489 tests.** Plan (425) y phase-state (455) están desactualizados. Gate de "+N tests" debe usar 489 como baseline.
7. **minim2.7 corregido.** Afirmó erróneamente que SE5.1-SE5.12 existen en `test_security_guard.py`. No existen. Implementación debe agregarlos.
8. **Edición: `test_security_guard.py` expandido en mismo archivo.** NO crear `test_security_guard_expanded.py` (como propone minim2.7). Seguir patrón de archivo único existente.

### Correcciones al plan

- ⚠️ El plan v3.1 dice: "Vulnerabilidad `__import__` en líneas 142/221, fix requerido" → **Código real ya tiene fix vía `_restricted_import()`**. No aplicar fix.
- ⚠️ El plan v3.1 dice: "18 tests nuevos" → **Realidad: 14 nuevos + 4 ya existen (SE5.13-SE5.16)**. Ajustar conteo.
- ⚠️ El plan v3.1 dice "Suite actual: 425 tests" → **Realidad: 489 tests**. Re-baseline necesario.
- ⚠️ El plan NO menciona `run.py:93` ni `local_executor.py:51` → **Ambos son vulnerabilidades activas. Agregadas como tareas 5 y 6.**

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] SE5.1: `import subprocess` → SecurityError("Forbidden import 'subprocess'")
✅ [CODE] SE5.2: `import shutil` → SecurityError("Forbidden import 'shutil'")
✅ [CODE] SE5.3: `import ctypes` → SecurityError("Forbidden import 'ctypes'")
✅ [CODE] SE5.4: `import socket` → SecurityError("Forbidden import 'socket'")
✅ [CODE] SE5.5: `import gc` → SecurityError("Forbidden import 'gc'")
✅ [CODE] SE5.6: `import inspect` → SecurityError("Forbidden import 'inspect'")
✅ [CODE] SE5.7: `import requests` → SecurityError("Forbidden import 'requests'")
✅ [CODE] SE5.8: `__import__("os")` → SecurityError("Forbidden function call '__import__'")
✅ [CODE] SE5.9: `compile("1+1", "", "eval")` → SecurityError("Forbidden function call 'compile'")
✅ [CODE] SE5.10: `exec("x=1")` → SecurityError("Forbidden function call 'exec'")
✅ [CODE] SE5.11: `async def` en `is_system=False` → SecurityError o RestrictedPython SyntaxError
✅ [CODE] SE5.12: `async def` en `is_system=True` → validate_skill() retorna True
✅ [BACKEND] SE5.13: `execute()` con `import os` → SecurityError (regresión)
✅ [BACKEND] SE5.14: `execute()` con `__builtins__['open']` → SecurityError (regresión)
✅ [BACKEND] SE5.15: `validate_skill()` con `__builtins__['__import__']` → SecurityError (regresión)
✅ [BACKEND] SE5.16: `execute()` con bypass indirecto → SecurityError (regresión)
✅ [BACKEND] SE5.17: `import importlib; importlib.import_module("os")` → SecurityError
✅ [CODE] SE5.18: hex-decoded "import os" + exec/compile → SecurityError
✅ [CODE] Fix run.py:93 — reemplazar `__import__` crudo por `_restricted_import`
✅ [CODE] Fix local_executor.py:51 — usar `SecurityGuard.execute()` o `_create_safe_builtins()`
✅ [DX] `fap security-audit` ejecuta sin errores y reporta breakdown por categoría
✅ [DX] `fap security-audit --json` produce JSON válido con {"total": 18, "pass": N, "categories": {...}}
✅ [DX] `fap test-step 5` funciona como alias
✅ [DATA] Sin cambios de schema DB — verificado contra código
```

**Funcionales:**
- [ ] 14/14 tests nuevos pasan (SE5.1-SE5.12 + SE5.17-SE5.18)
- [ ] 4/4 tests regresión pasan (SE5.13-SE5.16)
- [ ] `fap security-audit` reporta 18/18 pass
- [ ] `ruff check tests/unit/test_security_guard*.py src/cli/commands/run.py src/services/local_executor.py` → 0 errores
- [ ] Suite total no regreda: `pytest tests/` → 0 failures

**Técnicos:**
- [ ] Re-baseline documentado: contar tests exactos con `pytest --co -q tests/` antes y después
- [ ] `run.py` modo sandbox bloquea imports prohibidos; `--danger-no-sandbox` sigue funcional
- [ ] `local_executor.py` sigue ejecutando código válido (io/zipfile/json/math)

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap security-audit` command + alias `fap test-step 5` | Media | 1h | Ninguna | `fap security-audit` reporta breakdown; `--json` produce JSON válido |
| 1 | Expandir `test_security_guard.py` con SE5.1-SE5.7 (imports prohibidos: subprocess, shutil, ctypes, socket, gc, inspect, requests) | Baja | 20min | Tarea 0 | `fap security-audit --category imports` → 7/7 pass |
| 2 | Expandir `test_security_guard.py` con SE5.8-SE5.10 (calls prohibidos: `__import__()`, `compile()`, `exec()`) | Baja | 15min | Tarea 0 | `fap security-audit --category calls` → 3/3 pass |
| 3 | Expandir `test_security_guard.py` con SE5.11-SE5.12 (async: non-system bloqueado, system permitido) | Media | 20min | Tarea 0 | `fap security-audit --category async` → 2/2 pass |
| 4 | Verificar SE5.13-SE5.16 ya existen y pasan (regresión) | Baja | 5min | Ninguna | `fap security-audit --category regresion` → 4/4 pass |
| 5 | **FIX CRÍTICO:** `run.py:93` — reemplazar `__import__` crudo por versión restringida | Media | 30min | Tarea 0 | `fap run skill --sandbox` (sin flag) bloquea imports; tests SE5.x siguen pass |
| 6 | **FIX CRÍTICO:** `local_executor.py:51` — usar `SecurityGuard.execute()` o `_create_safe_builtins()` | Media | 30min | Tarea 0 | LocalExecutor ejecuta código válido, bloquea código malicioso |
| 7 | Crear `test_security_guard_escape.py` con SE5.17 (importlib bypass) y SE5.18 (hex exec bypass) | Media | 30min | Tarea 0 | `fap security-audit --category escape` → 2/2 pass |
| 8 | Validación final: lint + suite completa + re-baseline | Baja | 15min | Tareas 1-7 | `ruff check → 0 errors`. `fap security-audit → 18/18`. `pytest tests/ → baseline N` |
| **TOTAL** | | | **3.5h** | | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap security-audit` para dogfooding del resto del paso.

**Orden recomendado:** T4 (verificar regresión existente) → T0 (DX) → T1+T2+T3+T7 (tests en paralelo) → T5+T6 (fixes) → T8 (validación)

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1: Fix `run.py:93` rompe `fap run skill`** | Alta | Cambiar sandbox de CLI podría afectar bundles locales existentes | Test manual post-fix: `fap run skill --danger-no-sandbox` y modo normal. Agregar test de regresión. |
| **R2: Fix `local_executor.py:51` rompe LocalExecutor** | Alta | Cambiar exec directo por SecurityGuard.execute() cambia comportamiento de exec_globals | Verificar que `exec_globals` retornado tiene mismas keys. Agregar test de regresión. |
| **R3: SE5.11 async no lanza SecurityError sino SyntaxError** | Media | RestrictedPython rechaza `async def` con SyntaxError, no SecurityError | Test debe capturar ambos: `pytest.raises((SecurityError, SyntaxError))` |
| **R4: SE5.18 requiere `eval`/`exec` para ser bypass real** | Media | Hex literal solo = SyntaxError directo. Bypass real requiere decode + exec | Implementar: `code = b"\\x69\\x6d...".decode("utf-8"); exec(code)` → SecurityError |
| **R5: Suite baseline erronea (489 ≠ 455 ≠ 425)** | Baja | Plan y phase-state desactualizados | Ejecutar `pytest --co -q tests/` al inicio y documentar baseline real. Gate ajustado. |
| **R6: Zombie threads en sandbox timeout** | Media | `ThreadPoolExecutor.shutdown(wait=False)` no mata worker en loop infinito | Documentado en roadmap. No blocker para MVP. |
| **R7: Discrepancia minim2.7 (afirma SE5.1-SE5.12 existen)** | Baja | minim2.7 reportó erróneamente que tests existían | Corregido en esta unificación. Implementador debe agregar los 12 tests. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Import prohibido subprocess (SE5.1) | `guard.validate_skill("import subprocess")` | `SecurityError("Forbidden import 'subprocess'")` |
| TP-2 | Import prohibido requests (SE5.7) | `guard.validate_skill("import requests")` | `SecurityError("Forbidden import 'requests'")` |
| TP-3 | `__import__` como call (SE5.8) | `guard.validate_skill("__import__('os')")` | `SecurityError("Forbidden function call '__import__'")` |
| TP-4 | `compile()` prohibido (SE5.9) | `guard.validate_skill("compile('1+1','','eval')")` | `SecurityError("Forbidden function call 'compile'")` |
| TP-5 | `exec()` prohibido (SE5.10) | `guard.validate_skill("exec('x=1')")` | `SecurityError("Forbidden function call 'exec'")` |
| TP-6 | async non-system bloqueado (SE5.11) | `guard.validate_skill("async def f(): pass")` | `SecurityError` o `SyntaxError` de RestrictedPython |
| TP-7 | async system permitido (SE5.12) | `SecurityGuard(is_system=True).validate_skill("async def f(): pass")` | `True` |
| TP-8 | Regresión SE5.13 | `guard.execute("import os\\ndef f(): os.system('ls')")` | `SecurityError` |
| TP-9 | importlib bypass (SE5.17) | `guard.validate_skill("import importlib; importlib.import_module('os')")` | `SecurityError` |
| TP-10 | Hex exec bypass (SE5.18) | `guard.execute("exec(b'\\\\x69\\\\x6d...'.decode())")` | `SecurityError` |
| TP-11 | Fix run.py regresión | `safe_env["__import__"]("os")` post-fix | `SecurityError` (antes: import exitoso) |
| TP-12 | Fix local_executor regresión | `exec(code, {"__builtins__": safe_builtins}, loc)` reemplazado por `guard.execute(code)` | Mismo comportamiento para código válido |

**Comando para ejecutar tests:** `pytest tests/unit/test_security_guard*.py -v`
**Comando para DX:** `fap security-audit` / `fap test-step 5`
**Lint:** `ruff check src/cli/commands/run.py src/services/local_executor.py tests/unit/test_security_guard*.py`

---

## 📊 Calidad de Aportes por Análisis

| Agente | Score | Fortalezas | Debilidades |
|---|---|---|---|
| **ds** | ⭐ 4.9/5 | Verificación código más precisa (20/20). Identificó bug SE5.18 hex-inválido. Mejor DX tool (categorías + JSON). 4 etapas completas. | Solo falló: no detectó run.py:93 ni local_executor:51. |
| **glm** | ⭐ 4.9/5 | **Hallazgo más valioso:** `run.py:93` y `local_executor.py:51` — 2 vulnerabilidades activas que ningún otro agente detectó. Verificación más exhaustiva (22/22). Mejor análisis backend. | DX tool menos detallada que ds. |
| **kimi2.6** | ⭐ 4.3/5 | Detectó discrepancia suite count (489). Buen análisis DB/data. Identificó bypass FAP-CORE. Script verify_sec.py ejecutado. | Menos preciso en code verification. DX tool apunta a pre-validación, no testing. |
| **minim2.7** | ⭐ 3.5/5 | Detectó FORBIDDEN_MODULES count discrepancy. Conciso. | **ERROR GRAVE:** Afirmó SE5.1-SE5.12 existen (NO). Sin backend/fullstack analysis (§3/§4 = N/A). DX más débil. No detectó run.py/local_executor vulns. |

**Factor de corrección aplicado:** minim2.7 penalizado -1.0 por error factual (afirmar tests existentes que no existen). ds y glm subieron +0.4 por hallazgos críticos post-verificación de código real.
