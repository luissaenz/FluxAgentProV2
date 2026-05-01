# Análisis Técnico — Paso 5: Seguridad — Hardening

> **Paso:** 5 — Seguridad — Hardening
> **Agente:** glm
> **Fecha:** 2026-05-01
> **Referencia:** Plan v3.1 Paso 5, phase-state.md Fase VI

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `FORBIDDEN_MODULES` contiene subprocess, shutil, ctypes, socket, gc, inspect, requests | `grep` en `security_guard.py:19-41` | ✅ | Todos presentes. subprocess línea 23, shutil línea 24, ctypes línea 26, socket línea 25, gc línea 31, inspect línea 30, requests línea 38 |
| 2 | `ALLOWED_MODULES` contiene io, zipfile, hashlib, base64, string | `grep` en `security_guard.py:46-70` | ✅ | Líneas 65-70. Módulos de Paso 1 (dogfooding) incluidos |
| 3 | `FORBIDDEN_CALLS` = {eval, exec, compile, open, __import__} | `security_guard.py:73` | ✅ | Exactamente esos 5. AST scanner los detecta |
| 4 | `_create_safe_builtins()` existe con `_restricted_import` | `security_guard.py:126-159` | ✅ | Reemplaza `__import__` con versión restringida que verifica allowlist/forbidden |
| 5 | `execute()` usa `_create_safe_builtins()` para non-system | `security_guard.py:161-180` | ✅ | Línea 173: `exec_globals = {"__builtins__": self._create_safe_builtins()}` |
| 6 | `execute()` usa `__builtins__` completo para system | `security_guard.py:171` | ✅ | `exec_globals = {"__builtins__": __builtins__}` — system bundles bypass sandbox |
| 7 | `_verify_compilation()` usa `_create_safe_builtins()` | `security_guard.py:232-249` | ✅ | Línea 242: `safe_env = self._create_safe_builtins()` |
| 8 | Tests SE5.13-SE5.16 ya existen | `test_security_guard.py:98-126` | ✅ | 4 tests de diagnóstico ya implementados |
| 9 | `test_security_guard_escape.py` NO existe | `glob tests/**/*escape*` | ✅ | Archivo nuevo, no creado aún |
| 10 | Vulnerabilidad línea 142 (inyección `__import__`) — YA CORREGIDA | Plan dice `exec_globals["__builtins__"]["__import__"] = __import__` | ❌ DISCREPANCIA | Código actual usa `_create_safe_builtins()` con `_restricted_import`. Línea 142 NO existe como describe el plan |
| 11 | Vulnerabilidad línea 221 (inyección `__import__` en `_verify_compilation`) — YA CORREGIDA | Plan dice `safe_env["__import__"] = __import__` | ❌ DISCREPANCIA | Código actual usa `self._create_safe_builtins()` en `_verify_compilation`. Línea 221 NO existe como describe el plan |
| 12 | Vulnerabilidad en `run.py:93` — ACTIVA | `run.py:93`: `safe_env["__import__"] = __import__` | ⚠️ | CLI inyecta `__import__` real directamente. Bypass completo de sandbox. Fuera de `security_guard.py` |
| 13 | `async def` bloqueado por RestrictedPython | RestrictedPython v8.1 no soporta async | ⚠️ | Verificar experimentalmente. AST de RestrictedPython rechaza `async def` |
| 14 | `apply_kernel_hardening()` existe | `security_guard.py:279-306` | ✅ | Implementado como no-op en Windows/macOS. Placeholder para Linux Seccomp |
| 15 | `FORBIDDEN_MODULES` incluye `importlib` | `security_guard.py:29` | ✅ | SE5.17 verificará que AST scanner bloquea `import importlib` |
| 16 | `SecurityError` exportado y usado | `security_guard.py:76-79` + imports en bundle_manager, import_service, local_executor, dev, validate, run, registry | ✅ | Ampliamente integrado |
| 17 | `is_system` flag funciona correctamente | `security_guard.py:90,102-103,115-116,170` | ✅ | System bundles: bypass RestrictedPython, usa `__builtins__` completo |
| 18 | `_scan_ast` detecta `ast.Call` con `__import__` | `security_guard.py:201-207` | ✅ | Pero NO detecta acceso indirecto vía `__builtins__["__import__"]` — SE5.14/SE5.16 verifican que `_create_safe_builtins` bloquee esto en runtime |
| 19 | Hex-encoded payload (`\x69\x6d\x70\x6f\x72\x74`) → AST scanner lo ve como string literal | AST parse interpreta escape sequences | ✅ | SE5.18: eval de string hex resultaría en `import os` pero RestrictedPython lo bloquea |
| 20 | `from RestrictedPython import compile_restricted, safe_builtins` — `safe_builtins` NO tiene `__import__` | Verificado con `python -c` | ✅ | `safe_builtins` no contiene `__import__`. Confirmado |
| 21 | API `/bundles/security-config` expone ALLOWED_MODULES y FORBIDDEN_MODULES | `bundles.py:37-44` | ✅ | Endpoint GET sirve config de seguridad al CLI |
| 22 | `local_executor.py:51` usa `safe_builtins` directamente en exec | `local_executor.py:37,51` | ⚠️ | No usa `SecurityGuard.execute()`. Usa exec directo con `safe_builtins`. Sin `_restricted_import` |

