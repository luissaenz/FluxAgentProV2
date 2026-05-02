# Análisis Técnico — Paso 2: Fix `test_3_5_latency.py`

> **Agente:** kimi
> **Paso:** 2 — Fix `test_3_5_latency.py`
> **Fecha:** 2026-05-02
> **Origen:** `DEVS/plan.md` v3.2

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Archivo `tests/integration/test_3_5_latency.py` existe | `ls tests/integration/` | ✅ | Directorio listing confirma archivo presente (23671 bytes) |
| 2 | Clase `TestLatencyValidation` existe | Lectura completa archivo | ✅ | `class TestLatencyValidation:` línea 511 |
| 3 | Método `test_full_latency_validation` existe en línea 524 | Lectura completa | ✅ | `async def test_full_latency_validation(...)` línea 524 |
| 4 | `pytestmark = pytest.mark.skipif(...)` a nivel módulo ya existe | Lectura líneas 46-49 | ✅ | `pytestmark = pytest.mark.skipif(not SUPABASE_URL, reason="Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env")` |
| 5 | Variables `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` leídas vía `os.getenv` | Lectura líneas 42-44 | ✅ | `SUPABASE_URL = os.getenv("SUPABASE_URL")`, `SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` |
| 6 | `.env.example` define `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` | Lectura `.env.example` | ✅ | Líneas 2-4 |
| 7 | Makefile excluye latency test en `test-all` | Lectura Makefile línea 92 | ✅ | `$(PYTEST) tests/integration/ -v --timeout=60 --tb=short -k "not latency"` |
| 8 | `TESTING.md` documenta test como "Fallo conocido en CI" | Lectura TESTING.md línea 124 | ✅ | "test_3_5_latency.py: Fallo conocido en CI. Excluir con `-k 'not latency'`." |
| 9 | `pyproject.toml` tiene `pytest-timeout>=1.5.0` en dev deps | Lectura pyproject.toml línea 51 | ✅ | `"pytest-timeout>=1.5.0",` |
| 10 | `phase-state.md` registra decisión de arquitectura #7 sobre skipif | Lectura phase-state.md línea 146 | ✅ | "Fix `test_3_5_latency`: Skip condicional via `skipif` + mover a `tests/integration/`" |
| 11 | Test usa `load_dotenv()` en línea 36 | Lectura archivo | ✅ | `load_dotenv()` llamada antes de leer env vars |
| 12 | Fixtures `supabase_client` y `test_org_id` dependen de `SUPABASE_SERVICE_KEY` | Lectura líneas 485-502 | ✅ | `acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, ...)` |

**Discrepancias encontradas:**

**D1.** Plan pide `@pytest.mark.skipif` como decorador de clase/fn, pero código ya tiene `pytestmark` a nivel módulo.
- **Resolución:** `pytestmark` a nivel módulo ES el patrón correcto y más robusto para este caso. Aplica skip a TODOS los tests del módulo (incluyendo `test_clock_calibration`, `test_event_burst_handling`, `test_integrity_db_vs_received` y el `_main()` ejecutable). Un decorador solo en `TestLatencyValidation` dejaría `_main()` y helpers sin protección en ejecución directa. El código gana. No modificar estructura del skip.

**D2.** Plan pide verificar `SUPABASE_ANON_KEY`, pero el test realmente usa `SUPABASE_SERVICE_KEY`.
- **Resolución:** El test requiere `SUPABASE_SERVICE_KEY` (llamadas admin/RPC a `organizations` y `domain_events`). `SUPABASE_ANON_KEY` no se usa en ninguna parte del archivo. Agregar `SUPABASE_ANON_KEY` al skipif sería incorrecto y confuso. El código gana: mantener `SUPABASE_SERVICE_KEY`.

**D3.** Plan pide reason `"Requiere Supabase Realtime + DB real — plan.md P0 bug conocido"`, pero código actual tiene reason `"Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env"`.
- **Resolución:** El reason actual describe técnicamente qué falta. El reason del plan es más descriptivo del contexto de negocio (P0 bug conocido). Ambos son válidos. Sugerencia: mantener reason actual o fusionar. Dado que el usuario pidió NO UNIFICAR, documentar como discrepancia menor sin acción obligatoria.

