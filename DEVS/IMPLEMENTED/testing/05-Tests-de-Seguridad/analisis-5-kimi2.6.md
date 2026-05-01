# Análisis Paso 5 — Seguridad Hardening (kimi2.6)

> Agente: kimi2.6 | Paso: 5 (Seguridad — Hardening) | Fecha: 2026-05-01

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `security_guard.py` existe | `ls src/services/` | ✅ | `security_guard.py`, 306 líneas |
| 2 | `test_security_guard.py` existe | `ls tests/unit/` | ✅ | 15 tests, 100% pass |
| 3 | SE5.13-SE5.16 pasan | `pytest tests/unit/test_security_guard.py -v` | ✅ | 4/4 pass en 14.68s |
| 4 | `FORBIDDEN_MODULES` contiene 20 módulos | `src/services/security_guard.py:19-41` | ✅ | os, subprocess, shutil, socket, ctypes, sys, importlib, inspect, gc, urllib, requests, httpx, aiohttp, urllib3, http, ftplib, mmap |
| 5 | `FORBIDDEN_CALLS` contiene 5 funciones | `src/services/security_guard.py:73` | ✅ | eval, exec, compile, open, __import__ |
| 6 | `_create_safe_builtins()` restringe `__import__` | `security_guard.py:126-159` | ✅ | `_restricted_import` verifica allowlist + blacklist antes de delegar a `builtins.__import__` |
| 7 | Inyección cruda `__import__` en builtins NO existe | grep en `security_guard.py` | ❌ | Plan menciona líneas 142/221 con inyección directa. Código actual NO tiene eso. Fix ya aplicado |
| 8 | `RestrictedPython` bloquea `__builtins__` como nombre de var | Script `verify_sec.py` | ✅ | `Line 2: "__builtins__" is an invalid variable name because it starts with "_"` |
| 9 | Async non-system bloqueado | Script `verify_sec.py` | ✅ | `AsyncFunctionDef statements are not allowed` |
| 10 | Async system permitido | Script `verify_sec.py` | ✅ | `validate_skill` retorna True |
| 11 | `bundle_manager.py` inyecta `SecurityGuard` | `src/services/bundle_manager.py:54-57` | ✅ | `self.security_guard = security_guard or SecurityGuard()` |
| 12 | `is_system=True` para bundles FAP-CORE | `bundle_manager.py:89-95` | ✅ | Si `manifest.bundle_info.author == "FAP-CORE"` → `is_system = True` + `allowed_modules.add("src")` |
| 13 | `import_service.py` usa `execute()` para skills/flows | `import_service.py:292,324` | ✅ | `self.security_guard.execute(code, filename)` |
| 14 | `/api/bundles/security-config` expone listas | `src/api/routes/bundles.py:25-44` | ✅ | Retorna `allowed_modules`, `forbidden_modules`, `timeout_seconds`, `python_version` |
| 15 | Suite total = 489 tests | `pytest --co -q tests/` | ⚠️ | Plan dice 425; `phase-state.md` dice 455. Real: 489. Discrepancia numérica no explicada |
| 16 | `test_security_guard_escape.py` NO existe | `ls tests/unit/` | ❌ | Plan propone crearlo (SE5.17-SE5.18). No existe |
| 17 | SE5.1-SE5.10 (imports faltantes) NO existen | `grep -n "SE5\.[0-9]" tests/unit/test_security_guard.py` | ❌ | Solo SE5.13-SE5.16 presentes. Faltan 10 tests de imports/calls |
| 18 | SE5.11-SE5.12 (async system vs non-system) NO existen | Mismo grep | ❌ | No hay tests para async |

**Discrepancias encontradas:**

1. **Vulnerabilidad `__import__` ya fixeada.** Plan asume código vulnerable (líneas 142/221 inyectan `__import__` crudo). Código actual usa `_restricted_import` con allowlist+blacklist. Tests SE5.13-SE5.16 PASAN. No hay bug crítico activo. → **Resolución:** No aplicar fix de seguridad. Ejecutar tests diagnósticos para confirmar estado, luego documentar como regresión ya cubierta. Revisar si plan v3.1 refleja código pre-fix.

