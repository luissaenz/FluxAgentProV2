# TODO Post-MVP: FluxAgentPro-v2

Este documento lista las deudas técnicas, riesgos y funcionalidades identificadas durante la Fase 11 de Consolidación Arquitectónica que deben abordarse tras el lanzamiento del MVP.

## Arquitectura y Backend

### [Prio: ALTA] WarmupService para Tool Registry
- **Descripción:** Actualmente, el `tool_registry` (en `src.services.import_service`) es puramente *in-memory*. Al reiniciar el servidor, todas las habilidades importadas se pierden del registro en memoria hasta que se vuelven a importar.
- **Acción:** Implementar un servicio de inicio (Warmup) que al arrancar el servidor:
    1. Consulte todas las habilidades activas en la tabla `skills`.
    2. Las valide mediante `SecurityGuard`.
    3. Las registre automáticamente en el `tool_registry` de `RestrictedPython`.

### [Prio: MEDIA] Transporte SSE para Servidor MCP
- **Descripción:** Evaluar el uso de Server-Sent Events (SSE) como alternativa o complemento al transporte actual para mejorar la comunicación real-time con clientes MCP externos.

### [Prio: MEDIA] Bundle-Builder Agent
- **Descripción:** Desarrollar un agente especializado que pueda generar bundles (ZIP con manifest + código) a partir de lenguaje natural, integrándose con el flujo de importación atómico.

### [Prio: MEDIA] Dashboard Wizard UI
- **Descripción:** Interfaz web intuitiva para el upload de bundles, visualización de manifiestos y gestión de historial de importaciones por organización.

### [Prio: ALTA] Validación SemVer Estricta
- **Descripción:** Refinar el `ImportService` para realizar validaciones de versión semántica (SemVer) que bloqueen activamente el downgrade de bundles accidentales.

## Rendimiento y QA

### [Prio: BAJA] Optimización de Latencia en Local
- **Descripción:** Investigar las causas de los picos de latencia detectados en `test_3_5_latency.py` (hasta 16s en algunos entornos). Optimizar la configuración de WebSockets de Supabase Realtime si es necesario.

## Seguridad

### [Prio: MEDIA] Auditoría de Dependencias Dinámica
- **Descripción:** Automatizar el escaneo de vulnerabilidades en las dependencias permitidas (`ALLOWED_MODULES`) del sandbox de `RestrictedPython`.

### [Prio: BAJA] Hardening con Seccomp (Linux)
- **Descripción:** Activar el filtrado de llamadas al sistema (Seccomp) en los procesos que ejecutan el sandbox para añadir una capa adicional de defensa en profundidad en entornos Linux/Docker.
