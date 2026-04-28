# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v16

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Cierre de Paso 18 - Warmup & Persistence / The Registry Bridge)

---

## 1. Resumen de Fase

El objetivo de esta fase (**Fase III: Refinamiento y DX**) es elevar la experiencia del desarrollador (DX) y garantizar que el flujo **Local-First** sea robusto, seguro y un espejo fiel del entorno de producción. Tras cerrar la auditoría técnica del backend (Paso 16) y el refinamiento del CLI (Paso 17), el foco se ha completado en la **Resiliencia y Persistencia** del sistema de registros.

**Estado Actual:** 🚀 **PASO 18 COMPLETADO Y VALIDADO.** El sistema ahora es resiliente a reinicios mediante warmup automático y mantiene coherencia total tras borrados mediante soft-deletes sincronizados.

| Paso | Descripción | Estado |
|:---|:---|:---|
| T1-T16| Auditoría de Integridad Técnica y Cierre MVP | ✅ Completado |
| T17 | CLI Refinement (The Local Forge) | ✅ Completado |
| T18 | **Warmup & Persistence (The Registry Bridge)** | ✅ Completado |
| T19 | SemVer & Version Guard | ⏳ Pendiente |
| T20 | Dashboard & Wizard (The Visual Entry) | ⏳ Pendiente |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**Warmup & Persistence (Paso 18):**
- **Soft-Delete Sincronizado:** Implementado en `ImportService.delete_bundle`. Al borrar un bundle, se marcan como `is_active=False` tanto el bundle como sus agentes, skills y flujos asociados (verificado en `src/services/import_service.py`).
- **Invalidación de Caché L1:** Los registros de herramientas y flujos implementan `invalidate_tenant_cache(org_id)` para limpiar la memoria tras cambios en el catálogo, forzando la recarga desde DB (verificado en `src/flows/registry.py` y `src/tools/registry.py`).
- **Warmup Service:** Servicio global que identifica tenants con workflows activos y pre-carga sus assets en memoria durante el arranque para eliminar la latencia de "cold start" (verificado en `src/services/warmup.py`).
- **Integración en Lifespan:** La API de FastAPI ahora ejecuta el warmup global antes de aceptar peticiones (verificado en `src/api/main.py`).

**Refinamiento de CLI (Paso 17):**
- **Autenticación Persistente:** `fap login` gestiona tokens en `~/.fap/config.json`.
- **Sincronización de Seguridad:** `fap validate --sync` descarga reglas de `/api/bundles/security-config`.
- **Sandbox Local:** `fap run` utiliza `RestrictedPython` con paridad total con el servidor.

**Integridad de Backend:**
- **Esquema de Roadmap:** Migración 0028 aplicada, añadiendo `version` e `is_active` a `bundle_imports` y `skill_catalog` (verificado en `supabase/migrations/0028_roadmap_features.sql`).

---

## 3. Contratos Técnicos Vigentes

### Patrones de Código en Uso (Verificados):
- **Soft-Delete:** Filtro obligatorio `.eq("is_active", True)` en todas las lecturas de catálogo desde el `WarmupService` y métodos de carga dinámica.
- **Cache Registry:** Uso de llaves con prefijo `{org_id}:{asset_name}` en diccionarios `_flows` y `_tools` para aislamiento multi-tenant en memoria.
- **RLS (Row Level Security):** Uso de `current_setting('app.org_id')` configurado vía RPC `set_config`.
- **Auth:** `PyJWT` para validación de tokens y extracción de `org_id`.

### Schemas de Catálogo Actualizados (Migración 0028):
| Tabla | Columnas Críticas | Notas |
|:---|:---|:---|
| `bundle_imports` | `id, org_id, version, is_active` | `is_active` controla visibilidad global del bundle. |
| `skill_catalog` | `id, org_id, bundle_id, name, code_source, is_active` | `is_active` permite desactivar herramientas individuales. |
| `agent_catalog` | `id, org_id, role, bundle_id, is_active` | Ya incluía `is_active` por defecto. |
| `workflow_templates` | `id, org_id, flow_type, bundle_id, is_active` | Ya incluía `is_active` por defecto. |

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T18 | ✅ | `src/services/warmup.py`, `src/api/main.py`, `src/flows/registry.py`, `0028_roadmap_features.sql` | Warmup síncrono en lifespan para garantizar SLA de latencia. Soft-delete universal con `is_active`. | Resiliencia 100% |
| T17 | ✅ | `src/cli/`, `src/api/routes/bundles.py` | Typer + httpx. Sincronización de reglas de seguridad. | DX Pro |
| T16 | ✅ | `registry.py`, `import_service.py` | Cierre de brechas de auditoría técnica. | Auditado |

---

## 5. Criterios de Aceptación (Fase III - Paso 18)

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | `delete_bundle` oculta flujos y herramientas inmediatamente | ✅ Verificado (Invalidación de Caché L1) |
| 2 | El reinicio de la API pre-carga assets de tenants activos | ✅ Verificado (Logs de Warmup en startup) |
| 3 | La migración 028 añade `is_active` a tablas faltantes | ✅ Verificado (`0028_roadmap_features.sql`) |
| 4 | `FlowRegistry` tiene paridad con `ToolRegistry` en caché | ✅ Verificado (Métodos de invalidación idénticos) |

---

## 6. Estado del Repositorio

**Hitos Finales Alcanzados:**
- Cierre del **The Registry Bridge**: El sistema de registros en memoria y persistencia en DB está sincronizado.
- Preparado para **SemVer & Version Guard** (Paso 19), aprovechando el nuevo campo `version` en `bundle_imports`.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*
