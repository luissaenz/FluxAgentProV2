# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v19

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Cierre de Paso 19 - SemVer & Version Guard)

---

## 1. Resumen de Fase

El objetivo de esta fase (**Fase III: Refinamiento y DX**) es elevar la experiencia del desarrollador (DX) y garantizar que el flujo **Local-First** sea robusto, seguro y un espejo fiel del entorno de producción. Tras cerrar la auditoría técnica (Paso 16), el refinamiento del CLI (Paso 17) y la persistencia/warmup (Paso 18), se ha completado la **Protección de Versiones (SemVer)** para garantizar la integridad del ciclo de vida de los bundles.

**Estado Actual:** 🚀 **PASO 19 COMPLETADO Y VALIDADO.** El sistema ahora protege contra downgrades accidentales mediante SemVer y permite actualizaciones forzadas mediante bypass explícito.

| Paso | Descripción | Estado |
|:---|:---|:---|
| T1-T16| Auditoría de Integridad Técnica y Cierre MVP | ✅ Completado |
| T17 | CLI Refinement (The Local Forge) | ✅ Completado |
| T18 | Warmup & Persistence (The Registry Bridge) | ✅ Completado |
| T19 | **SemVer & Version Guard** | ✅ Completado |
| T20 | Dashboard & Wizard (The Visual Entry) | ⏳ Pendiente |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**SemVer & Version Guard (Paso 19):**
- **Validación SemVer:** Integración de la librería `packaging.version` para el parsing y comparación estricta de versiones siguiendo el estándar PEP 440 (verificado en `src/services/import_service.py`).
- **Downgrade Protection:** El método `_check_version_guard` consulta la última versión exitosa en `bundle_imports` filtrando por `bundle_name` y `org_id`, bloqueando cualquier importación con versión inferior.
- **Bypass con Flag Force:** Soporte para el parámetro booleano `force` en la importación, permitiendo ignorar el guard de versiones para correcciones de emergencia o downgrades intencionados.
- **Gestión de Errores Granular:** Implementación de `VersionConflictError` que resulta en un `HTTP 409 Conflict` para downgrades y `HTTP 400 Bad Request` para versiones malformadas (verificado en `src/api/routes/bundles.py`).

**Warmup & Persistence (Paso 18):**
- **Soft-Delete Sincronizado:** Marcas de `is_active=False` aplicadas recursivamente.
- **Warmup Service:** Pre-carga de assets en el arranque de la API (verificado en `src/api/main.py`).

**Refinamiento de CLI (Paso 17):**
- **Autenticación Persistente:** Gestión de tokens en `~/.fap/config.json`.
- **Sandbox Local:** Paridad de ejecución con `RestrictedPython`.

---

## 3. Contratos Técnicos Vigentes

### APIs y Endpoints (Actualizados):
| Endpoint | Método | Parámetros Críticos | Descripción |
|:---|:---|:---|:---|
| `/api/bundles/import` | `POST` | `force: bool = False` | Importación atómica con protección de versión opcional. |

### Patrones de Código en Uso (Verificados):
- **SemVer:** Comparación de objetos `Version` de la librería `packaging`. No se permiten strings ni comparaciones lexicográficas.
- **RLS (Row Level Security):** Uso de `current_org_id()` (session setting `app.org_id`). ⚠️ *Nota: Existe una discrepancia menor en el plan, el código real usa session settings via RPC.*
- **Auth:** `PyJWT` para validación de tokens ES256/HS256.
- **Tenant Isolation:** Prefijo `{org_id}:` en llaves de registro en memoria.

### Schemas de Catálogo (Migración 0028):
| Tabla | Columnas Críticas | Notas |
|:---|:---|:---|
| `bundle_imports` | `id, org_id, version, is_active` | `version` debe ser un string compatible con SemVer. |

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T19 | ✅ | `import_service.py`, `bundles.py`, `test_version_guard.py` | Uso de `packaging` para SemVer. HTTP 409 para conflictos. Flag `force` para bypass. | SemVer Pro |
| T18 | ✅ | `warmup.py`, `main.py`, `registry.py`, `0028_roadmap_features.sql` | Warmup síncrono. Soft-delete universal. | Resiliencia 100% |
| T17 | ✅ | `src/cli/`, `src/api/routes/bundles.py` | Sincronización de reglas de seguridad. CLI unificado. | DX Pro |

---

## 5. Criterios de Aceptación (Fase III - Paso 19)

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | Bloqueo automático de versiones inferiores (`1.0.0` sobre `1.1.0`) | ✅ Verificado (`test_version_guard.py`) |
| 2 | El flag `force=true` permite el downgrade | ✅ Verificado (`test_version_guard.py`) |
| 3 | Las versiones malformadas (ej: "beta-1") retornan 400 | ✅ Verificado (`test_version_guard.py`) |
| 4 | El guard es granular por `bundle_name` (no afecta a otros bundles) | ✅ Verificado (`test_version_guard.py`) |
| 5 | Estabilidad de tests legacy tras la implementación | ✅ Verificado (Mocks actualizados en 16 tests) |

---

## 6. Estado del Repositorio

**Hitos Finales Alcanzados:**
- **Version Guard Operativo**: El sistema garantiza que la evolución del código en producción sea siempre progresiva o controlada.
- **Regresiones Corregidas**: La suite de pruebas está estabilizada tras la introducción de la lógica de versiones.
- Preparado para el **Dashboard & Wizard (Paso 20)**, última pieza de la Fase III.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*
