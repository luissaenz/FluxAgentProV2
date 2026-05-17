# 🏛️ ANÁLISIS TÉCNICO FINAL — PASO 11: Estabilización Crítica y Fixes de Arquitectura

**Fase:** guiAgentGenerator  
**Fecha:** 2026-05-16  
**Objetivo:** Consolidar los análisis de los agentes y definir el plan de acción para resolver las discrepancias críticas identificadas.

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| dsfm | ✅ | 6 | fap templates check | ✅ | 4.8 |
| g3f | ✅ | 3 | fap-diag-tests | ✅ | 4.0 |
| lgn | ✅ | 4 | fap validate-builder-fixes | ✅ | 3.8 |
| mm2.5 | ✅ | 6 | fap test-builder run --fix-mocks | ✅ | 4.2 |
| qwen | ✅ | 4 | fap doctor builder | ✅ | 4.6 |
| step | ✅ | 6 | fap test-builder + validate_builder_nav_advanced.py | ✅ | 4.8 |
| tnt | ✅ | 4 | fap validate-builder-fixes | ✅ | 3.8 |
| X (Kilo) | ✅ | 5 | seed_idempotency_checker | ✅ | 3.5 |

**Promedio:** 4.1/5

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **ID-C02:** `templates_seed.py` no usa `ON CONFLICT` para idempotencia real | Todos | ✅ `src/cli/commands/templates_seed.py:183-206` | Cambiar a `INSERT ... ON CONFLICT DO NOTHING` vía `db.rpc()` o `db.insert().on_conflict().do_nothing()` |
| 2 | **ID-C03:** `BuilderBreadcrumb` desconectado del estado de tabs | Todos | ✅ `dashboard/components/builder/BuilderBreadcrumb.tsx:18`, `page.tsx:9`, `BuilderLayout.tsx:56` | Sincronizar via Context API o query params (`?tab=`) |
| 3 | **ID-C04:** Tests fallan por mocks inyectados incorrectamente | Todos | ✅ `tests/e2e/test_builder_scenarios.py:176-186`, `conftest.py:117-126` | Unificar mocks en `conftest.py` con `autouse=True` y parchear puntos de uso |
| 4 | **ID-023:** `zodResolver` en `AgentForm.tsx` sin validación de longitud mínima | dsfm, lgn, tnt, X | ✅ `dashboard/components/builder/AgentForm.tsx:33-45` | Agregar `.min(10)` a `goal` y `backstory` en Zod schema |
| 5 | **ID-051:** Patch points en `conftest.py` no cubren todos los imports | dsfm, mm2.5, step, qwen, X | ✅ `tests/conftest.py:117-126` | Agregar parches para `src.services.import_service.*` y usar `monkeypatch.setattr` |
| 6 | **ID-052:** `global_llm_mock` autouse puede romper suites no-builder | dsfm, mm2.5, step, X | ✅ `tests/conftest.py:276-305` | Limitar a tests con `@pytest.mark.llm_mocked` o mover a fixture exclusiva |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo del paso:** Resolver las discrepancias críticas identificadas en la fase `guiAgentGenerator` que bloquean la ejecución de la suite de tests E2E y comprometen la estabilidad del builder.

**Correcciones críticas al plan original:**
- El plan asume que `templates_seed.py` usa `ON CONFLICT`, pero el código real usa SELECT+INSERT. Se implementará `ON CONFLICT DO NOTHING`.
- El plan no menciona la desincronización entre `BuilderBreadcrumb` y el estado de tabs. Se implementará sincronización vía Context API.
- El plan no aborda los problemas de mocks en tests. Se unificarán los mocks en `conftest.py` con `autouse=True`.

**Decisión sobre herramienta DX seleccionada:** Se selecciona **`fap doctor builder`** (propuesta de qwen) como herramienta de diagnóstico centralizada, ya que verifica los 6 fixes críticos en un solo comando. Complementariamente, se utiliza **`fap test-builder`** (existente) para ejecutar la suite de tests una vez aplicados los fixes.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path
1. Ejecutar `fap templates seed` (idempotente) → crea/actualiza 8 templates system.
2. Acceder a `/builder` → se carga `BuilderLayout` con estado `activeTab='agent-form'`.
3. Cambiar de pestaña → `activeTab` se actualiza → `BuilderBreadcrumb` refleja el cambio.
4. Completar formulario → guardar agente → persistir en `agent_catalog`.
5. Ejecutar `fap test-builder run` → pasa 32/32 escenarios.

