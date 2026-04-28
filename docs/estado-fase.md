# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v4

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Post-Validación Formal ATG)

---

## 1. Resumen de Fase

El objetivo de esta fase es eliminar la creación manual de agentes e implementar un sistema seguro y atómico de importación a través de "Bundles" (archivos ZIP), el cual es el único camino de entrada para agentes, flujos y skills en FluxAgentPro-v2.

**Estado Actual:** ✅ **MVP COMPLETADO Y VALIDADO.** El sistema ha superado la suite de validación formal B1-B9.

| Paso | Descripción | Estado |
|:---|:---|:---|
| T0 | Estabilización de Tests | ✅ Completado |
| T1 | Limpieza Legacy (ArchitectFlow) | ✅ Completado |
| T2 | Setup y Migraciones (026+027) | ✅ Completado |
| T3 | BundleManager (hash, extracción) | ✅ Completado |
| T4 | SecurityGuard (AST + RestrictedPython) | ✅ Completado |
| T5 | ImportService + API `/bundles/import` | ✅ Completado |
| T6 | Refactor ToolRegistry + FlowRegistry híbridos | ✅ Completado |
| T7 | FAP-CLI (init, validate, package, export-agents) | ✅ Completado |
| T8 | Validación Formal y Certificación B1-B9 | ✅ Completado |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**Certificación de Seguridad y Atomicidad (B1-B9):**
- **Validación Estática (B2):** `SecurityGuard` bloquea exitosamente imports prohibidos (`os`, `sys`, etc.) y accesos a dunders.
- **Validación Dinámica (B3):** Timeout de 30s implementado vía `ThreadPoolExecutor` para evitar DOS por bucles infinitos en skills.
- **Atomicidad Transaccional (B5):** Verificado rollback total en `import_bundle_atomic` ante excepciones SQL o fallos lógicos.
- **Lógica de Upsert (B6):** Sincronización correcta de registros existentes basada en `(org_id, role)` para agentes y `(org_id, name)` para skills.

**Componentes Core:**
- `ImportService` (`src/services/import_service.py`) — Orquestación completa del pipeline.
- `BundleManager` (`src/services/bundle_manager.py`) — Validación de hashes SHA256 y límites de tamaño (50MB).
- `ToolRegistry` / `FlowRegistry` — Carga perezosa (Lazy Loading) desde base de datos con aislamiento multi-tenant.

**ArchitectFlow Saneado:**
- `src/flows/architect_flow.py` — Retorna definición JSON lista para ser empaquetada como bundle, sin persistencia directa.

### Qué no existe aún:
- **Hot-Reload (Post-MVP):** Las skills requieren un refresco del registry en memoria tras la importación (actualmente se hace bajo demanda en el lookup).

### Discrepancias Plan vs Código detectadas:
- ⚠️ **Naming de Identificadores:** El plan inicial sugería `name` como PK de agentes, pero el código real usa `(org_id, role)` para consistencia multi-tenant. Documentado y validado en `test_bundle_upsert.py`.

---

## 3. Contratos Técnicos Vigentes

### Modelos de datos (Migraciones reales):
| Tabla | Columnas | Fuente |
|:---|:---|:---|
| `bundle_imports` | `id`, `org_id`, `bundle_hash`, `status` | `0026_bundle_system.sql` |
| `skill_catalog` | `id`, `org_id`, `name`, `code_source` | `0026_bundle_system.sql` |
| `agent_catalog` | `id`, `org_id`, `role`, `bundle_id` | `0026_bundle_system.sql` |

### Patrones de Código Verificados:
- **Auth:** Uso de `PyJWT` para decodificación de tokens de Supabase (JWKS).
- **RLS:** Filtrado estricto por `org_id = auth.jwt() -> 'org_id'`.
- **Sandbox:** `RestrictedPython` con `safe_builtins` y allowlist de módulos aprobados.

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T5 | ✅ | `src/api/routes/bundles.py` | Invocación de RPC `import_bundle_atomic` | Integración API-DB exitosa |
| T7 | ✅ | `src/cli/main.py` | Paridad de validación local/remota | Comando `fap validate` operativo |
| T8 | ✅ | `tests/integration/*.py`, `LAST/validacion.md` | Certificación B1-B9 | 31 tests pasando al 100% |

---

## 5. Criterios Generales de Aceptación MVP

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | `fap validate` local | ✅ Verificado en `test_bundle_cli_validate.py` |
| 2 | Importación atómica | ✅ Verificado en `test_bundle_atomicity.py` |
| 3 | Rechazo por seguridad | ✅ Verificado en `test_security_guard.py` |
| 4 | Límite de 50MB | ✅ Verificado en `test_bundle_manager.py` |
| 5 | Upsert sin duplicados | ✅ Verificado en `test_bundle_upsert.py` |

---

## 6. Estado del Repositorio

**Commits de Validación:**
- `LAST/validacion.md` — Reporte final de cumplimiento B1-B9.
- `tests/integration/test_bundle_upsert.py` — Pruebas de paridad y sincronización de registros.
- `src/services/import_service.py` — Refuerzo de manejo de excepciones en el pipeline.

**Próxima Fase Sugerida:** Limpieza de endpoints legacy en `src/api/routes/agents.py` y despliegue de UI de Wizard de Importación.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*
