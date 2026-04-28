# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v5

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Cierre de Fase 10 - Wizard UI)

---

## 1. Resumen de Fase

El objetivo de esta fase era eliminar la creación manual de agentes e implementar un sistema seguro, atómico y guiado de importación a través de "Bundles" (archivos ZIP), integrando tanto el motor backend como una interfaz de usuario (Wizard) de última generación.

**Estado Actual:** ✅ **FASE COMPLETADA AL 100%.** El sistema es ahora el único camino de entrada oficial para agentes y skills.

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
| T9 | **Dashboard Wizard UI (Importación Guiada)** | ✅ Completado |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**Dashboard Wizard UI (Paso 10):**
- **Validación Local (JSZip):** Parsing de `manifest.json` directamente en el navegador antes de la subida.
- **Endpoint Dry-run (`/api/bundles/validate`):** Validación remota completa (AST + Sandbox) sin persistencia en DB, permitiendo previsualizar el impacto del bundle.
- **Wizard Interactivo:** Flujo de 3 estados (Selección -> Validación -> Despliegue) con feedback visual premium y reportes de seguridad detallados.
- **Atomicidad UI:** La confirmación final dispara la transacción RPC garantizando consistencia absoluta.

**Certificación de Seguridad y Atomicidad:**
- **SecurityGuard:** Bloqueo estricto de imports maliciosos y timeouts de ejecución (30s).
- **Importación Atómica:** Rollback total garantizado por `import_bundle_atomic` en PostgreSQL.
- **Persistencia Multi-tenant:** Aislamiento total por `org_id` en todos los registros dinámicos.

**Componentes Core:**
- `ImportService` (`src/services/import_service.py`) — Soporta ahora `validate_only`.
- `ToolRegistry` / `FlowRegistry` — Sistema híbrido (DB + FS) operativo.

### Qué no existe aún:
- **Bundle-Builder Agent (Post-MVP):** Generación de bundles desde lenguaje natural (Tarea T20).

### Discrepancias Plan vs Código detectadas:
- ✅ **Resuelto:** El identificador único de agentes es `(org_id, role)`, no `name`. El sistema de Upsert ha sido ajustado y validado para este contrato.

---

## 3. Contratos Técnicos Vigentes

### APIs y Endpoints (Verificados):
| Ruta | Método | Descripción | Fuente |
|:---|:---|:---|:---|
| `/api/bundles/validate` | `POST` | Validación Dry-run (Memoria) | `src/api/routes/bundles.py` |
| `/api/bundles/import` | `POST` | Importación Atómica (Persistencia) | `src/api/routes/bundles.py` |

### Modelos de datos (Migraciones reales):
| Tabla | Columnas Clave | Constraint |
|:---|:---|:---|
| `skill_catalog` | `org_id`, `name`, `code_source` | `UNIQUE(org_id, name)` |
| `agent_catalog` | `org_id`, `role`, `bundle_id` | `UNIQUE(org_id, role)` |

### Patrones de Código Verificados:
- **Frontend:** Uso de `jszip` para pre-parsing y componentes desacoplados (`BundleDropzone`, `ValidationReport`).
- **Backend:** Patrón "Memory-First" para validaciones ZIP evitando I/O de disco innecesario.

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T9 | ✅ | `bundles/page.tsx`, `components/*` | Validación remota previa al commit | Interfaz premium terminada |
| T10 | ✅ | `src/api/routes/bundles.py` | Añadido endpoint `/validate` | Soporte para Dry-runs |
| T8 | ✅ | `tests/integration/*.py` | Certificación B1-B9 | 100% de cobertura funcional |

---

## 5. Criterios Generales de Aceptación MVP

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | `fap validate` local | ✅ Verificado (CLI) |
| 2 | Importación atómica | ✅ Verificado (RPC/DB) |
| 3 | Rechazo por seguridad | ✅ Verificado (AST/Sandbox) |
| 4 | **Wizard UI Funcional** | ✅ Verificado (Flow UI -> API) |
| 5 | **Validación Dry-run** | ✅ Verificado (Endpoint `/validate`) |

---

## 6. Estado del Repositorio

**Hitos Finales:**
- Despliegue de la UI de Importación en `/integrations/bundles`.
- Implementación de `validate_only` en `ImportService` para soporte de UI.
- Validación final de seguridad y linting (0 errores).

**Próxima Fase:** Integración del **Bundle-Builder Agent** y expansión de la librería de flujos pre-construidos.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*

