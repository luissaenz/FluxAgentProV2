# 🗺️ PLAN DE IMPLEMENTACIÓN: FASE IV — ECOSISTEMA Y PARIDAD TOTAL

Este documento detalla la hoja de ruta técnica para alcanzar la paridad absoluta entre el desarrollo local y el entorno de producción en **FluxAgentPro-v2**, garantizando un ciclo de vida de desarrollo (SDLC) profesional, seguro y extremadamente rápido.

---

## 🎯 Objetivos de la Fase IV
1.  **Paridad "Local-as-Production"**: Eliminar los "atajos" de carga desde disco. Todo código local debe correr bajo las mismas restricciones que en producción (`RestrictedPython`, `SecurityGuard`).
2.  **Feedback en Tiempo Real**: Implementar un sistema de "Hot-Reload" mediante el CLI que sincronice cambios locales con la base de datos en < 2 segundos.
3.  **FAP-Implementor Skill**: Desarrollar un escuadrón técnico automatizado (fork de `skill-creator`) capaz de generar bundles válidos y seguros de forma agnóstica al modelo.
4.  **Dogfooding**: Migrar el núcleo del sistema (`ArchitectFlow`) al formato de Bundles.

---

## 🚀 Pasos de Implementación

### Paso 1: Infraestructura de Paridad (Modo Estricto)
**Objetivo:** Forzar al sistema a comportarse como un entorno de producción, incluso en local.

*   **Acciones:**
    *   Implementar `FAP_STRICT_MODE` en `ToolRegistry` y `FlowRegistry`.
    *   Configurar el entorno local para que la variable sea `true` por defecto.
    *   Desactivar el fallback a `src/tools/demo/*.py` cuando el modo estricto esté activo.
*   **Implicancias:**
    *   **Seguridad**: Garantiza que ningún código "sucio" en el sistema de archivos se ejecute sin pasar por el `SecurityGuard`.
    *   **DX**: El desarrollador *debe* publicar sus cambios para verlos, eliminando el riesgo de "funciona en mi máquina pero no en prod".
    *   **Rendimiento**: Se reduce la búsqueda innecesaria en disco.

### Paso 2: CLI Watcher — `fap dev`
**Objetivo:** Automatizar el ciclo de Publicación -> Base de Datos.

*   **Acciones:**
    *   Crear el comando `fap dev <path_to_bundle>`.
    *   Utilizar `watchdog` para monitorear cambios en el código fuente del bundle.
    *   Al detectar cambios:
        1.  Validación estática rápida (AST check).
        2.  Empaquetado en ZIP (Bundle).
        3.  Publicación atómica vía `fap-cli publish` a la API local.
        4.  Invalidación de caché de registries en el servidor local.
*   **Implicancias:**
    *   **Velocidad**: Sincronización transparente sin intervención del usuario.
    *   **Integridad**: Si el código local rompe las reglas de seguridad, el watcher lo detecta y aborta la publicación antes de romper la base de datos.

### Paso 3: CLI Runner — `fap run agent/flow`
**Objetivo:** Permitir pruebas granulares de componentes específicos desde la terminal.

*   **Acciones:**
    *   Extender `src/cli/commands/run.py` para soportar agentes y flujos completos.
    *   Aceptar un flag `--bundle` para ejecutar el bundle local *como si estuviera en la DB*, pasando por el pipeline de validación completo.
*   **Implicancias:**
    *   **Debugging**: Permite depurar la lógica de agentes sin necesidad de usar el Dashboard o la UI.
    *   **Aislamiento**: Facilita la creación de tests unitarios que verifiquen el comportamiento de un bundle de forma aislada.

### Paso 4: FAP-Implementor (Fork de `skill-creator`)
**Objetivo:** Crear una herramienta inteligente para la generación de agentes "FAP-ificados".

*   **Acciones:**
    *   Realizar un fork de la skill `skill-creator` de Anthropic.
    *   **FAP-ificación**: Modificar el prompt base para que entienda:
        *   Estructura de Bundles (`manifest.json`, subcarpetas).
        *   Restricciones de `RestrictedPython` (uso de `BaseTool`, no `os/subprocess`).
        *   Integración con MCP para tareas que requieran salir del sandbox.
    *   **Agnosticismo**: Asegurar que la lógica de generación no dependa de características exclusivas de un modelo (ej: Claude-only syntax), permitiendo que funcione con Gemini, GPT-4, etc.
*   **Implicancias:**
    *   **Escalabilidad**: Cualquier usuario podrá generar agentes complejos simplemente describiendo su intención.
    *   **Cumplimiento**: La skill generará código que *ya es válido* para el `SecurityGuard`, reduciendo los errores de importación.

