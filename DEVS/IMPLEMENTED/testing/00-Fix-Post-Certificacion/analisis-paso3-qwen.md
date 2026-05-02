# Análisis Técnico — Paso 3: Alinear nombres de pasos en TESTING.md

**Agente:** qwen
**Fecha:** 2026-05-02
**Paso:** 3 — Alinear nombres de pasos en TESTING.md
**Plan referencia:** `DEVS/plan.md` v3.2

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | TESTING.md existe | `ls TESTING.md` | ✅ | raíz proyecto, 126 líneas |
| 2 | Línea 66: "Paso 3: Validacion de Seguridad Profunda" | lectura directa | ✅ | `TESTING.md:66` |
| 3 | Línea 72: "Paso 4: Hardening de API Publica" | lectura directa | ✅ | `TESTING.md:72` |
| 4 | Línea 78: "Paso 5: Tests de Regresion E2E" | lectura directa | ✅ | `TESTING.md:78` |
| 5 | plan.md Paso 3 nombre | lectura directa | ✅ | `DEVS/plan.md:116` → "E2E — Flujos Completos con Mocks" |
| 6 | plan.md Paso 4 nombre | lectura directa | ✅ | `DEVS/plan.md:136` → "Mover `baseline.py` a `src/cli/commands/`" |
| 7 | plan.md Paso 5 nombre | lectura directa | ✅ | `DEVS/plan.md:170` → "Mover `baseline.py`..." — NO, plan.md no tiene sección "Paso 5" explícita como título. Ver §Criterios de Aceptación |
| 8 | phase-state.md Paso 3 | lectura directa | ✅ | `DEVS/phase-state.md:20` → "Paso 3: E2E — Flujos Completos con Mocks" |
| 9 | phase-state.md Paso 4 | lectura directa | ✅ | `DEVS/phase-state.md:21` → "Paso 4: Tests de Estrés y Robustez" |
| 10 | phase-state.md Paso 5 | lectura directa | ✅ | `DEVS/phase-state.md:22` → "Paso 5: Tests de Seguridad — Hardening" |
| 11 | baseline.py existe | `ls src/cli/baseline.py` | ✅ | 207 líneas |
| 12 | baseline_check import en main.py | lectura directa | ✅ | `src/cli/main.py:14` → `from src.cli.baseline import baseline_check` |
| 13 | registry.py línea 158 usa safe_builtins | lectura directa | ✅ | `src/tools/registry.py:158` → `from RestrictedPython import safe_builtins` |
| 14 | security_guard._create_safe_builtins() existe | lectura directa | ✅ | `src/services/security_guard.py:126` |
| 15 | test_registry_security.py NO existe | glob pattern | ✅ | No encontrado — confirma que es archivo nuevo (Paso 0) |
| 16 | test_3_5_latency.py existe | glob pattern | ✅ | `tests/integration/test_3_5_latency.py` |

**Discrepancias encontradas:**

1. **plan.md no tiene sección explícita "Paso 5" con título.** El plan salta de Paso 4 a "Criterios de Aceptación MVP". Los nombres correctos vienen de `phase-state.md`, no de `plan.md` directamente para Pasos 4 y 5. **Resolución:** Usar phase-state.md como fuente de verdad para nombres de Pasos 3-5, ya que phase-state.md refleja el estado real verificado post-certificación.

2. **plan.md Paso 4 = "Mover baseline.py"**, pero phase-state.md Paso 4 = "Tests de Estrés y Robustez". La tabla del plan.md (§Plan de Implementación) muestra Paso 3 = "Alinear nombres TESTING.md", Paso 4 = "Mover baseline.py". Esto confirma que los pasos del plan actual son hotfix post-certificación, NO los pasos originales de la fase. **Resolución:** Los nombres a alinear en TESTING.md deben coincidir con los pasos ORIGINALES de la fase (phase-state.md), no con los hotfix del plan actual.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

