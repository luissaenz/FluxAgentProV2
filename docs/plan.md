# 🗺️ PLAN MAESTRO: ARQUITECTURA BUNDLE-DRIVEN (V3)

## 🎯 Visión y Objetivo Principal
Establecer un ecosistema donde el desarrollo de sistemas agénticos sea **Local-First**. El usuario desarrolla, prueba y valida sus agentes, flujos y habilidades en su entorno local utilizando herramientas de CLI, para luego empaquetarlos en **Bundles (ZIP)** que son importados de forma atómica y segura en la plataforma FluxAgentPro (FAP).

**Regla de Oro:** El Bundle es el **único** camino de entrada para la lógica de negocio (Agentes, Flujos, Skills). No existen formularios de creación manual en el Dashboard.

---

## 🏗️ Estado de la Arquitectura (Certificación Fase II)
Al 2026-04-28, el núcleo del sistema ha sido auditado y certificado con **340 tests en verde**:
1.  **Validación de Integridad**: `BundleManager` procesa ZIPs in-memory con verificación SHA256.
2.  **Sandbox de Seguridad**: `SecurityGuard` implementa escaneo AST y `RestrictedPython` con timeout de 30s.
3.  **Persistencia Atómica**: RPC `import_bundle_atomic` garantiza transaccionalidad total (Todo o Nada).
4.  **Registro Híbrido**: `ToolRegistry` soporta carga dinámica desde DB con fallback a disco.

---

## 🔄 El Workflow "Forge-to-Cloud"
El proceso priorizado para el desarrollador sigue este flujo:

1.  **FORGE (Local)**: `fap init` genera la estructura. El dev escribe código Python para skills y JSON para agentes.
2.  **TEST (Local)**: `fap validate` simula el sandbox de FAP localmente para detectar errores de importación o brechas de seguridad.
3.  **PACK (Local)**: `fap package` genera el ZIP final con hashes firmados en el `manifest.json`.
4.  **IMPORT (Remote)**: El bundle se envía a FAP vía API/CLI.
5.  **ACTIVATE (Remote)**: El sistema hidrata el `ToolRegistry` y los agentes quedan listos para su ejecución en Crews.

---

## 🛠️ Roadmap de Implementación: Fase III (Refinamiento y DX)

### Paso 17: CLI Refinement (The Local Forge)
**Objetivo**: Convertir el CLI en una herramienta de grado profesional para desarrollo local.
-   **Mejora de `fap validate`**: Sincronizar las listas de módulos permitidos/prohibidos con el servidor.
-   **Comando `fap run`**: Permitir la ejecución de una skill local dentro del sandbox de `RestrictedPython` para pruebas rápidas.
-   **Autenticación**: Implementar `fap login` para gestionar tokens de organización y facilitar el `fap publish`.
-   **Complejidad**: Media | **Tiempo**: 8h

### Paso 18: Warmup & Persistence (The Registry Bridge)
**Objetivo**: Garantizar que el sistema sea resiliente a reinicios.
-   **Implementación de `WarmupService`**: Servicio que al arrancar escanea la tabla `skill_catalog` y pre-registra las habilidades en el `ToolRegistry`.
-   **Invalidación Dinámica**: Asegurar que al borrar un bundle, el caché de memoria se limpie en todos los nodos (si aplica).
-   **Complejidad**: Media | **Tiempo**: 6h

### Paso 19: SemVer & Version Guard
**Objetivo**: Control total sobre el despliegue y actualizaciones.
-   **Semantic Versioning**: Implementar lógica en `ImportService` para comparar la versión del bundle entrante contra la existente.
-   **Downgrade Prevention**: Bloquear importaciones de versiones menores a menos que se use un flag `--force`.
-   **Complejidad**: Baja | **Tiempo**: 4h

### Paso 20: Dashboard & Wizard (The Visual Entry)
**Objetivo**: Proveer una interfaz visual para la gestión de bundles.
-   **Wizard de Importación**: Interfaz de arrastrar y soltar (Drag & Drop) para bundles.
-   **Vista de Auditoría**: Visualizar el contenido de un bundle importado (lista de agentes y código de skills).
-   **Historial de Despliegue**: Timeline de qué bundles se han aplicado y por quién.
-   **Complejidad**: Alta | **Tiempo**: 16h

---

## 🛡️ Seguridad y Hardening (Post-MVP)
1.  **Seccomp Sandbox**: Implementar filtros de system calls en el worker para prevenir escapes de `RestrictedPython`.
2.  **Auditoría de Dependencias**: Escaneo automático de vulnerabilidades en los `ALLOWED_MODULES`.
3.  **Firmas Criptográficas**: Validación de bundles mediante claves públicas/privadas de proveedores.

---

## 📊 Métricas de Calidad y Éxito
-   **Tests E2E**: El 100% de los casos de importación (B1-B9) deben mantenerse en verde.
-   **Latencia**: La validación e importación de un bundle de 10 agentes debe ser < 5 segundos.
-   **Aislamiento**: Verificación mediante tests de penetración de que una Org no puede inyectar código en el espacio de otra.

---

## 🔮 Futuro: El Marketplace de Agentes
Una vez consolidado el flujo local, el sistema evolucionará hacia un marketplace donde los bundles podrán ser importados directamente desde repositorios públicos o privados (GitHub/GitLab/S3), permitiendo despliegues automáticos (CI/CD) de sistemas agénticos.