**D4.** Plan menciona ubicación "Antes de la clase `TestLatencyValidation` o función `test_full_latency_validation`". El `pytestmark` actual está en línea 46, antes de la clase (línea 511) y antes de todas las funciones.
- **Resolución:** La ubicación actual cumple el propósito funcional. No requiere cambio.

**D5.** Plan dice "Fix `test_3_5_latency.py`" como si el archivo no tuviera skipif, pero el archivo YA fue fixeado en Paso 0 (Auditoría de Línea Base) según `phase-state.md` decisión #7 y validación de `00-Auditoria-de-Linea-Base/validacion.md`.
- **Resolución:** El paso 2 del plan v3.2 parece redundante con trabajo ya realizado en Paso 0. El fix real que falta es posiblemente alinear el skipif con la firma exacta que pide el plan (añadir chequeo de `SUPABASE_SERVICE_KEY` al skipif existente, que actualmente solo checkea `SUPABASE_URL`).

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**Tablas tocadas:**
- `organizations` — fixture `test_org_id` hace `SELECT id LIMIT 1` (línea 96)
- `domain_events` — CRUD directo: insert (warmup), delete (cleanup), count (integridad), subscribe vía Realtime (líneas 104-120, 356-371)

**Columnas usadas:**
- `organizations.id`
- `domain_events.id`, `org_id`, `aggregate_type`, `aggregate_id`, `event_type`, `correlation_id`, `payload`, `sequence`, `created_at`

**RLS:**
- Test usa `SUPABASE_SERVICE_KEY` (rol `service_role`), que bypassa RLS. No aplica verificación de policies.

**Índices necesarios:**
- `domain_events(aggregate_id)` — usado en `_count_events_in_db()` y `_cleanup_events()`. Verificar existencia en migraciones.
- `domain_events(aggregate_id, event_type)` — implícito en queries de filtrado.

**Tipos de datos:**
- `created_at` retornado como ISO-8601 string (con o sin `Z`). Helper `_iso_to_epoch()` maneja ambos formatos. ✅
- `sequence` como integer. ✅
- `payload` como jsonb — insertado como dict Python. ✅

**Diagrama ER (relevante):**
```
organizations (1) ──< (N) domain_events
```
Relación por `org_id`. Test asume que existe al menos 1 organización.

**Impacto en datos existentes:**
- Test inserta y elimina eventos con `aggregate_id` único (`lat-test-{uuid}`). Cleanup en `finally` bloque (líneas 538-539, 576-577, 614-615). Riesgo de datos residuales si test se interrumpe antes del cleanup.

---

## 2️⃣ Análisis de Código (ETAPA 2)

**Funciones/Clases:**

| Nombre | Tipo | Firma | Línea |
|---|---|---|---|
| `_iso_to_epoch` | fn | `(iso_str: str) -> float` | 79 |
| `_percentile` | fn | `(sorted_values: list[float], pct: float) -> float` | 85 |
| `_get_valid_org_id` | async fn | `(supabase: AsyncClient) -> str` | 94 |
| `_count_events_in_db` | async fn | `(supabase: AsyncClient, aggregate_id: str) -> int` | 102 |
| `_cleanup_events` | async fn | `(supabase: AsyncClient, aggregate_id: str) -> None` | 113 |
| `LatencyValidator` | class | `__init__(self, supabase: AsyncClient, task_id: str, org_id: str)` | 128 |
| `LatencyValidator.calibrate_clock` | async method | `() -> None` | 142 |
| `LatencyValidator.start_monitoring` | async method | `() -> None` | 186 |
| `LatencyValidator._on_event` | method | `(payload: dict[str, Any]) -> None` | 218 |
| `LatencyValidator.send_warmup_events` | async method | `() -> None` | 270 |
| `LatencyValidator.run_multi_crew_flow` | async method | `() -> None` | 280 |
| `LatencyValidator._emit_synthetic_events` | async method | `() -> None` | 300 |
| `LatencyValidator._insert_event` | async method | `(sequence: int, event_type: str) -> None` | 355 |
| `LatencyValidator.analyze_results` | async method | `() -> dict[str, Any]` | 375 |
| `LatencyValidator.close` | async method | `() -> None` | 469 |
| `supabase_client` | fixture | `() -> AsyncClient` | 484 |
| `test_org_id` | fixture | `() -> str` | 499 |
| `task_id` | fixture | `() -> str` | 505 |
| `TestLatencyValidation.test_clock_calibration` | async test | `(supabase_client, test_org_id)` | 515 |
| `TestLatencyValidation.test_full_latency_validation` | async test | `(supabase_client, test_org_id, task_id)` | 524 |
| `TestLatencyValidation.test_event_burst_handling` | async test | `(supabase_client, test_org_id, task_id)` | 543 |
| `TestLatencyValidation.test_integrity_db_vs_received` | async test | `(supabase_client, test_org_id, task_id)` | 580 |
| `_main` | async fn | `() -> None` | 623 |

