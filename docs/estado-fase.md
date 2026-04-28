# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v20

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Cierre de Paso 20 - Dashboard & Wizard)

---

## 1. Resumen de Fase

El objetivo de esta fase (**Fase III: Refinamiento y DX**) ha sido elevar la experiencia del desarrollador (DX) y del administrador de la plataforma, garantizando que el flujo **Local-First** sea robusto y que el despliegue en la nube sea visual, auditable y seguro. Con la implementación del Dashboard & Wizard, se cierra el ciclo de vida completo de los bundles.

**Estado Actual:** 🏁 **FASE III COMPLETADA.** El sistema cuenta con un pipeline completo desde la creación local (CLI) hasta la gestión visual (Dashboard) con auditoría de código en tiempo real.

| Paso | Descripción | Estado |
|:---|:---|:---|
| T1-T16| Auditoría de Integridad Técnica y Cierre MVP | ✅ Completado |
| T17 | CLI Refinement (The Local Forge) | ✅ Completado |
| T18 | Warmup & Persistence (The Registry Bridge) | ✅ Completado |
| T19 | SemVer & Version Guard | ✅ Completado |
| T20 | **Dashboard & Wizard (The Visual Entry)** | ✅ Completado |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**Dashboard & Wizard (Paso 20):**
- **Bundle Wizard:** Interfaz interactiva de 3 pasos (Subida -> Validación -> Despliegue) con soporte para archivos ZIP y reporte de seguridad dinámico.
- **Validación en Tiempo Real:** Integración con el endpoint `/validate` para pre-visualizar el contenido del bundle (conteo de agentes/skills) y detectar conflictos de versión antes de persistir.
- **Control de Downgrades Visual:** Interfaz de advertencia cuando se detecta una versión inferior, permitiendo el bypass mediante un checkbox de "Force Downgrade" que inyecta el flag `force=true`.
- **Bundle Timeline (Historial):** Auditoría histórica de despliegues ordenada cronológicamente por `imported_at`. Permite visualizar el estado de cada importación y acceder a sus detalles.
- **Auditoría de Código (Audit Viewer):** Visor de código fuente premium integrado que permite inspeccionar el código de las skills importadas directamente desde el historial de bundles.

**Backend & API (Soporte Paso 20):**
- **Endpoint de Detalles:** Recuperación enriquecida de componentes que incluye el `code_source` de las skills para auditoría (verificado en `src/services/import_service.py`).
- **Endpoint de Historial:** Listado de importaciones ordenado por `imported_at` descendente.
- **FAP Client (Lib):** Cliente API refactorizado para manejar `FormData` de forma transparente, permitiendo subidas multipart seguras sin sobrescribir el boundary del navegador.

---

## 3. Contratos Técnicos Vigentes

### APIs y Endpoints (Actualizados):
| Endpoint | Método | Parámetros Críticos | Descripción |
|:---|:---|:---|:---|
| `/api/bundles/validate` | `POST` | `file: File` | Validación dry-run del bundle. |
| `/api/bundles/import` | `POST` | `file: File, force: bool` | Importación atómica con bypass opcional de versión. |
| `/api/bundles/history` | `GET` | - | Lista el historial de importaciones del tenant. |
| `/api/bundles/{id}/details` | `GET` | `bundle_id: str` | Retorna componentes y código fuente de un bundle. |

### Patrones de Código en Uso (Verificados):
- **Form Data Handling:** El cliente API `fapFetch` detecta instancias de `FormData` y elimina el header `Content-Type` manual para permitir que el navegador gestione el multipart boundary correctamente.
- **Audit Logging:** Las skills persisten su código fuente original en la columna `code_source` de `skill_catalog` para trazabilidad administrativa.
- **Visual Feedback:** Uso de `sonner` para notificaciones y estados de carga (skeletons/spinners) consistentes con el sistema de diseño.

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T20 | ✅ | `bundles.py`, `import_service.py`, `BundlesWizardPage.tsx`, `BundleTimeline.tsx`, `api.ts` | Auditoría visual de código. Cliente API compatible con FormData. | **Cierre Fase III** |
| T19 | ✅ | `import_service.py`, `bundles.py`, `test_version_guard.py` | Uso de `packaging` para SemVer. HTTP 409 para conflictos. Flag `force` para bypass. | SemVer Pro |
| T18 | ✅ | `warmup.py`, `main.py`, `registry.py`, `0028_roadmap_features.sql` | Warmup síncrono. Soft-delete universal. | Resiliencia 100% |

---

## 5. Criterios de Aceptación (Fase III - Paso 20)

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | Subir ZIP y ver reporte de validación antes de importar | ✅ Verificado (`BundlesWizardPage.tsx`) |
| 2 | El historial muestra los bundles ordenados por fecha de importación | ✅ Verificado (`import_service.py:199`) |
| 3 | Se puede ver el código fuente de las skills en el modal de auditoría | ✅ Verificado (`BundleTimeline.tsx` + `get_details`) |
| 4 | El checkbox "Force" funciona para resolver conflictos de versión | ✅ Verificado (Integración Wizard -> API) |
| 5 | Navegación sincronizada en el sidebar del dashboard | ✅ Verificado (`nav-main.tsx`) |

---

## 6. Estado del Repositorio

**Hitos Finales de la Fase III:**
- **Pipeline End-to-End**: Desde `fap package` en local hasta el Wizard en el Dashboard, el flujo está cerrado y validado.
- **Transparencia & Seguridad**: El sistema no solo bloquea versiones inferiores, sino que permite auditar visualmente qué código se está ejecutando.
- **Listo para Próxima Etapa**: La base del sistema de bundles es sólida y escalable para futuras integraciones y marketplace de agentes.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*