### Edge Cases MVP
- Ejecución concurrente de `fap templates seed` → debe manejar carrera con `ON CONFLICT`.
- Fallo de conexión a Supabase durante seed → manejar error con `HTTPException(503)`.
- Cambio de pestaña durante carga asíncrona → breadcrumb debe esperar a que el estado se estabilice.

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| Ruta real | Tipo de cambio | Descripción | Interfaces clave | Patrones a seguir |
|---|---|---|---|---|
| `src/cli/commands/templates_seed.py` | Modificación | Cambiar SELECT+INSERT por `INSERT ... ON CONFLICT DO NOTHING` | `def seed_templates(dry_run: bool, reset: bool) -> None` | `src/cli/commands/seed_bundle.py` (patrón de idempotencia) |
| `dashboard/components/builder/BuilderBreadcrumb.tsx` | Modificación | Usar `useBuilderTab()` hook para obtener `activeTab` | `activeTab: string` desde contexto | `dashboard/components/builder/BuilderLayout.tsx` (patrón useState) |
| `dashboard/components/builder/BuilderLayout.tsx` | Modificación | Exponer `activeTab` y `setActiveTab` via Context API | `BuilderTabContext.Provider` | `dashboard/components/builder/BuilderErrorBoundary.tsx` (patrón Context) |
| `dashboard/app/(app)/builder/page.tsx` | Modificación | Envolver contenido con `BuilderTabProvider` | `<BuilderTabProvider>{children}</BuilderTabProvider>` | `dashboard/app/(app)/layout.tsx` (patrón de providers) |
| `tests/conftest.py` | Modificación | Hacer `mock_service_client` autouse y agregar parches faltantes | `@pytest.fixture(autouse=True) def mock_all_db_clients(monkeypatch)` | `tests/conftest.py:112-140` (fixture existente) |
| `src/services/import_service.py` | Modificación | Agregar catch explícito de `TypeError`/`MagicMock` en `_check_version_guard` | `if not isinstance(current_version_str, str): raise BundleError(...)` | `src/services/import_service.py:167-171` (patrón fail-fast) |
| `dashboard/package.json` | Modificación | Pin Zod a v3 o migrar schema a v4 | `"zod": "^3.24.0"` | `dashboard/package.json` existente |
| `dashboard/components/builder/AgentForm.tsx` | Modificación | Cambiar `llmProvider: z.enum(...)` a `z.string()` y agregar `.min(10)` a `goal`/`backstory` | `z.object({ goal: z.string().min(10), backstory: z.string().min(10), ... })` | `dashboard/components/builder/TemplatePicker.tsx` (patrón de validación) |
| `scripts/validate_builder_mocks.py` | Creación | Script de diagnóstico para verificar mocks | `def run(dry_run: bool) -> int` | `scripts/cleanup_db.py` (patrón de scripts) |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap doctor builder
- **Qué automatiza:** Diagnóstica los 6 fixes críticos del Paso 11 en un solo comando.
- **Tipo:** CLI command (extensión de `fap test-builder`)
- **Ubicación:** `src/cli/commands/doctor_builder.py`
- **Cómo se usa:** `uv run fap doctor builder` — ejecuta checks secuenciales y reporta OK/FAIL.
- **Impacto para el usuario final:** Evita ejecutar 6 comandos separados para verificar estabilidad.
- **El implementador DEBE usarla** antes de ejecutar el resto de tareas.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **[Decisión]:** Usar `INSERT ... ON CONFLICT DO NOTHING` para idempotencia en `templates_seed.py`.  
   **Justificación:** Elimina la susceptibilidad a condiciones de carrera entre ejecuciones concurrentes y es más eficiente que SELECT+INSERT.

2. **[Decisión]:** Sincronizar breadcrumbs via Context API (`BuilderTabContext`) en lugar de URL query params.  
   **Justificación:** Más simple y mantiene el estado interno del builder sin depender de la URL, posponiendo el deep linking para el paso 9.

3. **[Corrección al plan]:** El plan no menciona que `mock_service_client` en `conftest.py` no es autouse, causando que los mocks no se apliquen globalmente. Se implementará `autouse=True`.