**Patrones existentes vs nuevos:**
- **Patrón async/await:** Consistente con resto de tests integración (`test_mcp_resilience.py`, `test_handover_real.py`). Usa `pytest-asyncio` con modo auto.
- **Patrón fixture por función:** `supabase_client` scope=function, fresco por test. ✅ Correcto para aislamiento.
- **Patrón cleanup en finally:** Todos los tests usan `try/finally` con `validator.close()` y `_cleanup_events()`. ✅
- **Patrón skipif a nivel módulo:** Único en suite. Todos los demás tests de integración NO tienen skipif (busqueda con grep confirma: solo este archivo tiene `skipif`). Esto es apropiado dado que es el único test que requiere infraestructura externa real.

**Duplicación de código:**
- Los 4 métodos de test repiten el patrón `try/finally` + `validator.close()` + `_cleanup_events()`. No es duplicación grave — cada test tiene lógica de carga diferente en el `try`.

**Cohesión/Acoplamiento:**
- `LatencyValidator` tiene alta cohesión: un solo propósito (medir latencia Realtime). Acoplamiento con `MultiCrewFlow` (línea 285) y `EventStore` (líneas 302, 316, 329, 343) — ambos son del proyecto, no externos. Aceptable.
- Fallback a eventos sintéticos si `MultiCrewFlow` falla (líneas 293-298) mejora robustez.

**Imports exactos:**
```python
from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pytest
from dotenv import load_dotenv
from src.flows.multi_crew_flow import MultiCrewFlow
from supabase import AsyncClient, AsyncClientOptions, acreate_client
```

**Calidad:**
- Complejidad ciclomática de `analyze_results()` es moderada (~15 ramas). Aceptable para test.
- Magic numbers bien documentados como constantes (`P95_THRESHOLD_MS`, etc.).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Endpoints/APIs involucrados:**
- No hay endpoints HTTP propios en este test. Es test de infraestructura DB + Realtime.

**Middleware:**
- `SUPABASE_SERVICE_KEY` se usa directamente con `acreate_client()`. No pasa por middleware de auth de la aplicación.

**Flujo de datos:**
```
Test → EventStore.append_sync() → Supabase POST /rest/v1/domain_events
                                      ↓
Test ← Realtime WS ← Supabase Realtime ← DB trigger/notify
```

**Contratos:**
- RPC `get_server_time` debe existir en Supabase (línea 154). Si no existe, calibración falla silenciosamente con offset=0 (líneas 155-160). **Gap:** No hay verificación de que este RPC exista en migraciones.
- Realtime subscription espera status `"SUBSCRIBED"` (línea 203). Si no llega en 5s, reintenta una vez (líneas 211-214). **Gap:** Si segundo intento falla, lanza excepción no manejada (`asyncio.wait_for` timeout).

**Error handling:**
- Cliente ve `SKIPPED` si no hay env vars. ✅
- Sin DB real, tests fallan con `RuntimeError` o excepciones de red. El skipif mitiga esto.
- Si `MultiCrewFlow` falla, hay fallback a sintéticos. ✅
- Si Realtime no entrega eventos, `analyze_results()` retorna `{"passed": False, "reason": "no_events_received"}`. ✅

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

