# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5.2 — PASO 11

**AGENTE:** Kilo  
**PASO:** 11 — Estabilización Crítica y Fixes de Arquitectura  
**Fecha análisis:** 2026-05-16  
**Fase:** guiAgentGenerator  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|--------------|--------|-----------|
| 1 | templates_seed.py existe | glob + read | ✅ | /src/cli/commands/templates_seed.py:1 |
| 2 | ON CONFLICT sin WHERE | grep en templates_seed.py | ❌ | No cláusula WHERE en upsert (líneas 180+) |
| 3 | BuilderBreadcrumb.tsx existe | glob | ✅ | dashboard/components/builder/BuilderBreadcrumb.tsx |
| 4 | AgentForm.tsx usa zodResolver | read líneas 1-50 | ⚠️ | import en línea 6, pero schema mismatch TS reportado |
| 5 | conftest.py existe | ls tests/ | ✅ | tests/conftest.py:1 (10970 bytes) |
| 6 | Migración 030_agent_templates.sql | ls migrations | ✅ | supabase/migrations/030_agent_templates.sql |
| 7 | agent_templates tabla schema | grep migración 030 | ✅ | columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system |
| 8 | RLS en templates | grep 030 | ⚠️ | No RLS explícito en migración (solo en plan) |
| 9 | fap CLI command templates seed | grep cli | ✅ | src/cli/commands/templates_seed.py registrado |
| 10 | Patch locations en tests | grep conftest + unit | ❌ | Mocks globales aplicados post-import (ID-051) |

**Discrepancias encontradas:**
- ❌ Plan menciona `templates_seed.py` pero archivo real está en `src/cli/commands/templates_seed.py` (estructura CLI anidada no documentada).
- ❌ Idempotencia rota: INSERT sin `ON CONFLICT DO NOTHING WHERE is_system=true` → múltiples seeds duplican filas.
- ❌ Path mismatch crítico: proyecto-config.json usa rutas Windows `D:\...` pero ejecución real en Linux `/home/daniel/...` → scripts CLI fallan en CI.
- ⚠️ AgentForm.tsx: zodResolver importado pero TS errors reportados en v23 → schema llmProvider enum vs string real.
- ⚠️ No existe `validate_builder_nav.py` mencionado en pasos posteriores pero referenced en ID-049.
- ❌ No hay tests unitarios para templates_seed.py idempotencia (cobertura 0%).

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ Schema: tabla `agent_templates` existe vía migración 030 (columnas exactas verificadas).
- ❌ Integridad: seed no es idempotente → riesgo de duplicados en `name` + `is_system=true` sin constraint UNIQUE.
- ❌ RLS policies: migración 030 NO incluye POLICY tenant_isolation ni lectura pública — contradice plan "RLS aplicado".
- ❌ Índices: ausente índice en `(category, is_system)` para filtros rápidos.
- ❌ Tipos: `suggested_tools TEXT[]` ok pero sin validación en seed (array vacío vs null).

**Impacto:** Seed repetido rompe `GET /api/templates` con duplicados; RLS faltante expone templates a tenants incorrectos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ Función principal: `seed_templates()` con firma `def seed_templates(reset: bool = False, dry_run: bool = False) -> int`
- ❌ Patrones: usa Typer + Rich pero ignora patrón de `src/cli/commands/*.py` (sin `app.add_typer` centralizado).
- ❌ Modularidad: TEMPLATES hardcodeado inline — duplicación con plan "8 templates predefinidos".
- ❌ Calidad: sin manejo de errores en `get_service_client()` → AttributeError si Supabase falla.
- ❌ Imports: `from src.db.session import get_service_client` — verificar si existe (no en ls src/db).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ Endpoint implícito: `fap templates seed` → llama seed interno.
- ❌ Error handling: sin HTTP 503 explícito para fallos DB (ID-010).
- ❌ Flujos: seed → DB → API `/api/templates` sin validación de conteo exacto 8.
- ❌ Contratos: payload seed no valida `soul_json` schema contra bundle v2.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ❌ Flujo end-to-end: seed idempotente falla → UI TemplatePicker muestra duplicados.
- ❌ Coherencia: breadcrumbs no sync con tab state real (ID-C03).
- ❌ Gaps: TS errors bloquean build; mocks rotos rompen 32 tests.