4. **[Corrección al plan]:** El plan asume que `zodResolver` en `AgentForm.tsx` es compatible con Zod v4, pero hay errores de tipo. Se pin Zod a v3 (`^3.24.0`) para mantener compatibilidad.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Tabla `agent_templates` existe con unique index parcial en `(name) WHERE is_system = TRUE`
✅ [DATA] `fap templates seed` ejecutable N veces sin error ni duplicados
✅ [CODE] `BuilderBreadcrumb` refleja cambios de tab en tiempo real
✅ [CODE] `tsc --noEmit` sin errores en componentes del builder
✅ [CODE] `AgentForm.tsx` compila con resolver de Zod sin warnings de tipo
✅ [BACKEND] `fap test-builder run` pasa 32/32 escenarios
✅ [BACKEND] Endpoints de templates manejan errores de DB con 503
✅ [FULLSTACK] Breadcrumb muestra tab activo correctamente en UI
✅ [DX] `fap doctor builder` ejecuta sin errores y reporta estado de los 6 fixes
```

**Funcionales:**
- [ ] Crear agente con formulario y guardar en Supabase.
- [ ] Sincronizar breadcrumb con tab activo.
- [ ] Ejecutar suite de tests E2E completa.

**Técnicos:**
- [ ] Cobertura de tests ≥ 90%.
- [ ] TypeScript sin errores en componentes del builder.
- [ ] Seed idempotente ejecutado 3 veces consecutivas sin errores.

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap doctor builder` | Media | 0.5h | Ninguna |
| 1 | Fix DB Seed idempotencia | Baja | 0.5h | Tarea 0 |
| 2 | Sync Breadcrumbs | Media | 1h | Tarea 0 |
| 3 | Fix Test Suite (mocks globales) | Alta | 2h | Tarea 0 |
| 4 | TypeScript Integrity (Zod) | Baja | 0.5h | Tarea 0 |
| 5 | Mocking Refactor + Regression Audit | Media | 1.5h | Tarea 0, 3 |
| **TOTAL** | | | **6 horas** | |

> [!IMPORTANT]  
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tests aprueban falsamente | Alta | Mock patches en targets incorrectos | Refactor patch targets a módulos consumidores; verificar que `execute.called` sea `True` |
| Race condition en seed | Media | SELECT + INSERT no atómico | Usar `ON CONFLICT` o `upsert` atómico |
| global_llm_mock rompe tests de otros equipos | Alta | `autouse=True` sin scope="session" | Scope="session" o mover a fixture exclusiva de builder tests |
| Breadcrumb fix rompe layout existente | Media | Cambio estructural en composición page.tsx/BuilderLayout | Mover breadcrumb DENTRO de BuilderLayout, no levantarlo a page.tsx |
| zodResolver rejection en producción | Baja | Select value inesperado fuera del enum | Validar valor en `onValueChange` antes de `setValue` |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Crear agente con formulario | `{role: "test", goal: "test goal", backstory: "test backstory", ...}` | `201 Created` con `role="test"` y `created_at` |
| TP-2 | Cambiar tab a "Crew Canvas" | Interacción UI → `setActiveTab("crew-canvas")` | Breadcrumb muestra "Crew Canvas" |
| TP-3 | Ejecutar `fap templates seed` 3 veces | `uv run fap templates seed` (3 ejecuciones) | `exit code 0` en todas, `skipped` aumenta, `inserted=0` |
| TP-4 | Importar ZIP corrupto | `POST /api/bundles/import` con ZIP inválido | `400 Bad Request` |
| TP-5 | `fap doctor builder` | `uv run fap doctor builder` | Reporte con 6 checks OK |
| TP-6 | `tsc --noEmit` en dashboard | `cd dashboard && npx tsc --noEmit` | `exit code 0` |

**Comando para ejecutar tests:**  
- Unit: `uv run pytest tests/unit/ -v --timeout=60`  
- Integration: `uv run pytest tests/integration/ -v --timeout=60`  
- E2E: `uv run fap test-builder run`

---

## 💾 Archivo de Salida

**Destino:** `/home/daniel/develop/Personal/FluxAgentProV2/DEVS/IN_PROGRESS/analisis-FINAL.md`

> [!IMPORTANT]  
> **REGLA DE ORO:** Único archivo permitido crear/modificar = `{paths.devs_in_progress}/analisis-FINAL.md`

---

## 📊 Métrica de Calidad del FINAL

| Métrica | Estado |
|:---|:---|
| `proyecto-config.json` leído antes de generar | ✅ 100% |
| Discrepancias consolidadas con resolución | ✅ 6/6 |
| Correcciones al plan documentadas | ✅ Todas encontradas |
| Propuesta DX incluida en §3 y Tarea 0 en §6 | ✅ Obligatorio |
| Criterio DX en §5 | ✅ Obligatorio |
| Secciones completadas | ✅ 9 secciones (0-8) |
| Casos de testing | ✅ ≥ 3 casos concretos |
| Tiempo estimado por tarea | ✅ 100% |

---