**Flujo completo:**
```
DB insert → Supabase Realtime → WS callback → LatencyValidator._on_event → analyze → report JSON
```

**Coherencia:**
- Decisiones de data apoyan al código: `domain_events` tiene `created_at` y `aggregate_id`. El test las usa correctamente.
- El test mide latencia de infraestructura, no de código propio. Es un test de integración con infraestructura real.

**Alineación plan vs arquitectura:**
- Plan asume que el test NO tiene skipif. Código demuestra que SÍ tiene skipif (aunque con condición incompleta — solo `SUPABASE_URL`, no `SUPABASE_SERVICE_KEY`).
- Plan pide decorador, código tiene `pytestmark`. Ambos funcionan. El plan necesita actualización o el skipif necesita enriquecerse.

**Gaps / Fricción:**
1. **Skipif incompleto:** Solo checkea `SUPABASE_URL`. Si `SUPABASE_URL` existe pero `SUPABASE_SERVICE_KEY` no, el test falla en fixture `supabase_client` (línea 491) con `TypeError` (None como key). El fix REAL del paso 2 debería ser: `pytestmark = pytest.mark.skipif(not SUPABASE_URL or not SUPABASE_SERVICE_KEY, ...)`.
2. **Exclusión manual en Makefile:** `test-all` usa `-k "not latency"`. Esto es fricción DX: el desarrollador debe recordar excluirlo. Un skipif robusto eliminaría la necesidad de `-k "not latency"`.
3. **Datos residuales:** Si el proceso se mata durante test, eventos de test quedan en DB. No hay cleanup global.
4. **Dependencia de RPC no documentada:** `get_server_time` no aparece en migraciones estándar (001-025). Puede ser un RPC manual agregado para este test.

**DX & Tooling (OBLIGATORIO):**

