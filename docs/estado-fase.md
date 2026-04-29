# Estado de Fase: Infraestructura de Paridad (FAP_STRICT_MODE) — v22

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** ACTUALIZACIÓN (Inicio de Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** es garantizar que el sistema de registries local se comporte exactamente como el de producción. Esto se logra mediante la eliminación de fallbacks accidentales al sistema de archivos local, forzando la carga de herramientas y flujos exclusivamente desde el sistema de bundles y base de datos, asegurando una validación absoluta antes del despliegue.

**Estado Actual:** 🛠️ **FASE IV EN PROGRESO.** Implementado el "Strict Mode" centralizado.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **Modo Estricto (FAP_STRICT_MODE):** Flag global en `src/config.py` que controla el comportamiento de los registries.
- **Gatekeeper de Herramientas:** `ToolRegistry.get()` ahora bloquea el fallback a `src/tools/demo/` cuando el modo estricto está activo, lanzando `ValueError`.
- **Sincronización de Registries:** `FlowRegistry.get()` actualizado con parámetro `strict_mode` para mantener simetría en la firma de las APIs de registros.
- **Observabilidad de Inicio:** El script `launch.sh` reporta el estado de `FAP_STRICT_MODE` en el banner de arranque del servidor.
- **Lazy Loading Persistente:** Registries con búsqueda en 2 niveles (Memoria -> DB) operativos.
- **Importación Atómica:** RPC `import_bundle_atomic` funcional.
- **FAP-CLI:** Operativa para empaquetado y validación local.

### ⚠️ Parcialmente Implementado
- *N/A*

### ❌ No Existe Aún (Post-MVP)
- **Retry con Backoff:** El sistema mantiene fail-fast.
- **Seccomp Sandbox:** Hardening a nivel de OS.
- **Firmas Criptográficas:** Validación PKI de bundles.

---

## 3. Contratos Técnicos Vigentes

### ⚙️ Configuración (src/config.py)
- `fap_strict_mode: bool = Field(True, ...)` — Valor por defecto `True` para forzar paridad desde el inicio.

### 🌐 Endpoints y Firmas (Verificados en Código)
| Componente | Método/Firma | Cambio Realizado |
| :--- | :--- | :--- |
| `ToolRegistry` | `get(name, org_id)` | Implementa gatekeeper contra filesystem fallback. |
| `FlowRegistry` | `get(name, org_id, strict_mode)` | Firma actualizada para simetría con ToolRegistry. |
| `launch.sh` | Banner informativo | Muestra `Strict Mode: true/false` al iniciar. |

### 🛠️ Patrones de Código en Uso
- **Strict Mode Gate:** Uso de `get_settings().fap_strict_mode` dentro de los métodos `get()` para decidir si permitir el acceso a archivos locales (`src/tools/demo/`).
- **Auth Pattern:** Uso de `PyJWT` con inyección de `org_id`.
- **RLS Pattern:** `auth.uid()` y `auth.jwt() -> 'org_id'` para aislamiento de datos.

---

## 4. Decisiones de Arquitectura Tomadas

- **Paridad sobre Conveniencia:** Se prioriza que el entorno local falle si falta un bundle (`FAP_STRICT_MODE=true`), evitando que el desarrollador use herramientas locales que no están en la base de datos de producción.
- **Aislamiento de Registros:** Los registros son independientes del entorno (`APP_ENV`), permitiendo habilitar la paridad incluso en `development`.
- **Logging de Auditoría:** Se introducen logs de nivel `INFO` explícitos cuando el Modo Estricto bloquea una carga ("Strict mode active: Skipping filesystem fallback...").

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | ✅ | `config.py`, `registry.py`, `launch.sh`, `.env.example` | Implementación de Strict Mode Gate. | Paridad Local-Prod |
| **T21** | ✅ | `bundles.py`, `import_service.py` | Errores 400/409, logs INFO. | Cierre Fase III |
| **T20** | ✅ | `BundlesWizardPage.tsx`, `api.ts` | Wizard Drag&Drop. | Dashboard Finalizado |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El sistema lanza error si se intenta usar una herramienta no cargada vía bundle/DB estando en modo estricto.
- [x] La configuración de modo estricto se puede sobrescribir vía variables de entorno (`FAP_STRICT_MODE`).
- [x] El banner de inicio muestra correctamente el estado de la paridad.
- [x] No hay degradación de performance por el chequeo de modo estricto.
- [x] La firma de los registros es consistente entre Tools y Flows.

---
*Documento generado automáticamente por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