2. **Suite total 489 tests.** Plan dice 425; phase-state dice 455. Diferencia de +34/+64 tests no documentada. Posible causas: tests de pasos 2-4 ya parcialmente implementados, o conteo inicial erróneo en plan v3.0. → **Resolución:** Ejecutar `pytest --co` antes de cualquier gate de "+N tests" para baseline real.

3. **`test_security_guard_escape.py` ausente.** Plan propone 2 tests de escape (importlib dinámico, hex payload). Archivo no existe. → **Resolución:** Crear archivo y tests. Hex payload no aplica directo en Python source (no hay `eval` de hex), pero sí probar `importlib.import_module` como bypass.

4. **SE5.1-SE5.12 ausentes.** Plan lista 10 tests de imports/calls y 2 de async. No existen. Código SÍ los bloquea (verificado con script). → **Resolución:** Agregar tests faltantes a `test_security_guard.py` existente. No requieren fix de código.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Paso 5 NO modifica schema DB. No hay tablas nuevas ni migraciones requeridas.

- **Tablas relacionadas indirectamente (ya existentes):**
  - `bundle_imports` — auditoría de importaciones, RLS `bundle_imports_tenant_isolation`.
  - `skill_catalog` — almacena `code_source` (TEXT) de skills validados.
  - `agent_catalog` — referencia `bundle_id`.
  - `workflow_templates` — referencia `bundle_id`, campo `code_source` para flows Python.
  - `domain_events` — auditoría de ejecuciones (usado por flujos que invocan skills).

- **Integridad referencial:**
  - `bundle_id` en `agent_catalog`, `workflow_templates`, `skill_catalog` → `bundle_imports(id)` ON DELETE SET NULL. ✅
  - `org_id` FK implícita vía RLS (tenant isolation). ✅

- **RLS:**
  - `bundle_imports` tiene RLS activo. ✅
  - `skill_catalog`, `agent_catalog`, `workflow_templates` también RLS (verificadas en migraciones previas). ✅

- **Índices:**
  - `idx_bundle_imports_org`, `idx_bundle_imports_org_version` existen. ✅

- **Impacto en datos existentes:** Ninguno. Paso 5 es puro testing + hardening.

---

## 2️⃣ Análisis de Código (ETAPA 2)

**Archivos tocados/directamente relacionados:**
- `src/services/security_guard.py` (core)
- `tests/unit/test_security_guard.py` (expandir)
- `tests/unit/test_security_guard_escape.py` (crear)
- `src/services/bundle_manager.py` (consumidor)
- `src/services/import_service.py` (consumidor)
- `src/api/routes/bundles.py` (endpoint expone config)

**Funciones/clases:**
- `SecurityGuard.__init__()` — firma: `timeout_seconds=30, allowed_modules=None, forbidden_modules=None, is_system=False`. ✅
- `SecurityGuard.validate_skill(source_code, filename)` — AST scan + compilación condicional. ✅
- `SecurityGuard._create_safe_builtins()` — crea dict safe con `_restricted_import`. Nuevo en código actual (no en plan). ✅
- `SecurityGuard.execute(source_code, filename)` — valida + ejecuta en globals restringidos o reales. ✅
- `SecurityGuard._scan_ast()` — detecta Import, ImportFrom, Call( Name | Attribute ). ✅
- `SecurityGuard._check_module()` — blacklist + allowlist. ✅
- `SecurityGuard._verify_compilation()` — `compile_restricted` + dry-run exec con timeout en ThreadPoolExecutor. ✅
- `SecurityGuard.apply_kernel_hardening()` — no-op en Windows, placeholder Seccomp en Linux. ✅

**Patrones:**
- Singleton no aplicado (cada `BundleManager` crea su `SecurityGuard`). Bajo overhead, acceptable.
- Timeout vía `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout)`. No usa `pytest-timeout` interno. Worker puede quedar zombie en loop infinito (`shutdown(wait=False)`). Patrón conocido.
- Bifurcación `is_system`: system bundles bypass RestrictedPython pero NO bypass AST scan. Correcto.

