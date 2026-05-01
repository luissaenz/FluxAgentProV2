# Análisis Técnico — Paso 5: Seguridad — Hardening

**Agente:** ds
**Fecha:** 2026-05-01
**Base:** `plan.md` §Paso 5 (pág. 211-276)
**Archivos afectados:** `src/services/security_guard.py`, `tests/unit/test_security_guard.py`, `tests/unit/test_security_guard_escape.py` (nuevo)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `security_guard.py` existe | `src/services/security_guard.py` | ✅ | 306 líneas. Clase `SecurityGuard` con `validate_skill()`, `execute()`, `_scan_ast()`, `_verify_compilation()`, `_create_safe_builtins()` |
| 2 | `FORBIDDEN_MODULES` incluye `subprocess` | grep en línea 23 | ✅ | `security_guard.py:23` — `"subprocess"` presente |
| 3 | `FORBIDDEN_MODULES` incluye `shutil` | grep en línea 24 | ✅ | `security_guard.py:24` — `"shutil"` presente |
| 4 | `FORBIDDEN_MODULES` incluye `ctypes` | grep en línea 25 | ✅ | `security_guard.py:26` — `"ctypes"` presente |
| 5 | `FORBIDDEN_MODULES` incluye `socket` | grep en línea 26 | ✅ | `security_guard.py:24` — `"socket"` presente |
| 6 | `FORBIDDEN_MODULES` incluye `gc` | grep en línea 27 | ✅ | `security_guard.py:31` — `"gc"` presente |
| 7 | `FORBIDDEN_MODULES` incluye `inspect` | grep en línea 28 | ✅ | `security_guard.py:30` — `"inspect"` presente |
| 8 | `FORBIDDEN_MODULES` incluye `requests` | grep en línea 29 | ✅ | `security_guard.py:37` — `"requests"` presente |
| 9 | `FORBIDDEN_CALLS` incluye `__import__` | línea 73 | ✅ | `{"eval", "exec", "compile", "open", "__import__"}` |
| 10 | `FORBIDDEN_CALLS` incluye `compile` | línea 73 | ✅ | Mismo set |
| 11 | `FORBIDDEN_CALLS` incluye `exec` | línea 73 | ✅ | Mismo set |
| 12 | `test_security_guard.py` existe | `tests/unit/test_security_guard.py` | ✅ | 126 líneas. 15 tests existentes |
| 13 | SE5.13-SE5.16 tests existen en test file | líneas 101-126 | ✅ | `test_se5_13_execute_blocks_forbidden_import` a `test_se5_16_execute_blocks_indirect_import_bypass` |
| 14 | `test_security_guard_escape.py` existe | glob en `tests/unit/` | ❌ | **NO EXISTE.** Archivo nuevo requerido para SE5.17-SE5.18 |
| 15 | `FORBIDDEN_MODULES` incluye `importlib` | línea 29 | ✅ | `"importlib"` presente — SE5.17 ya bloqueable |
| 16 | Vulnerabilidad `__import__` línea 142 (plan) | verificación runtime | ✅ **FIXED** | `_create_safe_builtins()` (línea 156) usa `_restricted_import` con allowlist, NO inyecta `__import__` real |
| 17 | Vulnerabilidad `__import__` línea 221 (plan) | verificación runtime | ✅ **FIXED** | `_verify_compilation()` (línea 242) usa `self._create_safe_builtins()` con `_restricted_import` |
| 18 | RestrictedPython bloquea `async def` | test runtime | ✅ | `compile_restricted("async def f(): pass")` → `SyntaxError: AsyncFunctionDef statements are not allowed.` |
| 19 | System bundles saltan RestrictedPython | línea 115 | ✅ | `if not self.is_system: self._verify_compilation(...)` |
| 20 | `_create_safe_builtins()` no permite `os` | test runtime | ✅ | `guard._create_safe_builtins()["__import__"]("os")` → `SecurityError: Forbidden import` |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | **Plan dice "agregar SE5.13-SE5.16" pero YA EXISTEN** en `test_security_guard.py:101-126`. | Confirmar que tests existen y pasan. NO duplicar. Plan desactualizado — suite actual ya cubre diagnóstico `__import__`. |
| D2 | **Vulnerabilidad `__import__` YA FUE FIJADA.** Plan v3.1 describe bug en líneas 142 y 221, pero código actual inyecta `_restricted_import` (con allowlist) NO `__import__` real. | Tests SE5.13-SE5.16 son verificación de regresión, no diagnóstico de bug activo. Fix ya aplicado. |
| D3 | **Plan cuenta 18 tests nuevos** (SE5.1-SE5.18). Realidad: 4 ya existen (SE5.13-SE5.16). Neto: **14 tests nuevos**. | Ajustar conteo en plan y criterios de aceptación. |
| D4 | **SE5.18 (`\x69\x6d\x70\x6f\x72\x74\x20\x6f\x73`) no es código Python válido por sí mismo.** Causa SyntaxError directo. El bypass real requiere `exec(decoded_string)` o `compile(decoded_string, '', 'exec')`, ambos ya bloqueados por `FORBIDDEN_CALLS`. | SE5.18 debe testear que hex-decoded code + exec no pasa el sandbox. El test actual propuesto en plan es syntax-invalid. Reescribir. |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Paso 5 no toca DB directamente.** No hay migraciones, tablas, RLS ni schemas involucrados.