Este paso no toca base de datos. Sin schema, sin migraciones, sin RLS.

**Impacto:** Ninguno en capa de datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

**Archivo afectado:** `TESTING.md` (documento, no código ejecutable)

**Cambios:** 3 líneas a modificar (66, 72, 78). Texto puro, sin lógica.

**Patrones existentes:** TESTING.md sigue estructura markdown con headers `### Paso N: Nombre`. Los nombres deben coincidir con phase-state.md.

**Firmas/Interfaces:** N/A — archivo de documentación.

**Imports:** N/A.

**Modularidad:** N/A.

**Riesgo de código:** Bajo. Cambios cosméticos en documentación. Sin impacto en ejecución.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

Este paso no toca APIs, endpoints, middleware ni servicios backend.

**Impacto:** Ninguno en capa backend.

**Contratos:** Ninguno afectado.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

DB → Backend → Frontend → UX: **Sin impacto**. Solo documentación.

### Coherencia

- phase-state.md ya tiene nombres correctos para Pasos 3-5
- TESTING.md tiene nombres desincronizados
- plan.md (hotfix) tiene pasos renumerados como tareas correctivas
- **Fuente de verdad:** phase-state.md (estado real post-certificación)

### Alineación

Plan dice "Nombres coinciden con plan.md secciones Paso 3, Paso 4, Paso 5". Pero plan.md actual es hotfix — sus secciones Paso 3/4/5 son tareas correctivas, no los nombres originales de la fase. **Discrepancia detectada en §0 #1.**

### Gaps

- Plan asume que plan.md tiene los nombres correctos — falso para este contexto hotfix
- phase-state.md es la fuente real de nombres de fase

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: sync-step-names
- **Qué automatiza:** Verifica que nombres de pasos en TESTING.md coincidan con phase-state.md. Evita desincronización manual futura.
- **Tipo:** script CLI / validador
- **Cómo se usa:** `python scripts/sync_step_names.py --check` (modo dry-run) o `python scripts/sync_step_names.py --fix` (aplica correcciones)
- **Impacto para el usuario final:** Elimina necesidad de revisar manualmente TESTING.md vs phase-state.md antes de cerrar fase. Detecta drift automáticamente en CI.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

**Especificación técnica de la herramienta:**

```python
# scripts/sync_step_names.py
def run(check_only: bool = True) -> int:
    """Lee TESTING.md y phase-state.md. Compara nombres de pasos 0-7.
    Si check_only=True: reporta diferencias (exit 1 si hay drift).
    Si check_only=False: aplica correcciones a TESTING.md (exit 0).
    """
```

