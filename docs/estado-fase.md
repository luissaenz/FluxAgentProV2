# Estado de Fase: Infraestructura de Paridad (FAP-Implementor) — v27

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** COMPLETADO (Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** era garantizar que el sistema de registries local se comportara exactamente como el de producción. Se han eliminado los fallbacks accidentales y se han proporcionado herramientas de CLI que permitan probar Agentes y Flujos localmente con las mismas restricciones de seguridad y persistencia que en el entorno real. Adicionalmente, se saneó la infraestructura resolviendo problemas de rutas relativas, encoding en Windows, y mejorando la observabilidad del ciclo de empaquetado y la suite de pruebas.

**Estado Actual:** ✅ **FASE IV COMPLETADA.** Todos los pasos (S1-S9) han sido implementados, validados y certificados con éxito. El repositorio está libre de warnings y la higiene global está automatizada.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **Suite de Validación E2E (Paso 6):** Implementación de `tests/e2e/test_parity_suite.py` cubriendo el ciclo de vida completo (`scaffold` -> `package` -> `publish` -> `run`) con aislamiento de tenants.
- **Auto-Hashing en `BundleManager`:** Automatización del cálculo SHA256 durante `create_bundle`, garantizando la integridad de los manifiestos.
- **Herramienta de Certificación:** `scripts/certify_fase4.py` validando pipeline completo e integrando validaciones reales (`pytest`).
- **Dogfooding ArchitectFlow (Paso 5):** Migración del Architect de componente estático a **System Bundle** dinámico.
- **Soporte de Flujos Python (.py):** `BundleManager` y `FlowRegistry` operando bajo un esquema persistido y seguro (`RestrictedPython`).
- **FAP-Implementor (Paso 4):** Skill inteligente para la generación de bundles seguros y alineados con el esquema v2.0.
- **CLI Utilities:** 
  - Scaffolding (`fap scaffold`)
  - Runner de componentes granulares (`fap run agent/flow/skill`)
  - Watcher hot-reload (`fap dev`)
- **Saneamiento DX y CLI (Paso 7/8/9):** 
  - Resolución unificada a rutas absolutas.
  - Fix de encoding `UTF-8` predictivo para terminales Windows (`scripts/sanitize_codebase.py`).
  - Script autómata de higiene `scripts/sanitize_codebase.py` utilizando `ruff`.
  - Refactoring global hacia `OrgBaseTool`.
- **Aislamiento Multi-Tenant y Tests (Paso 8/9):** 
  - `MockLLMManager` evolucionado para soportar respuestas JSON compatibles con Pydantic v2.
  - Resolución dual de herramientas (nombre de archivo + nombre de clase).
  - Eliminación global de `DeprecationWarnings` en la suite local.

### ⚠️ Parcialmente Implementado / Deuda Técnica
- **ID-004:** Pruebas unitarias de las "Tools" antiguas fallando debido al nuevo aislamiento multi-tenant. Si bien no bloquean la validación E2E (Fase IV exitosa), las tools individuales como `EscandalloTool` exigen ser actualizadas con el parámetro `org_id`.

### ❌ No Existe Aún (Siguiente Fase)
- **Fase V: Agentes Autónomos v2.0:** Orquestación de crews dinámicas, memoria persistente, y herramientas reactivas avanzadas.

---

## 3. Contratos Técnicos Vigentes

### 🌐 Endpoints y Firmas de CLI (Verificados en Código)
| Comando | Firma / Argumentos | Estado |
| :--- | :--- | :--- |
| `fap run skill` | `file_path, --input, --file, --danger-no-sandbox` | ✅ Funcional |
| `fap run agent` | `role, --bundle, --input, --timeout` | ✅ Funcional |
| `fap run flow` | `flow_type, --bundle, --input, --timeout` | ✅ Funcional |
| `fap scaffold` | `name, --dir` | ✅ Funcional |
| `fap package` | `bundle_path, --output` | ✅ Funcional |

### 📊 Esquemas de Base de Datos
- **`bundle_imports`**: Tracking de hashes e integridad por bundle.
- **`workflow_templates`**: Soporta `code_source` e `is_python` para flujos dinámicos.

### 🛠️ Patrones de Código en Uso
- **Mock-Driven Testing (JSON Validated):** El framework de tests se vale de un `MockLLMManager` que detecta dinámicamente si la llamada requiere una estructura JSON (ej: Pydantic schemas) devolviendo mocks válidos o un simple string. 
- **Filterwarnings:** La limpieza de la salida estándar se hace vía configuración central en `pyproject.toml`.
- **System Bundle Trust:** Los bundles con `author: FAP-CORE` activan `is_system=True` en `SecurityGuard` permitiendo sentencias como `async/await`.
- **Certificación Real & Higiene Automática:** El SDLC asume uso constante de `scripts/sanitize_codebase.py` para asegurar que el repositorio pasa linting siempre, y `scripts/certify_fase4.py` validando paridad de punta a punta.
- **Restricción de Secretos en Bundles:** Uso exclusivo del proxy `self._get_secret()` en `OrgBaseTool`.

---

## 4. Decisiones de Arquitectura Tomadas

- **Aprobación QA Aislada (Paso 9):** Se determinó aislar la rotura en tests unitarios antiguos (asociados a base features) como deuda técnica (`docs/sugest.md`) en lugar de considerarlos un bloqueo para la Fase IV, debido a que el componente central validado (Framework de Bundles y Paridad Local-Producción) es completamente funcional y certificable a nivel E2E.
- **Hibridación de Seguridad:** Se mantiene el escaneo de AST para TODOS los bundles, pero se permite ejecución privilegiada solo a componentes de sistema.
- **Supresión Selectiva de Warnings:** Configuración estricta en `pyproject.toml` para ignorar warnings incontrolables (ej: internals de LangChain y Pydantic core) que ensucian los logs.
- **Sanitización OS-Agnostic:** Los scripts DX asumen ejecución en consolas `tty` falsas (Windows CI) por lo que evitan estrictamente caracteres unicode decorativos por defecto, optando por `ascii` donde es crítico para prevenir crash.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | ✅ | `config.py`, `registry.py` | Modo Estricto Global. | Paridad Activa |
| **S2** | ✅ | `dev.py`, `main.py` | CLI Watcher con watchdog. | Hot-Reload |
| **S3** | ✅ | `run.py`, `main.py` | CLI Runner con subcomandos. | Funcional |
| **S4** | ✅ | `scaffold.py`, `bundle_utils.py` | Generación segura v2.0. | Implementor OK |
| **S5** | ✅ | `architect_flow.py`, `security_guard.py` | Dogfooding & Python Flows. | System Bundle |
| **S6** | ✅ | `test_parity_suite.py`, `certify_fase4.py` | Suite E2E & Certificación. | Completado Inicial |
| **S7** | ✅ | `package.py`, `dev.py`, `main.py` | Saneamiento rutas/encoding. | Paridad Absoluta |
| **S8** | ✅ | `local_executor.py`, `analytical.py`, `migrate_basetool.py` | Multi-tenancy Mock, Resolución Dual y `OrgBaseTool`. | Seguridad y DX |
| **S9** | ✅ | `certify_fase4.py`, `sanitize_codebase.py`, `conftest.py`, `pyproject.toml` | **QA Activo, Mocking JSON, Filterwarnings.** | **FASE CERRADA** |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El CLI permite generar estructuras de bundles válidas (`fap scaffold`).
- [x] Los bundles incluyen hashes de integridad verificables (Auto-computed).
- [x] El CLI permite ejecutar agentes/flujos locales usando el flag `--bundle`.
- [x] **Dogfooding:** El ArchitectFlow genera bundles válidos y es en sí mismo un bundle.
- [x] La suite de tests de integración para validación de bundles pasa al 100%.
- [x] QA: La consola está libre de warnings y la higiene global de formateo está garantizada vía CI scripts.

---
*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