**Discrepancias encontradas:**

1. **❌ Plan vs Código — Vulnerabilidad `__import__` YA CORREGIDA:** El plan (v3.1) describe `security_guard.py:142` y `221` como inyección directa de `__import__`. El código actual usa `_create_safe_builtins()` con `_restricted_import` que filtra imports contra allowlist/forbidden. **Los tests SE5.13-SE5.16 deben verificar que el fix SÍ funciona**, no que el bug existe.

2. **⚠️ Vulnerabilidad REAL en `run.py:93`:** `safe_env["__import__"] = __import__` inyecta `__import__` sin restricción. Esto DEBE corregirse para usar `SecurityGuard._create_safe_builtins()` o una versión restringida equivalente. No test cubre esto.

3. **⚠️ `local_executor.py:51`** usa `safe_builtins` directo sin `_restricted_import`. Similar a `run.py`, potencial bypass.

4. **⚠️ SE5.11 (async bloqueado):** RestrictedPython v8.1 rechaza `async def` en compilación. Verificar que `validate_skill` con `is_system=False` efectivamente lanza `SecurityError`. Si `is_system=True`, `validate_skill` saltea RestrictedPython y solo hace `compile()` estándar → async permitido → SE5.12 debe retornar True.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Paso 5 es testing de seguridad. **No hay cambios de schema DB.** No hay migraciones.

- ✅ **Sin tablas nuevas** — Paso toca solo `security_guard.py` y tests
- ✅ **Sin cambios de integridad referencial** — No hay impacto en DB
- ✅ **Sin RLS policies** — Fuera de scope
- ✅ **Sin índices nuevos** — Fuera de scope

**Nota:** El endpoint `/bundles/security-config` lee ALLOWED_MODULES/FORBIDDEN_MODULES del módulo. Si se modifican en runtime (vía SecurityGuard constructor o system bundle flag), la API NO refleja esos cambios dinámicos. Baja prioridad — no affecta Paso 5.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Archivos a modificar/crear

| Archivo | Acción | Descripción |
|---|---|---|
| `tests/unit/test_security_guard.py` | **Expandir** | Añadir SE5.1-SE5.12, verificar SE5.13-SE5.16 existentes |
| `tests/unit/test_security_guard_escape.py` | **Crear** | SE5.17-SE5.18 |
| `src/cli/commands/run.py` | **Fix** | Línea 93: reemplazar `__import__` por restricted version |
| `src/services/local_executor.py` | **Fix** | Línea 51: usar `SecurityGuard.execute()` o `_create_safe_builtins()` |

### 2.2 Funciones/clases nuevas

No hay funciones/clases nuevas en código fuente. Solo tests.

### 2.3 Funciones existentes — firmas y comportamiento

**`SecurityGuard.__init__`** — `security_guard.py:85-99`
```python
def __init__(self, timeout_seconds=30, allowed_modules=None, forbidden_modules=None, is_system=False)
```
- `is_system` habilita bypass de RestrictedPython (solo `compile()` estándar)
- `allowed_modules`/`forbidden_modules` personalizables

**`SecurityGuard.validate_skill`** — `security_guard.py:105-124`
```python
def validate_skill(self, source_code: str, filename: str = "skill.py") -> bool
```
- AST scan SIEMPRE se ejecuta
- `_verify_compilation` solo para `is_system=False`
- Retorna `True` o lanza `SecurityError`

