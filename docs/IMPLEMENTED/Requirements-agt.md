# 🎯 FluxAgentPro v2: MVP Requirements & Roadmap (Final Edition)

Este documento ha sido actualizado para consolidar el desarrollo actual y establecer las bases críticas para el lanzamiento del MVP (Minimum Viable Product).

---

## 🏗️ Fase 1: Cimientos Estabilizados (Core Infrastructure)
*Estado: Producción-Ready. No se requieren cambios estructurales, solo optimización.*

- **Multi-Tenant Flow Engine:** Sistema basado en `BaseFlow` y `BaseFlowState` con persistencia de snapshots en Supabase.
- **Event-Sourcing System:** `EventStore` inmutable para auditoría de cada paso del workflow.
- **Semantic Memory (RAG):** Sistema de memoria a largo plazo vectorial integrado para agentes.
- **Dynamic Registration:** Capacidad de generar y registrar workflows dinámicamente vía `ArchitectFlow`.

---

## 🧩 Fase 2: Pilares Finales del MVP (El Siguiente Paso)
*Objetivo: Dotar al sistema de visibilidad y capacidad de entrega externa.*

### A. Visión Contextual: Flow Explorer
- **Meta:** Pasar de logs de texto a mapas de nodos.
- **Base Técnica:** Endpoint `GET /flows/{flow_type}/topology` que expone la estructura de CrewAI para renderizado en frontend (React Flow).

### B. Entendimiento Micro: Agente Persona (SOUL)
- **Meta:** Humanizar el catálogo de agentes.
- **Base Técnica:** Extensión de `agent_catalog` con campos como `mission_statement` y `forbidden_actions`. El **Agent Specialist** traducirá el prompt técnico a un currículum operativo humanizado.

### C. Salidas Premium: Reporting & Templates
- **C.1 Dashboards (AI Insights):** Utilización del Agente Analítico para generar resúmenes JSON que se transformen en widgets visuales.
- **C.2 Publicación Web (Preformas):** 
  - **Motor:** Integración de **Jinja2 + Markdown** para "llenar" documentos (ej. presupuestos).
  - **Externalización:** Generación de enlaces únicos `fap.com/v1/outputs/{uuid}` con persistencia en la tabla `public_outputs`.

### D. Inteligencia Operativa: Agente Analítico
- **Meta:** Un consultor de solo lectura para la organización.
- **Base Técnica:** Un nuevo `AnalystFlow` con herramientas de búsqueda semántica en `domain_events` y acceso a métricas de uso de tokens (`state.tokens_used`).

---

## 🔒 Estándares de Ingeniería MVP
Para asegurar que las bases son sólidas, toda implementación debe cumplir:

1.  **Tenant Isolation (RLS):** Ni un solo query fuera de la protección de `org_id`.
2.  **Operational Safety:** El Agente Analítico (D) debe operar exclusivamente en modo **Read-Only**.
3.  **Granular Logic:** Uso de `base_guardrail.py` para validar cuotas de tokens y tareas antes de cada ejecución.
4.  **Trazabilidad Ininterrumpida:** Todo cambio de estado debe quedar registrado en el `EventStore`.

---

## 🚀 Próximo paso inmediato:
Implementación del **ReportService** y el **ReportPublishTool** para materializar el punto C.2 (Presupuestos y Preformas).