**Impacto indirecto:**
- Bundle definitions en DB (`bundle_skills`) pasan por `SecurityGuard.validate_skill()` en `bundle_manager.py`
- Si hay bypass de seguridad, datos almacenados en `agent_catalog`, `org_mcp_servers`, `domain_events` podrían ser comprometidos
- Schema actual soporta RLS por `org_id` — si sandbox se rompe, RLS no protege contra código malicioso dentro del tenant

**Schema relevante** (referencia, no modificado):
- `bundle_skills` → columna `source_code` TEXT → input de `validate_skill()`
- `service_tools` → columna `config` JSONB → input de ServiceConnector (no pasa por SecurityGuard)

✅ Sin cambios de schema requeridos. Paso puro de validación de sandbox.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones existentes verificadas

| Función | Firma | Rol | Estado |
|---|---|---|---|
| `SecurityGuard.validate_skill()` | `(source_code: str, filename: str = "skill.py") -> bool` | Orquesta AST scan + RestrictedPython | ✅ |
| `SecurityGuard.execute()` | `(source_code: str, filename: str = "dynamic_code.py") -> Dict[str, Any]` | Validación + ejecución en sandbox | ✅ |
| `SecurityGuard._scan_ast()` | `(source_code: str, filename: str)` | AST walk: imports, calls, dunder | ✅ |
| `SecurityGuard._check_module()` | `(root_module: str, full_module: str, filename: str)` | Blacklist + allowlist check | ✅ |
| `SecurityGuard._verify_compilation()` | `(source_code: str, filename: str)` | RestrictedPython compile + dry-run con timeout | ✅ |
| `SecurityGuard._create_safe_builtins()` | `() -> Dict[str, Any]` | Crea `safe_builtins` con `__import__` restringido por allowlist | ✅ |
| `SecurityGuard.apply_kernel_hardening()` | `()` estático | Seccomp placeholder (solo Linux) | ⚠️ Placeholder |

### Patrones y Calidad

- **Patrón de sandboxing:** Doble capa (AST scan → RestrictedPython). AST es pre-filter, RestrictedPython es runtime guard.
- **`_create_safe_builtins()`** como fábrica de builtins restringidos es correcto. No inyecta `__import__` real.
- **`_verify_compilation()`** usa `ThreadPoolExecutor` para timeout — patrón adecuado, con limpieza `cancel_futures=True` en timeout.
- **`apply_kernel_hardening()`** es placeholder. Importa `ctypes` dentro de la función (no al nivel módulo), evita el `FORBIDDEN_MODULES` check. Esto es deliberado y seguro porque corre en proceso servidor, no en sandbox.

### Complejidad ciclomática

- `_scan_ast()`: 6 ramas (Import, ImportFrom, Call con Name, Call con Attribute, SyntaxError, normal)
- `_verify_compilation()`: 5 ramas (success, TimeoutError, SecurityError, other Exception, finally)
- `_restricted_import()`: 3 ramas (forbidden, not allowed, allowed)
- Complejidad media-baja. Código mantenible.

