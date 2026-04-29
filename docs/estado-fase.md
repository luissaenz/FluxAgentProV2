# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v21

> 📅 **Fecha:** 2026-04-28
> 📝 **Estado:** ACTUALIZACIÓN (Cierre de Fase III - Refinamiento y DX)

---

## 1. Resumen de Fase

El objetivo de la **Fase III: Refinamiento y DX** ha sido consolidar el flujo **Local-First** mediante herramientas de CLI profesionales y una interfaz de gestión visual (Dashboard). Se ha robustecido la persistencia, la seguridad del sandbox y la observabilidad del sistema, permitiendo un despliegue de bundles atómico, versionado y auditable.

**Estado Actual:** 🏁 **FASE III COMPLETADA.** El sistema es 100% funcional desde el empaquetado local hasta la activación en la nube.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **Lazy Loading Persistente:** Registries (`ToolRegistry` y `FlowRegistry`) con búsqueda en 2 niveles (Memoria -> DB) y aislamiento multi-tenant.
- **Importación Atómica:** Procedimiento RPC `import_bundle_atomic` que garantiza integridad referencial en importaciones masivas.
- **Security Guard:** Sandbox basado en `RestrictedPython` con escaneo AST y límites de ejecución (30s timeout).
- **SemVer Version Guard:** Lógica de protección contra downgrades con soporte para flag `force`.
- **Dashboard & Wizard:** Interfaz visual para subida, validación y auditoría de bundles en tiempo real.
- **FAP-CLI:** Herramienta de línea de comandos para `init`, `validate`, `package` y `publish`.
- **Especialización de Errores:** Distinción entre `MalformedVersionError` (400) y `VersionDowngradeError` (409) para mejor DX.

### ⚠️ Parcialmente Implementado
- *N/A (Fase III cerrada)*

### ❌ No Existe Aún (Post-MVP)
- **Retry con Backoff:** El sistema falla rápido (fail-fast) para mantener simplicidad.
- **Seccomp Sandbox:** Hardening a nivel de OS (planeado para Post-MVP).
- **Firmas Criptográficas:** Validación de bundles mediante claves PKI.

---

## 3. Contratos Técnicos Vigentes

### 📊 Modelos de Datos (Migraciones 0026-0028)
- `bundle_imports`: Trazabilidad de cada ZIP subido (hash, version, timestamp).
- `skill_catalog`: Almacena código fuente (`code_source`) y bytecode compilado.
- `agent_catalog`: Definiciones JSON de agentes.
- `workflow_templates`: Definiciones de flujos.

### 🌐 Endpoints API (Verificados en `src/api/routes/bundles.py`)
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/bundles/validate` | Validación dry-run (sin persistencia). |
| `POST` | `/api/bundles/import` | Importación atómica (ZIP + opcional force=true). |
| `GET` | `/api/bundles/history` | Historial de importaciones del tenant. |
| `GET` | `/api/bundles/{id}/details` | Contenido detallado y código de un bundle. |
| `DELETE` | `/api/bundles/{id}` | Desactivación (Soft-delete) del bundle y sus componentes. |

### 🛠️ Patrones de Código en Uso
- **Auth Pattern:** Uso de `PyJWT` (HS256/ES256) con inyección de `org_id` vía `Depends(require_org_id)`.
- **RLS Pattern:** `auth.uid()` y `auth.jwt() -> 'org_id'` para aislamiento de datos.
- **Registry Pattern:** Inyección de dependencias en `SecurityGuard` y registro en memoria con prefijo `org_id:`.
- **Hydration Logging:** Logs de nivel `INFO` tras cargas exitosas desde base de datos en `src/tools/registry.py` y `src/flows/registry.py`.

---

## 4. Decisiones de Arquitectura Tomadas

- **Local-First Priority:** El bundle es el **único** camino de entrada para lógica de negocio. No se permiten ediciones manuales en DB.
- **Atomicidad PostgreSQL:** Uso extensivo de RPC en PL/pgSQL para evitar estados inconsistentes durante fallos de red.
- **Sandbox Híbrido:** Escaneo AST preventivo + Ejecución restringida en `RestrictedPython`.
- **Versioning:** Estricto cumplimiento de Semantic Versioning para evitar sobreescrituras accidentales.

### 📝 Correcciones al Plan Maestro
- ⚠️ **Auth:** Se utiliza `PyJWT` en lugar de `python-jose` (deprecada).
- ⚠️ **RLS:** Se utiliza el patrón de JWT Claims de Supabase para `org_id` en lugar de variables de sesión personalizadas.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **T21** | ✅ | `bundles.py`, `import_service.py` | Errores 400/409, logs INFO. | Quality Sprint Finalizado |
| **T20** | ✅ | `BundlesWizardPage.tsx`, `api.ts` | Wizard Drag&Drop, Auditoría Visual. | Cierre de Interfaz |
| **T19** | ✅ | `import_service.py` | Lógica SemVer y Version Guard. | Protección de Versión |
| **T18** | ✅ | `warmup.py`, `registry.py` | `WarmupService` para hidratación DB. | Resiliencia de Reinicio |
| **T17** | ✅ | `cli/main.py` | Refinamiento de `fap validate` y `login`. | DX Local |

---

## 6. Criterios Generales de Aceptación MVP (Fase III)

- [x] El flujo **Empaquetar -> Validar -> Importar** funciona sin errores.
- [x] Los componentes (Agentes/Skills) son inmediatamente utilizables tras la importación.
- [x] El sistema bloquea versiones inferiores por defecto (`VersionDowngradeError`).
- [x] El código de las skills se puede auditar visualmente desde el Dashboard.
- [x] Los errores de importación son atómicos (no dejan residuos en la DB).
- [x] No existen linters ni warnings críticos en el core del sistema.

---
*Documento generado automáticamente por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
