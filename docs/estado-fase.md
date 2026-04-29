# Estado de Fase: Infraestructura de Paridad (FAP-Implementor) — v24

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** ACTUALIZACIÓN (Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** es garantizar que el sistema de registries local se comporte exactamente como el de producción. Se busca eliminar fallbacks accidentales y proporcionar herramientas de CLI que permitan probar Agentes y Flujos localmente con las mismas restricciones de seguridad y persistencia que en el entorno real.

**Estado Actual:** 🛠️ **FASE IV EN PROGRESO.** Pasos S1 (Modo Estricto), S2 (CLI Watcher), S3 (CLI Runner) y S4 (FAP-Implementor) completados.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **FAP-Implementor (Paso 4):** Skill inteligente para la generación de bundles seguros y alineados con el esquema v2.0.
- **Scaffolding de Proyecto (fap scaffold):** Comando que genera la estructura de carpetas (`agents/`, `skills/`, `flows/`) y el `manifest.json` base.
- **Esquema de Bundle v2.0:** Integración de `bundle_info` (con autoría) y sistema de hashes SHA256 por archivo en `manifest.json`. Verificado en `src/utils/bundle_utils.py`.
- **CLI Runner (fap run agent/flow):** Extensión del CLI para soportar ejecución granular de componentes. Ahora correctamente registrado en `src/cli/main.py`.
- **Local Executor (`src/services/local_executor.py`):** Orquestador que maneja la carga transiente de bundles, validación AST y limpieza de registries.
- **CLI Watcher (fap dev):** Hot-reload automatizado para sincronización de bundles.
- **Security Guard (`src/services/security_guard.py`):** Implementación de allowlist y validación AST con `RestrictedPython`.

### ⚠️ Parcialmente Implementado
- **Dogfooding (ArchitectFlow):** Extracción parcial de la lógica de `architect_flow.py` para su conversión a bundle.

### ❌ No Existe Aún (Siguiente Paso)
- **Paso 5: Dogfooding (ArchitectFlow):** Migración final del core al formato bundle y eliminación de carga estática.
- **Paso 6: Suite de Validación E2E:** Certificación final de la Fase IV.

### 📝 CORRECCIÓN / DISCREPANCIA
- ✅ **CORREGIDO:** El registro de subcomandos en `src/cli/main.py` ahora utiliza correctamente `add_typer(run_app, name="run")`, permitiendo el acceso a `fap run agent` y `fap run flow`.

---

## 3. Contratos Técnicos Vigentes

### 🌐 Endpoints y Firmas de CLI (Verificados en Código)
| Comando | Firma / Argumentos | Estado |
| :--- | :--- | :--- |
| `fap run skill` | `file_path, --input, --file, --danger-no-sandbox` | ✅ Funcional |
| `fap run agent` | `role, --bundle, --input, --timeout` | ✅ Funcional |
| `fap run flow` | `flow_type, --bundle, --input, --timeout` | ✅ Funcional |
| `fap scaffold` | `name, --dir` | ✅ Funcional |

### 🛠️ Patrones de Código en Uso
- **Bundle Integrity:** Uso de `src/utils/bundle_utils.py` para centralizar el cálculo de SHA256 y actualización de manifiestos.
- **Transient Registration:** El `LocalExecutor` registra temporalmente tools y flows en los registries globales.
- **Async Typer Implementation:** Uso de `asyncio.run()` en wrappers de comandos Typer para soportar lógica asíncrona de Crews y Flows.

---

## 4. Decisiones de Arquitectura Tomadas

- **Agnosticismo de Bundles:** El generador de bundles no depende de la lógica interna de un modelo específico, permitiendo la generación de código compatible con `RestrictedPython`.
- **Estandarización de Salida:** Eliminación de emojis en logs de consola para garantizar compatibilidad con terminales Windows (CP1252/UTF-8 sin BOM).
- **Manifest v2.0 Mandatorio:** Todo bundle generado o validado debe cumplir con la estructura de hashes y metadatos del esquema v2.0.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | ✅ | `config.py`, `registry.py` | Modo Estricto Global. | Paridad Activa |
| **S2** | ✅ | `dev.py`, `main.py` | CLI Watcher con watchdog. | Hot-Reload |
| **S3** | ✅ | `run.py`, `main.py` | CLI Runner con subcomandos. | **Actualizado** |
| **S4** | ✅ | `scaffold.py`, `bundle_utils.py` | Generación segura v2.0. | **NUEVO** |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El CLI permite generar estructuras de bundles válidas (`fap scaffold`).
- [x] Los bundles incluyen hashes de integridad verificables.
- [x] El CLI permite ejecutar agentes/flujos locales usando el flag `--bundle`.
- [x] La suite de tests de integración para validación de bundles pasa al 100%.

---
*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