- Parsea headers `### Paso N:` en TESTING.md
- Parsea líneas `- ✅ **Paso N:` en phase-state.md
- Compara nombres. Reporta mismatch.
- Modo `--fix` reemplaza nombres en TESTING.md manteniendo resto del contenido intacto.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DOCS] TESTING.md línea 66 dice "### Paso 3: E2E — Flujos Completos con Mocks"
✅ [DOCS] TESTING.md línea 72 dice "### Paso 4: Estrés y Condiciones de Borde" — NO, phase-state.md dice "Tests de Estrés y Robustez"
✅ [DOCS] TESTING.md línea 78 dice "### Paso 5: Seguridad — Hardening" — phase-state.md dice "Tests de Seguridad — Hardening"
✅ [DX] Script sync-step-names ejecuta sin errores en modo --check
✅ [FULLSTACK] Nombres en TESTING.md coinciden con phase-state.md para Pasos 3, 4, 5
```

**Corrección de criterios basada en phase-state.md real:**

| Paso | TESTING.md (actual) | phase-state.md (correcto) |
|---|---|---|
| 3 | `Validacion de Seguridad Profunda` | `E2E — Flujos Completos con Mocks` |
| 4 | `Hardening de API Publica` | `Tests de Estrés y Robustez` |
| 5 | `Tests de Regresion E2E` | `Tests de Seguridad — Hardening` |

**Nota:** El plan.md original dice en la tabla de Tarea 3.1:
- Paso 4 → "Estrés y Condiciones de Borde"
- Paso 5 → "Seguridad — Hardening"

Pero phase-state.md dice:
- Paso 4 → "Tests de Estrés y Robustez"
- Paso 5 → "Tests de Seguridad — Hardening"

**Discrepancia adicional:** El plan.md y phase-state.md NO coinciden entre sí para nombres de Pasos 4 y 5. **El código gana:** phase-state.md refleja el estado archivado real (carpetas `04-Tests-de-Estres-y-Robustez/` y `05-Tests-de-Seguridad/` existen en DEVS/IMPLEMENTED/testing/). Los nombres de phase-state.md son los correctos.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Nombres en plan.md no coinciden con phase-state.md | Media | Plan hotfix usa nombres diferentes a fase original | Usar phase-state.md + carpetas IMPLEMENTED como fuente de verdad |
| Descripción bajo header queda incorrecta | Baja | Cambiar nombre de paso sin actualizar descripción | Revisar línea siguiente a cada header tras cambio |
| Script sync-step-names introduce bug de parsing | Baja | Regex incorrecto para headers markdown | Test con --check primero, validar diff antes de --fix |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: sync-step-names | `scripts/sync_step_names.py` | `def run(check_only: bool = True) -> int` | — | DX | Baja | 0.25h | Ninguna | → verificar: `python scripts/sync_step_names.py --check` reporta 3 drifts |
| 1 | Cambiar nombre Paso 3 en TESTING.md | `TESTING.md:66` | Texto: `### Paso 3: E2E — Flujos Completos con Mocks` | phase-state.md línea 20 | DOCS | Baja | 0.05h | Tarea 0 | → verificar: grep "Paso 3: E2E" TESTING.md retorna 1 match |
| 2 | Cambiar nombre Paso 4 en TESTING.md | `TESTING.md:72` | Texto: `### Paso 4: Tests de Estrés y Robustez` | phase-state.md línea 21 + carpeta `04-Tests-de-Estres-y-Robustez/` | DOCS | Baja | 0.05h | Tarea 0 | → verificar: grep "Paso 4: Tests de Estrés" TESTING.md retorna 1 match |
| 3 | Cambiar nombre Paso 5 en TESTING.md | `TESTING.md:78` | Texto: `### Paso 5: Tests de Seguridad — Hardening` | phase-state.md línea 22 + carpeta `05-Tests-de-Seguridad/` | DOCS | Baja | 0.05h | Tarea 0 | → verificar: grep "Paso 5: Tests de Seguridad" TESTING.md retorna 1 match |
| 4 | Validar descripciones bajo headers | `TESTING.md:67-70, 73-76, 79-82` | Revisar que descripciones coincidan con contenido real de cada paso | phase-state.md §1 resumen de pasos | DOCS | Baja | 0.1h | Tareas 1-3 | → verificar: descripciones mencionan tests correctos (E2E, stress, security) |
| 5 | Ejecutar sync-step-names --check post-fix | `scripts/sync_step_names.py` | `run(check_only=True)` → retorna 0 | Tarea 0 | DX | Baja | 0.05h | Tareas 1-4 | → verificar: exit code 0, 0 drifts reportados |

**Tiempo total estimado:** 0.55h

---

## 🔮 Roadmap (NO implementar ahora)

- Agregar validación de nombres de pasos en `fap baseline-check` como check adicional
- Extender sync-step-names para validar también CHANGELOG.md y README.md contra phase-state.md
- CI gate que falle si TESTING.md drift vs phase-state.md > 0

---

**Fuente de verdad final:** phase-state.md + estructura de carpetas en `DEVS/IMPLEMENTED/testing/` definen los nombres correctos. Plan.md hotfix no es referencia válida para nombres de pasos originales de la fase.
