# 🏛️ ANÁLISIS UNIFICADO FINAL: PASO 3 — SEGURIDAD (SANDBOXING REAL)

**Estado:** Definido / Listo para Implementación
**Unificador:** Antigravity (Architect Flow)
**Paso:** 3 (Seguridad / Sandboxing)
**Origen:** Consolidación de 4 análisis (ATG, Kilo, OC, Ollama)
**Fecha:** 2026-04-28

---

## 0. Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|
| ATG | ✅ | 3 (Red, Sys, Timeout) | ✅ (grep pyproject, ls src) | 4.5 |
| Kilo | ✅ | 1 (Timeout) | ✅ (grep pyproject, read src) | 4.0 |
| OC | ✅ | 3 (RPC, Allowlist, Sys) | ✅ (grep migrations, grep src) | 5.0 |
| Ollama | ✅ | 4 (Red, Sys, Timeout, Integration) | ✅ (grep src, ls tests) | 4.8 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **Módulos de Red/Sys omitidos** en `FORBIDDEN_MODULES` | ATG, Ollama | ✅ `src/services/security_guard.py:20` | Añadir `urllib`, `http`, `ftplib`, `sys`, `requests`, `httpx` a la lista. |
| 2 | **Timeout no implementado** en validación/ejecución | Todos | ✅ `src/services/security_guard.py:42` | Implementar `concurrent.futures.ThreadPoolExecutor` para la fase de compilación/test-run. |
| 3 | **Integración ausente** en `BundleManager` | Ollama | ✅ `src/services/bundle_manager.py:102` | Inyectar `SecurityGuard` en `BundleManager` y llamar a `validate_skill` en `_parse_file_content`. |
| 4 | **RPC `import_bundle_atomic` NO existe** | OC | ✅ `supabase/migrations/` (falta 027) | Crear migración `0027_bundle_rpc.sql` con la lógica de transacción atómica. |
| 5 | **Allowlist de módulos omitido** | OC | ✅ `src/services/security_guard.py` | Implementar `ALLOWED_MODULES` (CrewAI, Pydantic, etc.) y validar en `_scan_ast`. |

---

## 1. Resumen Ejecutivo

Este paso tiene como objetivo blindar el sistema contra la ejecución de código malicioso contenido en los bundles de agentes. Aunque existe una base del `SecurityGuard`, se han detectado fallos críticos de integración y omisiones en las listas de bloqueo que invalidarían la seguridad del sistema en producción.

La unificación concluye que el diseño debe evolucionar de una validación pasiva (solo compilación) a una validación activa con **timeout real** e integración mandatoria en el pipeline de importación, garantizando que ninguna skill llegue a la base de datos sin pasar el sandbox. Se han detectado **3 correcciones críticas al plan original** respecto a la falta de la migración RPC y la integración ausente.

---

## 2. Diseño Funcional Consolidado

### Happy Path (Importación Segura)
1.  **Carga de ZIP**: El usuario envía el bundle via API.
2.  **Extracción e Integridad**: `BundleManager` valida tamaño y hashes SHA256.
3.  **Sandboxing Mandatorio**: Para cada archivo `.py` en `skills/`:
    -   **Scanner AST**: Detecta imports prohibidos (blacklist) y asegura que solo se usen módulos autorizados (allowlist).
    -   **Dunder Block**: Se impide el acceso a atributos que empiecen por `__` (introspección).
    -   **RestrictedPython**: Compilación con timeout de 30s.
4.  **Persistencia Atómica**: Si TODAS las skills son válidas, se invoca el RPC `import_bundle_atomic` para insertar agentes, flujos y skills en una única transacción.
5.  **Confirmación**: Retorno de éxito con el ID del bundle importado.

### Edge Cases MVP
-   **Skills con bucles infinitos**: Deben ser cortadas por el timeout de 30s durante la validación inicial.
-   **Fallo de una sola skill**: El bundle completo debe ser rechazado (transaccionalidad total).
-   **Módulos de Red**: Cualquier intento de `import requests` o `urllib` debe ser bloqueado estáticamente para prevenir exfiltración.

---

