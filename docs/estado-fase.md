# Estado de Fase: Infraestructura de Paridad (FAP-Implementor) — v26

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** COMPLETADO (Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** era garantizar que el sistema de registries local se comportara exactamente como el de producción. Se han eliminado los fallbacks accidentales y se han proporcionado herramientas de CLI que permitan probar Agentes y Flujos localmente con las mismas restricciones de seguridad y persistencia que en el entorno real. Adicionalmente, se saneó la infraestructura resolviendo problemas de rutas relativas, encoding en Windows y mejorando la observabilidad del ciclo de empaquetado.

**Estado Actual:** ✅ **FASE IV COMPLETADA.** Todos los pasos (S1-S9) han sido implementados, validados y certificados.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **Suite de Validación E2E (Paso 6):** Implementación de `tests/e2e/test_parity_suite.py` cubriendo el ciclo de vida completo (`scaffold` -> `package` -> `publish` -> `run`) con aislamiento de tenants.
- **Auto-Hashing en `BundleManager`:** Automatización del cálculo SHA256 durante `create_bundle`, garantizando la integridad de los manifiestos sin intervención manual.
- **Herramienta de Certificación:** `scripts/certify_fase4.py` para la validación rápida del pipeline y generación de reportes de cumplimiento.
- **Dogfooding ArchitectFlow (Paso 5):** Migración del Architect de componente estático a **System Bundle** dinámico.
- **Soporte de Flujos Python (.py):** `BundleManager` y `FlowRegistry` permiten la carga y ejecución de flujos basados en código fuente persistido en DB.
- **Seguridad Privilegiada (`is_system`):** El `SecurityGuard` permite que bundles certificados (`author: FAP-CORE`) utilicen `async/await` y accedan al módulo `src`, manteniendo el sandboxing para tenants.
- **Generación de Bundles In-Memory:** `BundleManager.create_bundle` centraliza la creación de ZIPs válidos para exportación y seeding.
- **FAP-Implementor (Paso 4):** Skill inteligente para la generación de bundles seguros y alineados con el esquema v2.0.
- **Scaffolding de Proyecto (fap scaffold):** Comando que genera la estructura de carpetas (`agents/`, `skills/`, `flows/`) y el `manifest.json` base.
- **CLI Runner (fap run agent/flow):** Extensión del CLI para soportar ejecución granular de componentes.
- **CLI Watcher (fap dev):** Hot-reload automatizado para sincronización de bundles.
- **Security Guard (`src/services/security_guard.py`):** Implementación de allowlist y validación AST con `RestrictedPython`.
- **Saneamiento de Rutas (Paso 7):** Resolución unificada a rutas absolutas en `fap dev` y `fap package`.
- **Soporte Universal Windows (Paso 7):** Corrección activa de errores de encoding (UTF-8 wrapper) en el CLI (`main.py`).
- **Observabilidad de Hashing (Paso 7):** Generación e impresión explícita de hashes por archivo durante el empaquetado.
- **Certificación Real E2E (Paso 9):** Integración activa de `pytest.main()` dentro de `scripts/certify_fase4.py`.
- **Higiene Automatizada (Paso 9):** Script `scripts/sanitize_codebase.py` para aplicar reglas consistentes de linting/formatting (`ruff`).- **Herramienta de DX para Migración (Paso 8):** Script `scripts/migrate_basetool.py` para refactorizar automatizadamente importaciones legacy a `OrgBaseTool`.
- **Aislamiento Multi-Tenant de Tools (Paso 8):** Refactor de `src/tools/analytical.py` y herramientas de sistema para heredar obligatoriamente de `OrgBaseTool`.

### ⚠️ Parcialmente Implementado
- *Ninguno. Todos los componentes de la Fase IV están operativos.*

### ❌ No Existe Aún (Siguiente Fase)
- **Fase V: Agentes Autónomos v2.0:** Orquestación de crews dinámicas y memoria persistente.

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

### 📊 Esquemas de Base de Datos (Actualizados)
- **`bundle_imports`**: Tracking de hashes e integridad por bundle.
- **`workflow_templates`**: Soporta `code_source` e `is_python`. Verificado en `supabase/migrations/0029_python_flows.sql`.

### 🛠️ Patrones de Código en Uso
- **Auto-Hashing Registry:** El `BundleManager` inyecta automáticamente los hashes en el `BundleManifest` durante el empaquetado.
- **Mock-Driven Testing:** Uso de `MockLLMManager` en `tests/conftest.py` para pruebas E2E deterministas sin coste de tokens.
- **System Bundle Trust:** Los bundles con `author: FAP-CORE` activan `is_system=True`.
- **Atomic Bundle Import:** Uso del RPC `import_bundle_atomic`.
- **Certificación Activa:** El proceso de certificación no es solo de comprobación estática, sino que ejecuta los tests de integración reales (`pytest`).
- **Encoding Predictivo:** Se fuerza explícitamente `utf-8` en flujos I/O para asegurar compatibilidad interplataforma en salidas CLI.
- **Resolución Dual de Herramientas (Paso 8):** `LocalExecutor` registra herramientas por filename y ClassName (ej. `{org_id}:dual_tool`).
- **Restricción de Secretos en Bundles (Paso 8):** Uso exclusivo de `self._get_secret()` en `OrgBaseTool` (verificado en `security_rules.md`).

---

## 4. Decisiones de Arquitectura Tomadas

- **Certificación como Pipeline:** La validación no es manual; se requiere la ejecución exitosa de `certify_fase4.py` para marcar la infraestructura como estable.
- **Hibridación de Seguridad:** Se mantiene el escaneo de AST para TODOS los bundles, pero se permite ejecución privilegiada solo a componentes de sistema.
- **Agnosticismo de Bundles:** El generador de bundles no depende de la lógica interna de un modelo específico.
- **Supresión Selectiva de Warnings:** Configuración en `pyproject.toml` para ignorar `DeprecationWarning` de dependencias externas (Supabase) que generaban ruido en los logs de certificación.
- **Paths Absolutos Mandatorios:** Abandono del manejo de rutas relativas inter-componentes para prevenir errores de CWD en binarios y watchers.
- **Aislamiento Simulado Local:** Inyección dinámica de contexto (vía mocks) en la suite de pruebas para emular un entorno multi-tenant sin servidor real.

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
| **S9** | ✅ | `certify_fase4.py`, `sanitize_codebase.py`| QA Activo e Higiene. | **FASE CERRADA** |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El CLI permite generar estructuras de bundles válidas (`fap scaffold`).
- [x] Los bundles incluyen hashes de integridad verificables (Auto-computed).
- [x] El CLI permite ejecutar agentes/flujos locales usando el flag `--bundle`.
- [x] **Dogfooding:** El ArchitectFlow genera bundles válidos y es en sí mismo un bundle.
- [x] La suite de tests de integración para validación de bundles pasa al 100%.

---
*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