### Herramienta Propuesta: seed_idempotency_checker
- **Qué automatiza:** Verifica y fuerza idempotencia en seeds de templates antes de cada ejecución de fap templates seed.
- **Tipo:** CLI script (`scripts/seed_guard.py`)
- **Cómo se usa:** `python scripts/seed_guard.py --check` o integrado en `fap templates seed --guard`
- **Impacto para el usuario final:** Elimina duplicados manuales en DB y previene fallos en tests E2E.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

✅ [DATA] Tabla `agent_templates` existe con 8 filas is_system=true sin duplicados  
✅ [CODE] `templates_seed.py` ejecuta con `ON CONFLICT DO NOTHING` idempotente  
✅ [BACKEND] `fap templates seed` devuelve exit code 0 en 3 ejecuciones consecutivas  
✅ [FULLSTACK] Breadcrumbs cambian en tiempo real al switch de tabs  
✅ [DX] seed_idempotency_checker ejecuta sin errores y reduce duplicados a 0  

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Duplicados masivos en agent_templates | Alta | Seed sin WHERE en ON CONFLICT | Añadir WHERE is_system=true + unique constraint |
| Tests 100% rotos post-mock refactor | Alta | patch aplicado post-import | Usar pytest-mock con autouse fixtures en conftest |
| Path Windows en config.json | Media | Config generado en host Win | Normalizar paths relativos o detectar OS |
| RLS bypass en templates | Alta | Migración 030 sin POLICY | Añadir POLICY tenant_isolation inmediata |
| TS build bloqueado | Media | zodResolver + enum mismatch | Fix schema llmProvider a z.string() |

---

## 7️⃣ Plan de Implementación

**Tarea 0 siempre = DX & Tooling.**

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX & Tooling**: seed_idempotency_checker | `scripts/seed_guard.py` | `def run(dry_run: bool) -> int` | `scripts/cleanup_db.py :: main()` | DX | Baja | 0.5h | Ninguna | → verificar: `python scripts/seed_guard.py --help` ejecuta sin errores |
| 1 | Fix idempotencia seed | `src/cli/commands/templates_seed.py:180` | Añadir `ON CONFLICT (name, is_system) DO NOTHING WHERE is_system = true` | `src/cli/commands/seed_bundle.py` | DATA | Baja | 0.5h | Tarea 0 | → verificar: `fap templates seed` x3 sin duplicados |
| 2 | Sync Breadcrumbs state | `dashboard/components/builder/BuilderBreadcrumb.tsx` | `useTabState()` hook que lee active tab real | `dashboard/components/builder/BuilderLayout.tsx` | FULLSTACK | Media | 1h | Tarea 0 | → verificar: tab switch actualiza breadcrumb |
| 3 | Fix mocks conftest | `tests/conftest.py` | Mover `patch` a `pytest.fixture(autouse=True)` pre-import | `tests/conftest.py:50` | CODE | Media | 1h | Tarea 0 | → verificar: `uv run pytest tests/unit/ -k builder --tb=no` = 32/32 |
| 4 | Fix TS zodResolver | `dashboard/components/builder/AgentForm.tsx:33` | Cambiar `llmProvider: z.enum(...)` a `z.string()` | `dashboard/components/builder/TemplatePicker.tsx` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `npm run tsc --noEmit` sin errores |
| 5 | Regression audit | `tests/conftest.py` | Añadir `scope="session"` isolation markers | `tests/conftest.py:100` | CODE | Baja | 0.5h | Tarea 3 | → verificar: suites pre-existentes pasan intactas |

**Tiempo total estimado:** 4 horas

---

## 🔮 Roadmap

- Añadir unique constraint + index en agent_templates para prevenir futuros leaks.
- Centralizar todos los seeds en `scripts/seed_runner.py` con guard universal.
- Adoptar path normalization en proyecto-config.json generator.

**NOTA CRÍTICA (caveman):** Paso 11 es parche de bombero. Arquitectura rota desde origen (paths, seeds, mocks). Si no se resuelve raíz, pasos 12-15 fallarán en cadena. NO UNIFICAR — cada fix aislado.