### Tests existentes que ya cubren SE5.x

| Test | Cubre | Estado |
|---|---|---|
| `test_forbidden_import_os` | `import os` | ✅ Existe (línea 34) |
| `test_forbidden_import_sys` | `import sys` | ✅ Existe (línea 40) |
| `test_forbidden_eval` | `eval()` | ✅ Existe (línea 60) |
| `test_forbidden_open` | `open()` | ✅ Existe (línea 66) |
| `test_dunder_access` | `__subclasses__()` | ✅ Existe (línea 72) |
| `test_timeout_infinite_loop` | `while True: pass` | ✅ Existe (línea 84) |
| `test_bypass_attempt` | `__builtins__['open']` | ✅ Existe (línea 91) |
| `test_se5_13_execute_blocks_forbidden_import` | SE5.13 | ✅ Existe (línea 101) |
| `test_se5_14_execute_blocks_builtins_bypass` | SE5.14 | ✅ Existe (línea 108) |
| `test_se5_15_verify_compilation_blocks_injected_import` | SE5.15 | ✅ Existe (línea 115) |
| `test_se5_16_execute_blocks_indirect_import_bypass` | SE5.16 | ✅ Existe (línea 122) |

### Tests faltantes (pendientes de implementar)

| ID | Descripción | Archivo destino |
|---|---|---|
| SE5.1 | `import subprocess` → bloqueado | `test_security_guard.py` |
| SE5.2 | `import shutil` → bloqueado | `test_security_guard.py` |
| SE5.3 | `import ctypes` → bloqueado | `test_security_guard.py` |
| SE5.4 | `import socket` → bloqueado | `test_security_guard.py` |
| SE5.5 | `import gc` → bloqueado | `test_security_guard.py` |
| SE5.6 | `import inspect` → bloqueado | `test_security_guard.py` |
| SE5.7 | `import requests` → bloqueado | `test_security_guard.py` |
| SE5.8 | `__import__("os")` → bloqueado | `test_security_guard.py` |
| SE5.9 | `compile("1+1", "", "eval")` → bloqueado | `test_security_guard.py` |
| SE5.10 | `exec("x=1")` → bloqueado | `test_security_guard.py` |
| SE5.11 | `async def` en `is_system=False` → bloqueado | `test_security_guard.py` |
| SE5.12 | `async def` en `is_system=True` → permitido | `test_security_guard.py` |
| SE5.17 | `import importlib; importlib.import_module("os")` → bloqueado | `test_security_guard_escape.py` |
| SE5.18 | Hex-encoded payload + exec bypass → bloqueado | `test_security_guard_escape.py` |

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Paso 5 no crea/modifica endpoints de API.** SecurityGuard es capa de servicio interno:

```
Bundle Upload (API) → bundle_manager.py → SecurityGuard.validate_skill() → DB (bundle_skills)
                                       → SecurityGuard.execute() → runtime sandbox
```

**Middleware relevante:**
- `src/api/middleware.py` → `verify_jwt` + org isolation. Protege acceso a endpoints de bundle.
- SecurityGuard no expone API directa. Solo se invoca desde `bundle_manager.py` y `crews/factory.py`.

**Flujo de datos:**
1. `POST /api/bundles/upload` → JWT validated → body contiene `source_code`
2. `bundle_manager.create_bundle()` → `SecurityGuard.validate_skill(code, is_system=False)`
3. AST scan → RestrictedPython compilation → si pasa, guarda en DB
4. En ejecución: `SecurityGuard.execute(code)` para bundles non-system

**Problema potencial:** SecurityGuard no es invocado en todos los paths de ejecución. Verificar:
- `bundle_manager.py` → ✅ llama `validate_skill()` en `create_bundle()`
- `crews/factory.py` → `resolve_tools()` NO invoca SecurityGuard directamente. Tools pasan por `ServiceConnector._run()` que sanitiza output post-ejecución.

✅ Sin cambios de API requeridos. Endpoints existentes son suficientes.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
Usuario escribe bundle code
  → Frontend (dashboard) upload a API
    → API valida JWT + org_id
      → bundle_manager.create_bundle()
        → SecurityGuard.validate_skill() [AST scan + RestrictedPython]
          → DB insert bundle_skills
            → En ejecución: SecurityGuard.execute()
              → CrewAI Agent usa tool/funcionalidad del bundle