### Paso 5: Dogfooding — Migración de `ArchitectFlow`
**Objetivo:** Utilizar el sistema de bundles para el componente más crítico del sistema.

*   **Acciones:**
    *   Extraer `src/flows/architect_flow.py` y sus dependencias.
    *   Empaquetarlo como el bundle oficial `fap-core-architect`.
    *   Eliminar la carga estática del código del core.
*   **Implicancias:**
    *   **Mantenibilidad**: El "arquitecto" puede actualizarse independientemente del servidor core.
    *   **Validación Real**: Si el sistema puede manejar su propio flujo arquitectónico como un bundle, puede manejar cualquier cosa.

### Paso 7: Saneamiento y Robustez de Infraestructura (Estabilidad)
**Objetivo:** Eliminar inconsistencias técnicas y asegurar que las herramientas de CLI sean resilientes.

*   **Acciones:**
    *   **Unificación de Manifiesto (V06):** Centralizar la lógica de esquemas en `src/utils/bundle_utils.py` y actualizar `fap init`, `fap package` y `fap scaffold` para usar exclusivamente el estándar v2.0 (`bundle_info`).
    *   **Paths Dinámicos (V01):** Refactorizar `package_bundle` para que devuelva la ruta absoluta del archivo generado, eliminando suposiciones de directorios en `fap dev`.
    *   **Fix Windows Encoding (V07):** Forzar salida ASCII o detectar encoding en terminales Windows para prevenir crashes por emojis en el output de `rich`.
    *   **Observabilidad de Hashing (V13):** Implementar logs de nivel `INFO` en `BundleManager.create_bundle` que detallen el proceso de cálculo de integridad.

### Paso 8: Integridad Arquitectónica y Multi-Tenancy (Seguridad)
**Objetivo:** Garantizar que los componentes locales respeten el aislamiento de datos y la resolución de nombres del core.

*   **Acciones:**
    *   **Aislamiento Obligatorio (V09):** Actualizar las plantillas de generación del `fap-implementor` y la documentación para que todas las skills hereden de `OrgBaseTool` en lugar de `BaseTool`, garantizando acceso al Vault y RLS.
    *   **Resolución Dual de Tools (V04):** Modificar el `LocalExecutor` para que registre herramientas en el registry transiente usando tanto el nombre del archivo como el nombre de la clase.

### Paso 9: Certificación Técnica Profunda (QA)
**Objetivo:** Elevar el estándar de calidad de la suite de validación y eliminar ruido en los logs.

*   **Acciones:**
    *   **Saneamiento de Mocks (V10):** Ajustar los tipos de retorno en `MockLLMManager` para que coincidan estrictamente con las expectativas de Pydantic v2, eliminando warnings de serialización.
    *   **Certificación Real (V12):** Integrar `pytest.main()` dentro de `scripts/certify_fase4.py` para que la certificación incluya pruebas de ejecución real por defecto.
    *   **Higiene Final (V08):** Ejecución de limpieza de imports y formateo automatizado en los módulos de utilidades.

---

## ⏱️ Estimación de Esfuerzo (Horas Totales: 61h)

| Hito | Tiempo | Prioridad |
|---|---|---|
| Infraestructura & Modo Estricto | 5h | Crítica |
| CLI Watcher (`fap dev`) | 10h | Alta |
| CLI Runner (Extensión) | 6h | Media |
| Dogfooding (`ArchitectFlow`) | 10h | Alta |
| Skill Builder (`fap-implementor`) | 8h | Media |
| Validación Final & E2E | 8h | Alta |
| **Saneamiento & Robustez (P7)** | 6h | Alta |
| **Integridad & Multi-Tenancy (P8)** | 4h | Crítica |
| **Certificación Profunda (P9)** | 4h | Media |

---

## ⚠️ Riesgos y Mitigaciones

1.  **Riesgo:** La sincronización constante de `fap dev` genera versiones innecesarias en la DB.
    *   **Mitigación:** Implementar un flag `is_dev` en los bundles para que el sistema local sobreescriba la versión de desarrollo en lugar de crear un historial infinito.
2.  **Riesgo:** La skill `fap-implementor` genera código que el LLM no puede ejecutar localmente.
    *   **Mitigación:** Incluir un paso de "Pre-validación" en la skill que ejecute el `SecurityGuard` antes de presentar el código al usuario.
3.  **Riesgo (NUEVO):** La herencia de `OrgBaseTool` podría fallar en entornos sin una sesión de organización activa.
    *   **Mitigación:** Implementar un `MockOrgContext` en el `LocalExecutor` que inyecte un `org_id` de pruebas por defecto.