**`SecurityGuard._create_safe_builtins`** — `security_guard.py:126-159`
```python
def _create_safe_builtins(self) -> Dict[str, Any]
```
- Crea builtins restringidos con `_restricted_import`
- `_restricted_import` verifica forbidden/allowed lists antes de importar
- **KEY FIX:** Ya NO inyecta `__import__` real

**`SecurityGuard.execute`** — `security_guard.py:161-180`
```python
def execute(self, source_code: str, filename: str = "dynamic_code.py") -> Dict[str, Any]
```
- Llama `validate_skill` primero
- Para `is_system=True`: usa `__builtins__` completo (trust model)
- Para `is_system=False`: usa `_create_safe_builtins()`
- Retorna `exec_globals` dict

**`SecurityGuard._scan_ast`** — `security_guard.py:182-217`
- Detecta `import X`, `from X import Y`, `ast.Call` con FORBIDDEN_CALLS
- Detecta `__dunder__` attribute access en calls
- **GAP:** No detecta acceso indirecto vía `__builtins__` dict (subscript). Se頼 en `_create_safe_builtins()` para runtime protection

**`SecurityGuard._verify_compilation`** — `security_guard.py:232-277`
- Compila con `compile_restricted`
- Ejecuta dry-run con timeout (`concurrent.futures.ThreadPoolExecutor`)
- Timeout default: 30s (configurable)

### 2.4 Patrones: se siguen los existentes

- **Fixture:** `guard` fixture con `SecurityGuard(timeout_seconds=2)` — patrón existente
- **Tests:** `pytest.raises(SecurityError, match="...")` — patrón existente
- **Aserciones:** Saltar RestrictedPython para system bundles → patrón `is_system=True`

### 2.5 Modularidad y duplicación

- **Duplicación:** `run.py:93` y `local_executor.py:51` replican lógica de sandbox manualmente en vez de usar `SecurityGuard.execute()`. Debería unificarse.
- **Cohesión:** `SecurityGuard` tiene alta cohesión — AST scan + compilación + ejecución en una clase.

### 2.6 Imports y dependencias

- `RestrictedPython 8.1` — dependencia directa. Sin `__version__` attribute (verificado).
- `safe_builtins` de RestrictedPython — NO contiene `__import__` (verificado).
- No se requieren dependencias nuevas para Paso 5.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### 3.1 APIs afectadas

| Endpoint | Impacto | Descripción |
|---|---|---|
| `GET /bundles/security-config` | Solo lectura | Expone ALLOWED_MODULES y FORBIDDEN_MODULES. Los tests no lo modifican. |
| `POST /bundles/import` | Indirecto | Usa `ImportService` → `BundleManager` → `SecurityGuard.validate_skill()`. Tests verifican que SecurityError se propaga correctamente. |
| `POST /bundles/validate` | Indirecto | Dry-run validation. Similar al anterior. |

### 3.2 Middleware

- `require_org_id` (middleware.py) — No afectado por Paso 5.
- `SecurityError` es capturada en `bundles.py:99` y convertida a HTTPException.

### 3.3 Flujos backend → frontend

Paso 5 es testing puro. No hay cambios en flujos de datos. Los tests se ejecutan en CI, no en runtime.

### 3.4 Contratos entre servicios

- **`SecurityGuard` → `BundleManager`:** `validate_skill()` lanza `SecurityError` → `BundleManager.process_zip()` lo propaga
- **`SecurityGuard` → `ImportService`:** `execute()` retorna `exec_globals` o lanza `SecurityError`
- **`SecurityGuard` → `LocalExecutor`:** Actualmente NO usa `execute()`. Usa `validate_skill()` + exec manual. **Vulnerabilidad.**
- **`SecurityGuard` → `flow_registry`:** Usa `SecurityGuard(is_system=True).execute()` para flows de DB

### 3.5 Error handling

- `SecurityError` → propagada a caller → HTTPException en API routes
- En `import_service.py:293`, errores de skill registration se **loguean y continúan** (`except Exception: continue`). Vulnerabilidad potencial: skill malicioso que escapa sandbox NO se registra, pero NO falla el bundle import.
- En `bundle_manager.py:136`, `SecurityError` se convierte en `BundleError` con contexto.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### 4.1 Flujo completo: DB → Backend → Frontend → UX

No hay cambios fullstack directos. Impacto indirecto:

