# 🧠 ANÁLISIS TÉCNICO — Paso 11: Estabilización Crítica y Fixes de Arquitectura

> **Agente:** g3f  
> **Paso:** 11  
> **Fase:** guiAgentGenerator  
> **Estado:** En Progreso  

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` | exists | ✅ | `supabase/migrations/030_agent_templates.sql:10` |
| 2 | Índice `idx_agent_templates_system_name` | exists (unique/partial) | ✅ | `supabase/migrations/030_agent_templates.sql:32` |
| 3 | `templates_seed.py` | current logic | ✅ | `src/cli/commands/templates_seed.py:183-195` (select then insert) |
| 4 | `BuilderBreadcrumb` hardcode | exists | ✅ | `dashboard/app/(app)/builder/page.tsx:9` (`activeTab="agent-form"`) |
| 5 | `AgentForm.tsx` | exists | ✅ | `dashboard/components/builder/AgentForm.tsx` |
| 6 | `conftest.py` | exists | ✅ | `tests/conftest.py` |
| 7 | `test_builder_scenarios.py` | local mocks | ✅ | `tests/e2e/test_builder_scenarios.py:192-262` |
| 8 | `agents.py` imports | direct import | ✅ | `src/api/routes/agents.py:13` (`from ...db.session import get_tenant_client`) |

**Discrepancias encontradas:**
1. **[TESTS] Patching inefectivo:** El plan identifica correctamente que `patch("src.db.session.get_tenant_client")` no funciona en `agents.py` debido al estilo de importación `from ... import ...`. Se debe parchear el namespace del router.
2. **[DB SEED] Idempotencia:** `templates_seed.py` ya intenta ser idempotente con un `select`. El fallo reportado en ID-C02 sugiere que este check falla o que se prefiere el uso de `ON CONFLICT` nativo para evitar race conditions.
3. **[FRONTEND] Breadcrumbs:** El componente `BuilderBreadcrumb` recibe `activeTab` como prop, pero el padre `page.tsx` lo tiene hardcodeado. `BuilderLayout` es quien realmente maneja las pestañas internas.

---

### 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Idempotencia en Seed:** La tabla `agent_templates` tiene un índice único parcial: `UNIQUE(name) WHERE is_system = TRUE`. 
  - **Problema:** Un `upsert` simple fallará en Postgres si no se especifica el predicado del índice en la cláusula `ON CONFLICT`.
  - **Resolución:** Mantener el patrón `select` + `insert` es seguro, pero si se desea `upsert`, se requiere SQL crudo o una configuración específica del cliente Supabase que no es trivial. Se optará por reforzar el `select` check y manejar el error de unicidad explícitamente para mayor robustez.

---

### 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Refactor de Mocks (Python):** 
  - Mover `fresh_db`, `db_cm`, `mock_select`, `mock_insert`, `mock_update`, `mock_delete` y `chain_response` de `tests/e2e/test_builder_scenarios.py` a `tests/conftest.py` como fixtures o funciones de utilidad.
  - Esto permitirá que otros tests de la fase `guiAgentGenerator` reutilicen la infraestructura de mocks sin duplicación.
- ✅ **TypeScript Integrity:**
  - El error en `AgentForm.tsx` se debe a que `zodResolver` espera que el tipo del esquema coincida con el tipo de los datos de `useForm`. Si el esquema tiene `.default()`, Zod infiere que el campo siempre existe, pero el tipo de TypeScript de la interfaz del Agente podría marcarlo como opcional.
  - **Firma:** Corregir en `dashboard/components/builder/AgentForm.tsx`.

---

### 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **Fix de Mocks en Routers:**
  - En `test_builder_scenarios.py`, cambiar todos los `patch("src.db.session.get_tenant_client", ...)` por:
    - `patch("src.api.routes.agents.get_tenant_client", ...)`
    - `patch("src.api.routes.templates.get_service_client", ...)`
    - `patch("src.api.routes.tools.get_service_client", ...)`
  - Esto garantiza que el mock se inyecte en el namespace donde se usa.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Sincronización de Breadcrumbs:**
  - **Flujo:** `BuilderLayout` (donde reside el estado de las pestañas) debe comunicar el cambio a `BuilderPage` o usar un store compartido. 
  - **Solución MVP:** Elevar el estado `activeTab` de `BuilderLayout` a `BuilderPage` y pasarlo a ambos componentes.
- ✅ **DX & Tooling:** El implementador se enfrenta a una suite de tests "rota". Necesitamos una herramienta que diagnostique EXACTAMENTE qué mocks están fallando antes de aplicar los fixes.

```
### Herramienta Propuesta: fap-diag-tests
- **Qué automatiza:** Escanea archivos de test y routers para detectar desajustes de patching (imports vs patch points).
- **Tipo:** Script de diagnóstico.
- **Cómo se usa:** `python scripts/diag_test_patching.py tests/e2e/test_builder_scenarios.py`
- **Impacto para el usuario final:** Identifica preventivamente fallos de inyección de mocks que causan AttributeError.
- **Prioridad:** Tarea 0 — Implementar antes que el resto del paso.
```

---

### 5️⃣ Criterios de Aceptación

- ✅ [DATA] `fap templates seed` no falla si los templates ya existen (idempotencia real).
- ✅ [CODE] `tests/conftest.py` contiene las fixtures `db_mock` y `mock_response`.
- ✅ [BACKEND] `test_builder_scenarios.py` usa patching por namespace de router.
- ✅ [FULLSTACK] Los Breadcrumbs cambian de texto al alternar entre "Agent Form" y "Crew Canvas".
- ✅ [DX] El script de diagnóstico identifica al menos 3 puntos de patching incorrectos en la suite actual.

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Regresión Global | Media | Cambios en `conftest.py` pueden afectar tests de fases anteriores. | Ejecutar suite completa `uv run pytest tests/` tras el refactor. |
| Fuga de Mocks | Alta | Un mock mal cerrado en `conftest.py` puede contaminar otros tests. | Usar fixtures con `yield` y asegurar limpieza en `teardown`. |
| Inconsistencia UI | Baja | Desincronización entre Query Params y estado de React. | Sincronizar estado via `useEffect` si se opta por la solución de URL. |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX Tooling**: Diag Patching | `scripts/diag_test_patching.py` | `def scan_file(path: str) -> List[str]` | — | DX | Media | 1h | Ninguna | `python scripts/diag_test_patching.py tests/e2e/test_builder_scenarios.py` |
| 1 | Refactor de fixtures globales | `tests/conftest.py` | fixtures: `db_mock`, `mock_query_chain` | `test_scenario_6_full_stack.py` | CODE | Media | 2h | Tarea 0 | `uv run pytest tests/e2e/test_builder_scenarios.py` (debe fallar menos) |
| 2 | Corregir Patching por Namespace | `tests/e2e/test_builder_scenarios.py` | `with patch("src.api.routes.agents.get_tenant_client", ...)` | — | BACKEND | Media | 1.5h | Tarea 1 | `fap test-builder run` |
| 3 | Fix Idempotencia Seed | `src/cli/commands/templates_seed.py` | `def seed_templates(dry_run, reset)` | — | DATA | Baja | 0.5h | Tarea 2 | `fap templates seed` (ejecutar 2 veces) |
| 4 | Sync Breadcrumbs en UI | `dashboard/app/(app)/builder/page.tsx` | Elevación de estado `activeTab` | `dashboard/app/(app)/integrations/page.tsx` | FULLSTACK | Media | 1h | Tarea 0 | Navegar en el builder y observar breadcrumbs |
| 5 | Fix TS y Eslint warnings | `dashboard/components/builder/AgentForm.tsx` | Corrección de tipos en `useForm` | — | CODE | Baja | 0.5h | Tarea 4 | `npm run lint` |

**Tiempo total estimado:** 6.5 horas

---

### 🔮 Roadmap (NO implementar ahora)

- Implementar `upsert` real en el cliente Supabase extendiendo `TenantClient`.
- Migrar toda la navegación del Builder a Query Params para permitir historial de navegación real.