```

### Coherencia

- ✅ SecurityGuard es la ÚNICA barrera entre código de bundle y ejecución. No hay segundo filtro en runtime.
- ✅ `_create_safe_builtins()` protege `execute()` con `__import__` restringido por allowlist.
- ✅ `_verify_compilation()` protege `validate_skill()` con RestrictedPython.
- ⚠️ **Gap:** Si hay un bug en RestrictedPython (CVE), no hay fallback. `apply_kernel_hardening()` es placeholder.

### DX & Tooling

#### Herramienta Propuesta: `fap security-audit`

- **Qué automatiza:** Verifica en 1 comando que el sandbox de SecurityGuard bloquea todos los vectores del Paso 5. Ejecuta todos los tests SE5.x, reporta breakdown por categoría (imports, calls, async, escape). Útil para CI y para desarrolladores que crean bundles y quieren validar qué pueden/cannot importar.
- **Tipo:** CLI (Typer command, extensión de `fap`)
- **Cómo se usa:**
  ```bash
  fap security-audit                    # corre todos los SE5.x tests
  fap security-audit --category imports  # solo imports (SE5.1-SE5.7)
  fap security-audit --category calls    # solo calls (SE5.8-SE5.10)
  fap security-audit --category async    # solo async (SE5.11-SE5.12)
  fap security-audit --category escape   # solo escape (SE5.17-SE5.18)
  fap security-audit --category vuln     # solo diagnóstico (SE5.13-SE5.16)
  fap security-audit --json              # output JSON para CI
  ```
- **Impacto para el usuario final:** Desarrolladores de bundles no necesitan conocer los 18 tests individuales. Un solo comando verifica que su código pasará el sandbox. CI puede integrar `--json` para gates automáticos.
- **Prioridad:** Tarea 0 — útil antes de escribir tests SE5.x para verificar regresión.

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] SE5.1: `import subprocess` → SecurityError("Forbidden import")
✅ [CODE] SE5.2: `import shutil` → SecurityError("Forbidden import")
✅ [CODE] SE5.3: `import ctypes` → SecurityError("Forbidden import")
✅ [CODE] SE5.4: `import socket` → SecurityError("Forbidden import")
✅ [CODE] SE5.5: `import gc` → SecurityError("Forbidden import")
✅ [CODE] SE5.6: `import inspect` → SecurityError("Forbidden import")
✅ [CODE] SE5.7: `import requests` → SecurityError("Forbidden import")
✅ [CODE] SE5.8: `__import__("os")` → SecurityError
✅ [CODE] SE5.9: `compile(...)` → SecurityError("Forbidden function call 'compile'")
✅ [CODE] SE5.10: `exec(...)` → SecurityError("Forbidden function call 'exec'")
✅ [CODE] SE5.11: `async def` en non-system → SecurityError (RestrictedPython)
✅ [CODE] SE5.12: `async def` en system → validate_skill() retorna True
✅ [CODE] SE5.13: execute() bloquea `import os` → SecurityError (regresión)
✅ [CODE] SE5.14: execute() bloquea `__builtins__['open']` → SecurityError (regresión)
✅ [CODE] SE5.15: validate_skill() bloquea `__builtins__['__import__']` → SecurityError (regresión)
✅ [CODE] SE5.16: execute() bloquea bypass indirecto → SecurityError (regresión)
✅ [CODE] SE5.17: `importlib.import_module("os")` → SecurityError
✅ [CODE] SE5.18: Hex-encoded exec bypass → SecurityError
✅ [CODE] 14/14 tests nuevos pasan (SE5.1-SE5.12 + SE5.17-SE5.18)
✅ [CODE] 4/4 tests regresión pasan (SE5.13-SE5.16)
✅ [DX] `fap security-audit` ejecuta todos los SE5.x tests con breakdown por categoría
✅ [DX] `fap security-audit --json` produce output parseable por CI
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1: RestrictedPython CVE** | Alta | RestrictedPython ≥7.x podría tener vulnerabilidad no conocida que permita bypass del sandbox. Dependencia externa. | Monitorear CVEs. `apply_kernel_hardening()` como tercera capa (implementar Seccomp real en Linux). Tests de regresión SE5.x detectan bypass. |
| **R2: `apply_kernel_hardening()` placeholder** | Media | La función está definida pero no se llama en ningún flujo. Es un no-op en Windows. Linux no tiene Seccomp activo. | Documentar como T15.5 pendiente. Riesgo mitigado mientras RestrictedPython + AST scan funcionen. |
| **R3: `_restricted_import` no chequea `fromlist`** | Media | `_restricted_import()` solo checkea `name.split(".")[0]`. `fromlist` con `level > 0` (import relativo) podría permitir import de módulo no permitido si el módulo actual está en allowed. | Edge case improbable porque bundles non-system no tienen `src` en `ALLOWED_MODULES`. Agregar `level == 0` assertion como safety net. |
| **R4: SecurityGuard no se invoca en todos los paths** | Media | Si un nuevo flujo de ejecución omite `validate_skill()`, código malicioso puede ejecutarse sin sandbox. | Centralizar invocación de SecurityGuard en un decorador o middleware de "execution gate". Agregar test de integración que verifique que todo bundle non-system pasa por SecurityGuard. |
| **R5: Tests SE5.x ya parcialmente implementados** | Baja | Plan asume 18 tests nuevos, pero 4 ya existen. Si implementador duplica, hay tests redundantes que pueden confundir. | Marcar SE5.13-SE5.16 como "ya existen — verificar pass". NO recrear. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap security-audit` comando CLI | FULLSTACK/DX | Media | 30min | Ninguna | → verificar: `fap security-audit` muestra breakdown correcto. `fap security-audit --json` produce JSON válido con `{"total": 18, "pass": 0, "fail": 0, "categories": {...}}` |
| 1 | Implementar tests SE5.1-SE5.7 (imports prohibidos) | CODE | Baja | 15min | Tarea 0 | → verificar: `fap security-audit --category imports` reporta 7/7 pass |
| 2 | Implementar tests SE5.8-SE5.10 (calls prohibidos) | CODE | Baja | 10min | Tarea 0 | → verificar: `fap security-audit --category calls` reporta 3/3 pass |
| 3 | Implementar tests SE5.11-SE5.12 (async) | CODE | Baja | 10min | Tarea 0 | → verificar: `fap security-audit --category async` reporta 2/2 pass. SE5.12 usa `SecurityGuard(is_system=True)` |
| 4 | Verificar tests SE5.13-SE5.16 ya existen y pasan | CODE | Baja | 5min | Ninguna | → verificar: pytest ejecuta `test_se5_13` a `test_se5_16` sin errores |
| 5 | Crear `test_security_guard_escape.py` con SE5.17-SE5.18 | CODE | Media | 15min | Tarea 0 | → verificar: `fap security-audit --category escape` reporta 2/2 pass |
| 6 | Validación final + lint | CODE | Baja | 10min | Tareas 1-5 | → verificar: `ruff check tests/unit/test_security_guard*.py` → 0 errores. `fap security-audit` → 18/18 pass |

**Tiempo total estimado:** 1.5 horas
**Tests totales:** 18 (14 nuevos + 4 verificación regresión)
**Archivos modificados:** `tests/unit/test_security_guard.py` (+12 tests), `src/cli/commands/` (+ `security_audit.py`)
**Archivos creados:** `tests/unit/test_security_guard_escape.py`

---

## 🔮 Roadmap (NO implementar ahora)

- **Seccomp real en Linux:** Implementar `apply_kernel_hardening()` con BPF filter para workers. Desbloquea tercera capa de defensa.
- **Decorador `@sandboxed`:** Anotación que fuerza `validate_skill()` en cualquier función que ejecute código de bundle. Previene R4.
- **Allowlist de módulos auditada:** Revisar `ALLOWED_MODULES` periódicamente. Módulos como `ctypes` (usado internamente en `apply_kernel_hardening`) y `inspect` (bloqueado en FORBIDDEN pero potencialmente necesario para bundles avanzados).
- **Fuzzing del sandbox:** Agregar test de fuzzing que genere código aleatorio y verifique que SecurityGuard nunca crashea (solo rechaza o acepta).
