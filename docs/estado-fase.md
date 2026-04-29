# Estado de Fase: Infraestructura de Paridad (FAP-Implementor) — v25

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** ACTUALIZACIÓN (Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** es garantizar que el sistema de registries local se comporte exactamente como el de producción. Se busca eliminar fallbacks accidentales y proporcionar herramientas de CLI que permitan probar Agentes y Flujos localmente con las mismas restricciones de seguridad y persistencia que en el entorno real.

**Estado Actual:** 🛠️ **FASE IV EN PROGRESO.** Pasos S1 (Modo Estricto), S2 (CLI Watcher), S3 (CLI Runner), S4 (FAP-Implementor) y S5 (Dogfooding ArchitectFlow) completados.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **Dogfooding ArchitectFlow (Paso 5):** Migración del Architect de componente estático a **System Bundle** dinámico.
- **Soporte de Flujos Python (.py):** `BundleManager` y `FlowRegistry` permiten la carga y ejecución de flujos basados en código fuente persistido en DB.
- **Seguridad Privilegiada (`is_system`):** El `SecurityGuard` permite que bundles certificados (`author: FAP-CORE`) utilicen `async/await` y accedan al módulo `src`, manteniendo el sandboxing para tenants.
- **Generación de Bundles In-Memory:** `BundleManager.create_bundle` centraliza la creación de ZIPs válidos para exportación y seeding.
- **FAP-Implementor (Paso 4):** Skill inteligente para la generación de bundles seguros y alineados con el esquema v2.0.
- **Scaffolding de Proyecto (fap scaffold):** Comando que genera la estructura de carpetas (`agents/`, `skills/`, `flows/`) y el `manifest.json` base.
- **Esquema de Bundle v2.0:** Integración de `bundle_info` (con autoría) y sistema de hashes SHA256 por archivo en `manifest.json`. Verificado en `src/utils/bundle_utils.py`.
- **CLI Runner (fap run agent/flow):** Extensión del CLI para soportar ejecución granular de componentes. Ahora correctamente registrado en `src/cli/main.py`.
- **Local Executor (`src/services/local_executor.py`):** Orquestador que maneja la carga transiente de bundles, validación AST y limpieza de registries.
- **CLI Watcher (fap dev):** Hot-reload automatizado para sincronización de bundles.
- **Security Guard (`src/services/security_guard.py`):** Implementación de allowlist y validación AST con `RestrictedPython`.

### ⚠️ Parcialmente Implementado
- **Suite de Validación E2E:** Pendiente certificación final de la Fase IV.

### ❌ No Existe Aún (Siguiente Paso)
- **Paso 6: Suite de Validación E2E:** Certificación final de la Fase IV con pruebas de importación/exportación cruzadas.

---

## 3. Contratos Técnicos Vigentes

### 🌐 Endpoints y Firmas de CLI (Verificados en Código)
| Comando | Firma / Argumentos | Estado |
| :--- | :--- | :--- |
| `fap run skill` | `file_path, --input, --file, --danger-no-sandbox` | ✅ Funcional |
| `fap run agent` | `role, --bundle, --input, --timeout` | ✅ Funcional |
| `fap run flow` | `flow_type, --bundle, --input, --timeout` | ✅ Funcional |
| `fap scaffold` | `name, --dir` | ✅ Funcional |

### 📊 Esquemas de Base de Datos (Actualizados)
- **`workflow_templates`**: Incluye ahora `code_source` (TEXT) e `is_python` (BOOLEAN) para soportar flujos dinámicos. Verificado en `supabase/migrations/0029_python_flows.sql`.

### 🛠️ Patrones de Código en Uso
- **System Bundle Trust:** Los bundles con `author: FAP-CORE` activan `is_system=True` en el `SecurityGuard`, permitiendo imports de `src` y skipping de `RestrictedPython`.
- **Atomic Bundle Import:** Uso del RPC `import_bundle_atomic` para inserción sincronizada de agentes, flujos (JSON/Py) y metadatos.
- **Seeding Automatizado:** Uso de `scripts/seed_system_bundles.py` para el bootstrap de componentes core como bundles.
- **Bundle Integrity:** Uso de `src/utils/bundle_utils.py` para centralizar el cálculo de SHA256 y actualización de manifiestos.

---

## 4. Decisiones de Arquitectura Tomadas

- **Desacoplamiento del Core:** Los flujos del sistema (como Architect) ya no se importan estáticamente en `main.py`, sino que se cargan desde el registro dinámico.
- **Hibridación de Seguridad:** Se mantiene el escaneo de AST para TODOS los bundles, pero se permite ejecución privilegiada solo a componentes de sistema para no limitar sus capacidades asíncronas.
- **Agnosticismo de Bundles:** El generador de bundles no depende de la lógica interna de un modelo específico, permitiendo la generación de código compatible con `RestrictedPython`.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | ✅ | `config.py`, `registry.py` | Modo Estricto Global. | Paridad Activa |
| **S2** | ✅ | `dev.py`, `main.py` | CLI Watcher con watchdog. | Hot-Reload |
| **S3** | ✅ | `run.py`, `main.py` | CLI Runner con subcomandos. | Funcional |
| **S4** | ✅ | `scaffold.py`, `bundle_utils.py` | Generación segura v2.0. | Implementor OK |
| **S5** | ✅ | `architect_flow.py`, `security_guard.py` | Dogfooding & Python Flows. | **NUEVO** |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El CLI permite generar estructuras de bundles válidas (`fap scaffold`).
- [x] Los bundles incluyen hashes de integridad verificables.
- [x] El CLI permite ejecutar agentes/flujos locales usando el flag `--bundle`.
- [x] **Dogfooding:** El ArchitectFlow genera bundles válidos y es en sí mismo un bundle.
- [ ] La suite de tests de integración para validación de bundles pasa al 100%.

---
*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