**Duplicación:**
- `FORBIDDEN_MODULES` y `ALLOWED_MODULES` hardcodeados. No hay carga dinámica de config. Tolerable para MVP.

**Calidad:**
- Complejidad ciclomática de `_scan_ast` es moderada (3 tipos de nodo + anidación Call). Manejable.
- `_verify_compilation` usa closure + executor anidado. Complejidad alta pero aislada.

**Imports/dependencias:**
- `RestrictedPython>=7.0` en `pyproject.toml`. ✅
- `safe_builtins` de RestrictedPython usado. ✅
- `concurrent.futures` para timeout. ✅

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Endpoints:**
- `GET /api/bundles/security-config` — expone `ALLOWED_MODULES`, `FORBIDDEN_MODULES`, `timeout_seconds`, `python_version`. Sin auth adicional más allá de `require_org_id`. Riesgo infoleak mínimo (attack surface disclosure).
- `POST /api/bundles/import` — recibe ZIP, `BundleManager` valida seguridad vía `validate_skill` en skills/flows Python. Si falla → HTTP 400 con `SecurityError`. ✅
- `POST /api/bundles/validate` — dry-run, mismo path de validación sin DB write. ✅

**Middleware:**
- `require_org_id` aplica a todos los endpoints de bundles. ✅
- No hay middleware de rate-limit específico para `/import`. Riesgo: upload masivo de ZIPs maliciosos para DoS del sandbox (CPU timeout 30s * N requests).

**Flujo de datos:**
1. Cliente sube ZIP.
2. `BundleManager.process_zip()` extrae en memoria.
3. Para cada `.py` en `skills/` y `flows/`, invoca `security_guard.validate_skill()`.
4. Si bundle FAP-CORE, `is_system=True` → permite async + módulo `src`.
5. `ImportService` registra skills/flows vía `security_guard.execute()`.
6. `execute()` compila y corre código en sandbox (non-system) o builtins reales (system).

**Contratos:**
- `validate_skill` retorna `bool` (True) o raise `SecurityError`.
- `execute` retorna `Dict[str, Any]` (globals) o raise `SecurityError`.
- `SecurityError` mensajes incluyen contexto: `Forbidden import 'X'`, `Forbidden function call 'Y'`, `timeout after Zs`.

**Error handling:**
- `bundles.py` captura `SecurityError` → HTTP 400. ✅
- `bundle_manager.py` captura `SecurityError` → `BundleError` con contexto. ✅
- `import_service.py` en `_register_skills/_register_flows`: loguea error y continúa (`continue`). **⚠️ Skill/flow fallido se ignora silenciosamente sin reportar al usuario en response HTTP.** Gap de UX.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

**Flujo completo:**
```
Usuario (CLI/Web) → POST /api/bundles/import
  → FastAPI → BundleManager.process_zip()
    → SecurityGuard.validate_skill() (AST + RestrictedPython)
      → ImportService._register_skills/_register_flows()
        → SecurityGuard.execute() (sandbox o system)
          → ToolRegistry / FlowRegistry (memoria)
            → Disponible para ejecución por agentes
```

**Coherencia:**
- Validación en importación + ejecución en registro = doble barrera. ✅
- `is_system` consistente entre `validate_skill` y `execute` (misma instancia `SecurityGuard`). ✅
- `security-config` endpoint permite al CLI sincronizar validación local. ✅

**Gaps/Frictions:**
1. **Skill fallido en importación se ignora.** `_register_skills` hace `continue` en excepción sin acumular errores en `BundleRPCResult`. Usuario no sabe qué skills fallaron.
2. **No hay pre-validación local en CLI.** `fap` no tiene comando para validar un `.py` contra la config del servidor antes de empaquetar ZIP.
3. **Rate-limit ausente en `/import`.** Sin protección contra fuzzing del sandbox.

**DX & Tooling (OBLIGATORIO):**