```
Bundle Upload (Frontend) → /bundles/import (API) → ImportService → BundleManager → SecurityGuard.validate_skill()
                                                                            ↓ (si pasa)
                                                                     SecurityGuard.execute() → registro de skill/flow
```

- Si `SecurityGuard` falla → 400 Bad Request con mensaje de `SecurityError`
- Si `SecurityGuard` permite código malicioso → **vulnerabilidad de ejecución de código arbitrario**

### 4.2 Coherencia

- **✅** `SecurityGuard` usado consistentemente en `BundleManager`, `ImportService`, `Registry`, `CLI validate`, `CLI dev`
- **❌** `run.py` y `local_executor.py` NO usan `SecurityGuard.execute()` — implementations sandbox manuales inconsistentes
- **✅** `is_system` flag permite system bundles con acceso completo

### 4.3 Alineación con arquitectura existente

- Los tests SE5.1-SE5.12 son unitarios puros — sin DB, sin HTTP, sin mocking complejo
- SE5.13-SE5.16 son diagnostics que VERIFICAN que el fix funciona
- SE5.17-SE5.18 son tests de escape avanzados — unitarios puros
- **FIX de `run.py:93`** alinea CLI con el patron de SecurityGuard

### 4.4 DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap test-security
- **Qué automatiza:** Ejecuta TODOS los tests de seguridad (SE5.1-SE5.18) con un solo comando. Reporta resultados por categoría (imports, async, injection, escape).
- **Tipo:** CLI command (extensión de `fap test-step`)
- **Cómo se usa:** `fap test-security` o `fap test-step 5`
- **Impacto para el usuario final:** Un comando para validar seguridad completa del sandbox. Evita ejecutar manualmente pytest con filtros específicos.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Sin cambios de schema necesarios — verificado contra código
✅ [CODE] SE5.1: import subprocess → SecurityError con "Forbidden import 'subprocess'"
✅ [CODE] SE5.2: import shutil → SecurityError con "Forbidden import 'shutil'"
✅ [CODE] SE5.3: import ctypes → SecurityError con "Forbidden import 'ctypes'"
✅ [CODE] SE5.4: import socket → SecurityError con "Forbidden import 'socket'"
✅ [CODE] SE5.5: import gc → SecurityError con "Forbidden import 'gc'"
✅ [CODE] SE5.6: import inspect → SecurityError con "Forbidden import 'inspect'"
✅ [CODE] SE5.7: import requests → SecurityError con "Forbidden import 'requests'"
✅ [CODE] SE5.8: __import__("os") → SecurityError con "Forbidden function call '__import__'"
✅ [CODE] SE5.9: compile("1+1", "", "eval") → SecurityError con "Forbidden function call 'compile'"
✅ [CODE] SE5.10: exec("x=1") → SecurityError con "Forbidden function call 'exec'"
✅ [CODE] SE5.11: async def en is_system=False → SecurityError (RestrictedPython rechaza async)
✅ [CODE] SE5.12: async def en is_system=True → True (bypass RestrictedPython, solo compile())
✅ [BACKEND] SE5.13: execute() con import os → SecurityError (verificar fix funciona)
✅ [BACKEND] SE5.14: execute() con __builtins__["open"] → SecurityError (verificar fix funciona)
✅ [BACKEND] SE5.15: _verify_compilation con __builtins__["__import__"] → SecurityError (verificar fix funciona)
✅ [BACKEND] SE5.16: execute() con bypass indirecto → SecurityError (verificar fix funciona)
✅ [BACKEND] SE5.17: import importlib → SecurityError (FORBIDDEN_MODULES)
✅ [CODE] SE5.18: Payload hex-encoded "import os" → SecurityError o RestrictedPython error
✅ [CODE] Fix run.py:93 — reemplazar __import__ por restricted version
✅ [CODE] Fix local_executor.py:51 — usar SecurityGuard.execute() o _create_safe_builtins()
✅ [DX] fap test-security ejecuta sin errores y reporta por categoría
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| SE5.11-SE5.12: RestrictedPython rechaza async de formas inesperadas | Media | RestrictedPython v8.1 puede lanzar errores distintos a SecurityError para async | Capturar RuntimeError/CompilationError además de SecurityError en test |
| SE5.18: Hex-encoded payload podría pasar AST scanner | Alta | AST parsea string literals tal cual, no decodifica \x escapes como código ejecutable | RestrictedPython compile_restricted bloquea exec/compile, y string hex no es código ejecutable sin eval. Verificar experimentalmente |
| Fix `run.py:93` rompe CLI `fap run skill` | Alta | Cambiar sandbox podría afectar funcionalidad local | Test de regresión en CLI + verificar que skills permitidas siguen funcionando |
| Fix `local_executor.py:51` rompe `fap run` local | Media | Patrón similar a run.py | Mismo fix: usar SecurityGuard.execute() |
| Allowed modules incompleto para uso real | Baja | Módulos como `io`, `zipfile` añadidos en Paso 1. Skills pueden necesitar otros módulos no en allowlist | Configuración dinámica vía `/bundles/security-config` ya existe |
| `import_service.py:293` continúa en error de skill registration | Media | Si skill escapa sandbox y falla en exec, se loguea y continúa. No bloquea bundle import | Evaluación: esta es decisión de diseño (best-effort registration). No cambia para Paso 5 |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Añadir `fap test-step 5` o verificar que funciona con tests existentes | FULLSTACK/DX | Baja | 0.5h | Ninguna | → verificar: `fap test-step 5` ejecuta tests de security sin errores |
| 1 | Expandir `test_security_guard.py` con SE5.1-SE5.7 (imports) | CODE | Baja | 0.5h | Ninguna | → verificar: 7 tests nuevos pasan con `pytest tests/unit/test_security_guard.py -v` |
| 2 | Expandir `test_security_guard.py` con SE5.8-SE5.10 (forbidden calls) | CODE | Baja | 0.5h | Ninguna | → verificar: 3 tests nuevos pasan |
| 3 | Expandir `test_security_guard.py` con SE5.11-SE5.12 (async) | CODE | Media | 1h | Ninguna | → verificar: async en non-system lanza SecurityError, async en system retorna True |
| 4 | Verificar SE5.13-SE5.16 ya existen y pasan | BACKEND | Baja | 0.5h | Ninguna | → verificar: `pytest tests/unit/test_security_guard.py -k "se5" -v` muestra 4 tests pasando |
| 5 | Crear `test_security_guard_escape.py` con SE5.17-SE5.18 | CODE | Media | 1h | Ninguna | → verificar: 2 tests nuevos pasan con `pytest tests/unit/test_security_guard_escape.py -v` |
| 6 | Fix `run.py:93` — reemplazar `__import__` inseguro por restricted | CODE | Media | 1h | Ninguna | → verificar: `fap run skill --danger-no-sandbox` funciona y sandbox mode bloquea imports prohibidos |
| 7 | Fix `local_executor.py:51` — usar `SecurityGuard.execute()` o `_create_safe_builtins()` | CODE | Media | 1h | Ninguna | → verificar: test de regresión de LocalExecutor pasa |
| 8 | Ejecutar suite completa Paso 5 y verificar coverage | FULLSTACK | Baja | 0.5h | Tareas 1-7 | → verificar: todos los tests de seguridad pasan, coverage de security_guard.py >90% |