```markdown
### Herramienta Propuesta: `fap validate-env`
- **Qué automatiza:** Verifica que todas las variables de entorno requeridas por tests de integración real estén presentes antes de ejecutar pytest. Elimina el ciclo de "correr test → falla por falta de env → revisar cuál falta → reintentar".
- **Tipo:** CLI comando / validador
- **Cómo se usa:** `fap validate-env --for integration` escanea tests/integration/ por patrones `os.getenv`, compara contra `.env`, reporta qué falta.
- **Impacto para el usuario final:** Deja de ejecutar tests que van a fallar. Ahorra tiempo en CI local.
- **Prioridad:** Baja — tarea opcional, no bloquea paso 2.

### Herramienta Propuesta: `fap cleanup-test-events`
- **Qué automatiza:** Limpia eventos de test de `domain_events` cuyo `aggregate_id` empiece con `lat-test-` o `burst-test-` o `integrity-test-`. Resuelve gap de datos residuales.
- **Tipo:** script / CLI comando
- **Cómo se usa:** `fap cleanup-test-events --before 24h` elimina eventos de test antiguos.
- **Impacto para el usuario final:** Mantiene DB limpia sin intervención manual SQL.
- **Prioridad:** Baja.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [TEST] `pytest tests/integration/test_3_5_latency.py -v` muestra SKIPPED cuando env vars faltan
✅ [TEST] `pytest tests/integration/test_3_5_latency.py -v` ejecuta (no skipped) cuando SUPABASE_URL y SUPABASE_SERVICE_KEY están presentes
✅ [CODE] `pytestmark` a nivel módulo cubre todos los tests del archivo
✅ [BACKEND] Fixture `supabase_client` no lanza TypeError con None como key
✅ [FULLSTACK] Makefile `test-all` puede eliminar `-k "not latency"` si skipif es robusto
✅ [DX] Test no deja datos residuales en caso de interrupción normal (cleanup en finally)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Skipif incompleto causa TypeError si solo SUPABASE_URL está presente | Media | `pytestmark` solo checkea `SUPABASE_URL`, no `SUPABASE_SERVICE_KEY` | Enriquecer skipif: `not SUPABASE_URL or not SUPABASE_SERVICE_KEY` |
| `-k "not latency"` en Makefile oculta tests que deberían correr en CI con DB real | Baja | Si CI tiene DB configurada, el test nunca corre porque Makefile lo excluye | Eliminar `-k "not latency"` del Makefile tras robustecer skipif |
| RPC `get_server_time` no existe en migraciones | Media | Test depende de RPC que no está en schema versionado | Agregar `get_server_time` a migraciones o documentar como setup manual requerido |
| Cleanup en `finally` no ejecuta si proceso recibe SIGKILL | Baja | Eventos de test quedan en DB | Herramienta `fap cleanup-test-events` o cron de limpieza |
| Test mide latencia de red + Supabase Realtime, no solo código propio | Baja | Latencia variable por condiciones de red hace test flaky | Aceptar como test de infraestructura, no gate de CI. Documentar en TESTING.md. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. Una tarea = un artefacto
> 2. Interfaz completa en la tarea
> 3. Patrón de referencia explícito
> 4. Verificación inline
> 5. Test de atomicidad

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Enriquecer skipif en `test_3_5_latency.py`** | `tests/integration/test_3_5_latency.py:46-49` | `pytestmark = pytest.mark.skipif(not SUPABASE_URL or not SUPABASE_SERVICE_KEY, reason="Requiere Supabase Realtime + DB real — plan.md P0 bug conocido")` | Patrón existente: propio archivo línea 46 (`pytestmark = pytest.mark.skipif(...)`) | CODE | Baja | 0.05h | Ninguna | → verificar: `pytest tests/integration/test_3_5_latency.py -v` muestra `SKIPPED` cuando `SUPABASE_SERVICE_KEY` falta (simular con `SUPABASE_URL=fake`) |
| 2 | **Opcional: Eliminar `-k "not latency"` de Makefile** | `Makefile:92` | Remover `-k "not latency"` del target `test-all` | Patrón: otros targets del Makefile no usan `-k` exclusiones | DX | Baja | 0.02h | Tarea 1 | → verificar: `make test-all` ejecuta sin errores (latency se skipea automáticamente si no hay env) |
| 3 | **Validar flujo end-to-end** | — | — | — | FULLSTACK | Baja | 0.05h | Tareas 1-2 | → verificar: Criterios §5 pasan todos |

**Tiempo total estimado:** 0.12 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Agregar RPC `get_server_time` a migraciones SQL para que el test sea 100% reproducible en fresh DB.
- Implementar `fap cleanup-test-events` para limpieza periódica de datos de test.
- Considerar `@pytest.mark.integration` además de skipif para poder filtrar tests por categoría (`pytest -m integration`).
- Evaluar mover `test_3_5_latency.py` a `tests/integration/manual/` si se considera demasiado flaky para CI automático.

---

## 📊 Métrica de Calidad

| Métrica | Mínimo | Real |
|:---|:---|:---|
| `proyecto-config.json` leído antes de explorar | 100% | ✅ |
| Elementos verificados (§0) | ≥ 8 (1-2 archivos) | 12 |
| Discrepancias detectadas | ≥ 1 si toca código existente | 5 (D1-D5) |
| Secciones completadas | 8 secciones (0-7) | 8 |
| Etapas cubiertas | 4 etapas (data, code, backend, fullstack+DX) | 4 |
| Criterios de aceptación | ≥ 1 por sub-paso, verificables | 6 |
| Riesgos identificados | ≥ 3 | 5 |
| Tareas atómicas (1 artefacto por tarea) | 100% | 3/3 |
| Interfaz exacta por tarea | 100% | 3/3 |
| Patrón de referencia explícito por tarea | 100% | 3/3 |
| Verificación inline por tarea | 100% | 3/3 |
| Suposiciones no verificadas | ≤ 2 | 1 (existencia de RPC get_server_time en DB) |
| Propuesta DX / Tooling | ≥ 1 herramienta concreta | 2 propuestas |
| Estimación de tiempo | Sí, por tarea y total | ✅ |

---

**Idioma de respuesta:** Español 🇪🇸