```markdown
### Herramienta Propuesta: `fap bundle-sec-check`
- **Qué automatiza:** Validación local de skills/flows Python contra las mismas reglas de seguridad del servidor. Elimina ciclo de subir ZIP → fallar → corregir → repetir.
- **Tipo:** CLI command
- **Cómo se usa:** `fap bundle-sec-check ./mi_bundle.zip` o `fap bundle-sec-check ./skills/mi_skill.py --org-id xyz`. Descarga config vía `GET /security-config` y corre `SecurityGuard.validate_skill()` localmente.
- **Impacto para el usuario final:** Deja de subir bundles inválidos. Reduce feedback loop de minutos a segundos.
- **Prioridad:** Tarea 0 — implementar antes que tests faltantes. Provee base para dogfooding de los propios tests de seguridad.
```

---

## 5️⃣ Criterios de Aceptación

Lista binaria verificable:

- ✅ [DATA] Ninguna migración requerida. Schema existente soporta auditoría de bundles.
- ✅ [CODE] `SecurityGuard` mantiene firma pública estable (`validate_skill`, `execute`, `__init__`).
- ✅ [CODE] `_create_safe_builtins()` restringe `__import__` sin inyección cruda.
- ✅ [CODE] `FORBIDDEN_MODULES` incluye subprocess, shutil, ctypes, socket, gc, inspect, requests, importlib.
- ✅ [CODE] `FORBIDDEN_CALLS` incluye eval, exec, compile, open, __import__.
- ✅ [BACKEND] Endpoint `/security-config` responde con listas ordenadas y timeout.
- ✅ [BACKEND] `POST /import` retorna HTTP 400 ante `SecurityError`.
- ✅ [BACKEND] `BundleManager` propaga `is_system=True` solo para author `FAP-CORE`.
- ❌ [BACKEND] `_register_skills` no reporta fallos individuales al usuario (gap conocido).
- ❌ [FULLSTACK] No existe `fap bundle-sec-check` para pre-validación local.
- ❌ [FULLSTACK] No existe rate-limit en `/import`.
- ❌ [DX] `test_security_guard.py` cubre solo 15/27 tests propuestos (faltan SE5.1-SE5.12, SE5.17-SE5.18).
- ✅ [DX] Suite total baseline conocida: 489 tests (re-baseline antes de medir "+N").

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Plan obsoleto vs código real (vuln `__import__`) | Media | Plan v3.1 describe vulnerabilidad ya corregida. Implementador podría perder tiempo re-fixeando algo sano. | Verificar `security_guard.py` actual antes de aplicar cualquier fix. Ejecutar SE5.13-SE5.16 como regresión, no diagnóstico. |
| Infoleak por `/security-config` | Baja | Expone `ALLOWED_MODULES` y `FORBIDDEN_MODULES` a cualquier usuario autenticado. Facilita reconocimiento de attack surface. | No exponer listas completas; retornar hash o versión de config. O mover endpoint a rol admin. |
| Zombie threads en sandbox timeout | Media | `ThreadPoolExecutor.shutdown(wait=False)` no mata worker en loop infinito. Acumulación de threads bajo carga. | Migrar a `ProcessPoolExecutor` o `multiprocessing` con `terminate()`. Evaluar costo en Windows. |
| Skills fallidos silenciosos en import | Media | `_register_skills` hace `continue` sin acumular errores. Usuario cree que importó todo. | Acumular errores en `BundleRPCResult.warnings` o `failed_skills`. |
| FAP-CORE bundle bypass | Media | `is_system=True` desactiva RestrictedPython. Si comprometen clave de firma/author "FAP-CORE", sandbox desaparece. | Agregar firma criptográfica de bundles system + validación de certificado FAP-CORE. Fuera de scope MVP. |
| Discrepancia conteo tests (489 vs 425/455) | Baja | Baseline mal documentada. Gates de "+N tests" se vuelven inconsistentes. | Re-ejecutar `pytest --co` al inicio del paso y documentar baseline real. |

---

## 7️⃣ Plan de Implementación

