# Estado de Fase: Infraestructura de Paridad (CLI Runner) — v23

> 📅 **Fecha:** 2026-04-29
> 📝 **Estado:** ACTUALIZACIÓN (Fase IV - Paridad Local-Producción)

---

## 1. Resumen de Fase

El objetivo de la **Fase IV: Infraestructura de Paridad** es garantizar que el sistema de registries local se comporte exactamente como el de producción. Se busca eliminar fallbacks accidentales y proporcionar herramientas de CLI que permitan probar Agentes y Flujos localmente con las mismas restricciones de seguridad y persistencia que en el entorno real.

**Estado Actual:** 🛠️ **FASE IV EN PROGRESO.** Pasos S1 (Modo Estricto), S2 (CLI Watcher) y S3 (CLI Runner) completados.

---

## 2. Estado Actual del Proyecto

### ✅ Implementado y Funcional (Verificado en Código)
- **CLI Runner (fap run agent/flow):** Extensión del CLI para soportar ejecución granular de componentes.
- **Local Executor (`src/services/local_executor.py`):** Orquestador que maneja la carga transiente de bundles, validación AST y limpieza de registries.
- **Mock Persistence:** Sistema de interceptación de llamadas a DB mediante `unittest.mock` para evitar efectos colaterales durante el `fap run` local.
- **Agent/Task Factory (`src/crews/factory.py`):** Capacidad de reconstruir objetos de CrewAI desde definiciones JSON del bundle.
- **Modo Estricto (FAP_STRICT_MODE):** Flag global que bloquea fallbacks al sistema de archivos local.
- **CLI Watcher (fap dev):** Hot-reload automatizado para sincronización de bundles.

### ⚠️ Parcialmente Implementado
- **Integración de Subcomandos en `fap run`:** El archivo `src/cli/commands/run.py` tiene la lógica de subcomandos, pero `src/cli/main.py` aún registra el comando `run` apuntando directamente a `run_skill` en lugar de usar `add_typer`.

### ❌ No Existe Aún (Siguiente Paso)
- **Paso 4: FAP-Implementor:** Skill inteligente para generación de bundles seguros.
- **Paso 5: Dogfooding (ArchitectFlow):** Migración del core al formato bundle.

### 📝 CORRECCIÓN / DISCREPANCIA
- ⚠️ **Registro de Comandos:** El plan de paridad requería que `fap run` fuera un grupo de comandos (`skill`, `agent`, `flow`). Aunque `run.py` está refactorizado, `src/cli/main.py` requiere una actualización para usar `add_typer(run_app, name="run")` para habilitar el acceso a `fap run agent` y `fap run flow`.

---

## 3. Contratos Técnicos Vigentes

### 🌐 Endpoints y Firmas de CLI (Verificados en Código)
| Comando | Firma / Argumentos | Estado |
| :--- | :--- | :--- |
| `fap run skill` | `file_path, --input, --file, --danger-no-sandbox` | ✅ Funcional |
| `fap run agent` | `role, --bundle, --input, --timeout` | ✅ Implementado en logic (⚠️ Ver Discrepancia) |
| `fap run flow` | `flow_type, --bundle, --input, --timeout` | ✅ Implementado en logic (⚠️ Ver Discrepancia) |

### 🛠️ Patrones de Código en Uso
- **Transient Registration:** El `LocalExecutor` registra temporalmente tools y flows en los registries globales y los limpia al finalizar (`clear()`).
- **In-Memory Mocking:** Uso de `MagicMock` para simular respuestas de Supabase (`get_tenant_client`, `get_service_client`).
- **Async Typer:** Comandos del CLI definidos como `async def` para integración nativa con procesos asíncronos de Flows.
- **BaseCrew Testability:** Import de `get_settings` con `# noqa: F401` en `src/crews/base_crew.py` para compatibilidad con mocks de tests unitarios.

---

## 4. Decisiones de Arquitectura Tomadas

- **Aislamiento por Inyección:** En lugar de modificar el código de los agentes para soportar "modo local", se utiliza `LocalExecutor.mock_persistence()` para parchear las dependencias de red en tiempo de ejecución.
- **Subcomandos Typer:** Adopción de subcomandos para `fap run` para mejorar la escalabilidad de la herramienta.
- **Seguridad Mandatoria:** Incluso en ejecución local con `--bundle`, el `SecurityGuard` valida el código AST a menos que se use `--danger-no-sandbox`.

---

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | ✅ | `config.py`, `registry.py`, `launch.sh` | Modo Estricto Global. | Paridad Activa |
| **S2** | ✅ | `dev.py`, `main.py`, `publish.py` | CLI Watcher con watchdog. | Hot-Reload |
| **S3** | ✅ | `run.py`, `local_executor.py`, `factory.py`, `base_crew.py` | CLI Runner con paridad y mocks. | **NUEVO** |

---

## 6. Criterios Generales de Aceptación MVP (Fase IV)

- [x] El CLI permite ejecutar agentes remotos vía API con polling de resultados.
- [x] El CLI permite ejecutar agentes/flujos locales usando el flag `--bundle`.
- [x] La ejecución local simula la persistencia sin escribir en la base de datos real.
- [x] Los inputs JSON se cargan correctamente desde string o archivos.
- [x] La suite de tests unitarios (238) e integración (84) pasa al 100%.

---
*Documento actualizado por el Arquitecto de Contexto (Antigravity) siguiendo el protocolo 0_CONTEXTO.md.*