**Tiempo total estimado:** 6 horas

**Orden de ejecución recomendado:**
1. Tarea 4 primero (verificar estado actual de SE5.13-SE5.16)
2. Tareas 1-2-3-5 en paralelo (tests nuevos)
3. Tareas 6-7 (fixes críticos)
4. Tarea 0-8 (DX y verificación final)

**Nota sobre SE5.13-SE5.16:** Si alguno de estos tests FALLA (código malicioso se ejecuta), significa que el fix de `_restricted_import` tiene bugs. **FIJAR `security_guard.py` ANTES de continuar.** Sin embargo, análisis del código actual indica que el fix DEBERÍA funcionar.

---

## 🔮 Roadmap (NO implementar ahora)

- **Seccomp/Kernel hardening:** `apply_kernel_hardening()` es placeholder. Implementar BPF filter para Linux workers.
- **Configuración dinámica de allowed/forbidden modules:** API `/bundles/security-config` solo lee defaults. Permitir configuración por org.
- **Rate limiting en SecurityGuard:** Prevenir abuse de compilación (DoS por código complejo).
- **Logging estructurado de violaciones de seguridad:** Audit trail de código bloqueado por org.bundle.
- **Test de SE5.18 con más vectores de encoding:** Base64, rot13, string concatenation dinámica.