> [!IMPORTANT]
> Cada tarea incluye verificación inline.

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap bundle-sec-check` CLI | FULLSTACK/DX | Media | 2h | Ninguna | → verificar: `fap bundle-sec-check ./tests/data/sample_bundle.zip` ejecuta sin error y reporta "Security validation passed" o lista de fallos. |
| 1 | Agregar SE5.1-SE5.10 a `test_security_guard.py` | CODE | Baja | 1h | Tarea 0 | → verificar: `pytest tests/unit/test_security_guard.py -k "se5_1 or se5_2 or se5_3 or se5_4 or se5_5 or se5_6 or se5_7 or se5_8 or se5_9 or se5_10"` → 10 pass. |
| 2 | Agregar SE5.11-SE5.12 (async system/non-system) a `test_security_guard.py` | CODE | Baja | 0.5h | Tarea 1 | → verificar: `pytest tests/unit/test_security_guard.py -k "se5_11 or se5_12"` → 2 pass. |
| 3 | Crear `tests/unit/test_security_guard_escape.py` con SE5.17-SE5.18 | CODE | Media | 1h | Tarea 1 | → verificar: `pytest tests/unit/test_security_guard_escape.py -v` → 2 pass. |
| 4 | Documentar discrepancia plan vs código en análisis y actualizar gates | FULLSTACK | Baja | 0.5h | Tarea 1-3 | → verificar: `grep -A5 "Discrepancia" DEVS/IN_PROGRESS/analisis-5-kimi2.6.md` presente. Gate de paso 5 no exige fix de `security_guard.py` (ya sano). |
| 5 | Re-baseline suite: contar tests exactos y ajustar gates | CODE | Baja | 0.5h | Ninguna | → verificar: `pytest --co -q tests/ | tail -1` → número documentado en salida del paso. |
| 6 | Ejecutar suite completa: `pytest tests/` | FULLSTACK | Baja | 1h | Tareas 1-3 | → verificar: 0 failures, 0 errors. Baseline actual + tests nuevos = 100% pass. |
| 7 | Opcional: acumular errores de skill/flow en `BundleRPCResult` | BACKEND | Media | 1.5h | Tarea 6 | → verificar: `pytest tests/integration/test_bundle_cli_validate.py -v` o test E2E con ZIP inválido → response incluye `failed_skills` list no vacío. |

**Tiempo total estimado:** 7 horas (6h obligatorias + 1.5h opcional).

---

## 🔮 Roadmap (NO implementar ahora)

- **Firma criptográfica de bundles FAP-CORE:** Reemplazar trust por `author == "FAP-CORE"` con verificación de certificado/clave pública. Bloquea escalada si autor string spoofeado.
- **Rate-limit en `/import`:** Middleware de límite de requests/min por `org_id` para prevenir DoS de sandbox.
- **Sandbox por proceso:** Reemplazar `ThreadPoolExecutor` por `multiprocessing.Process` con `terminate()` para matar loops infinitos de verdad. Requiere serialización de código.
- **Config dinámica de seguridad:** Mover `ALLOWED_MODULES`/`FORBIDDEN_MODULES` a tabla DB o settings por-tenant en lugar de constantes hardcodeadas.
- **Pre-validación local en CLI:** Extender `fap bundle-sec-check` para soportar validación offline sin llamar al servidor (embeber lógica de `SecurityGuard` en CLI).

---

## 🚫 Reglas de Oro — Cumplimiento

- ✅ Análisis accionable y específico. Ninguna sección genérica.
- ✅ TODO verificado contra código real. Script `verify_sec.py` ejecutado.
- ✅ Ambigüedad señalada: hex payload, zombie threads, skills silenciosos.
- ✅ Plan contradice código → código gana. Vuln `__import__` ya fixeada documentada.
- ✅ Coherente con `phase-state.md`: pasos 0-1 completados, paso 2-4 pendientes.
- ✅ TODO el paso 5 (sub-pasos 5.1-5.4) cubierto.
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX.
- ✅ ≥ 1 herramienta DX propuesta: `fap bundle-sec-check`.
- ✅ Cada tarea con verificación inline.
- ✅ Suposiciones no verificadas ≤ 2: (1) Hex payload no aplica directo en Python source. (2) Worker zombie asumido por documentación de `shutdown(wait=False)`.
- ✅ Estimación de tiempo por tarea y total.