## 3. Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `src/services/security_guard.py` (Actualización)
-   **FORBIDDEN_MODULES**: Incluir `os`, `subprocess`, `shutil`, `socket`, `mmap`, `ctypes`, `importlib`, `inspect`, `gc`, `urllib`, `http`, `ftplib`, `sys`.
-   **ALLOWED_MODULES**: `{"crewai", "pydantic", "json", "re", "datetime", "math", "random", "typing"}`.
-   **Implementación de Timeout**:
    ```python
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(compile_restricted, source_code, ...)
        byte_code = future.result(timeout=self.timeout_seconds)
    ```

#### 2. `src/services/bundle_manager.py` (Refactor)
-   Modificar `__init__` para aceptar `SecurityGuard`.
-   En `_parse_file_content`, invocar `self.security_guard.validate_skill(code, filename)`.

#### 3. `supabase/migrations/0027_bundle_rpc.sql` (NUEVO)
-   Función `import_bundle_atomic(payload JSONB)`.
-   Lógica de Upsert coordinado para `agent_catalog`, `workflow_templates` y `skill_catalog`.

---

## 4. Decisiones Tecnológicas

1.  **Doble Capa (AST + RP)**: Se mantiene el escaneo AST previo a RestrictedPython por eficiencia (falla rápido) y para cubrir ataques de introspección que RP podría omitir en modo compilación pura.
2.  **Bloqueo de Red Total**: Se prohíbe explícitamente cualquier librería de red. Las skills deben ser puras o interactuar via MCP.
3.  **Transaccionalidad en DB**: Se elige usar una función PL/pgSQL (RPC) para garantizar que el catálogo no quede en estado inconsistente si falla la inserción del último agente de un bundle.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
-   [ ] Un bundle con `import os` en una skill es rechazado con error 400.
-   [ ] Un bundle con código sintácticamente inválido es rechazado.
-   [ ] Si la base de datos falla al insertar el segundo agente de tres, no se inserta ninguno (Rollback).
-   [ ] El usuario recibe el mensaje de error específico indicando qué archivo falló la validación.

### Técnicos
-   [ ] `SecurityGuard` utiliza el parámetro `timeout_seconds` para interrumpir validaciones largas.
-   [ ] `BundleManager` lanza `SecurityError` (o similar) que es capturado por el controlador de la API.
-   [ ] La migración 027 se aplica sin errores sobre la 026.
-   [ ] Los tests unitarios pasan al 100% incluyendo casos de bypass (dunder methods).

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. |
|---|---|---|---|
| 1 | **Migración 027**: Crear RPC `import_bundle_atomic` | Alta | 2.5h |
| 2 | **Refuerzo SecurityGuard**: Listas completas y validación AST mejorada | Media | 1.5h |
| 3 | **Implementación Timeout**: ThreadPoolExecutor en validation | Media | 1.5h |
| 4 | **Integración BundleManager**: Inyectar y llamar a SecurityGuard | Baja | 1h |
| 5 | **Suite de Tests de Integración**: Validar flujo completo bundle -> security -> RPC | Alta | 3h |
| **TOTAL** | | | **9.5h** |

---

## 7. Riesgos y Mitigaciones

-   **Riesgo**: `SecurityGuard` bloquea módulos necesarios para el funcionamiento interno de CrewAI.
    -   **Mitigación**: Añadir a `ALLOWED_MODULES` solo tras verificación de traza de error en tests de integración.
-   **Riesgo**: El implementador copia el plan §100 que dice "sys parcial" pero ignora que el diseño unificado pide "sys bloqueado".
    -   **Mitigación**: **MARCAR COMO PRIORIDAD** el seguimiento del Diseño Técnico Definitivo de este documento.

---

## 8. Testing Mínimo Viable (Casos de Prueba)

1.  **TP-S1**: Skill con `eval("__import__('os').system('ls')")` -> RECHAZO.
2.  **TP-S2**: Skill con `while True: pass` -> RECHAZO por TIMEOUT (30s).
3.  **TP-S3**: Skill con `from pydantic import BaseModel` -> ÉXITO (Allowlist).
4.  **TP-DB1**: Bundle con manifest inválido -> RECHAZO (Integrity).
5.  **TP-DB2**: Inserción de bundle -> Verificar que `skill_catalog` tiene el código fuente y `agent_catalog` tiene el `bundle_id` correcto.
