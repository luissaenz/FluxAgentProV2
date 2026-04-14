# Análisis de Integración Agentica (FAP <-> Claude/MCP)

Este documento detalla los elementos faltantes y los requerimientos técnicos para transformar **FluxAgentPro (FAP)** en un sistema agéntico capaz de ser operado por agentes externos (como Claude) mediante el **Model Context Protocol (MCP)**.

## 1. Estado Actual de la Infraestructura

| Componente | Rol Actual | Limitación para Agentes |
| :--- | :--- | :--- |
| **MCP Pool** | Cliente | El sistema consume herramientas externas pero no se expone a sí mismo. |
| **FlowRegistry** | Catálogo Interno | No tiene interfaz de descubrimiento compatible con el protocolo MCP. |
| **TenantClient** | Aislamiento RLS | Requiere inyección explícita de `org_id` en cada sesión de ejecución. |
| **BaseFlow** | Orquestador | La validación de entrada es manual; falta definición de esquemas (JSON Schema). |

## 2. Elementos Faltantes (Roadmap de Implementación)

### 2.1 Servidor MCP (Entry Point)
Es necesario crear un binario o script de entrada (ej: `src/agentic/server.py`) que implemente el servidor MCP.
- **Transporte Stdio**: Para integración local con Claude Desktop.
- **Transporte SSE**: Para integración con agentes web o dashboards externos.

### 2.2 Traductor de Herramientas (Flow-to-Tool)
Un módulo que convierta el `FlowRegistry` en una lista de herramientas MCP:
- **Descubrimiento Dinámico**: Escanear los flows registrados.
- **Generación de Esquemas**: Mapear los argumentos de los flows a parámetros de herramientas MCP.
- **Metadatos**: Exponer descripciones claras para el LLM.

### 2.3 Puente de Ejecución Multitenant (`mcp_bridge.py`)
Un controlador que orqueste la ejecución:
1. **Captura de Contexto**: Recibir el `org_id` (vía variable de entorno o comando de configuración inicial).
2. **Instanciación de Flow**: Crear la instancia del flow correcto según el nombre de la herramienta.
3. **Manejo de Resultados**: Capturar el output del flow y formatearlo como `TextContent` o `ImageContent` de MCP.

### 2.4 Migración a Esquemas Tipados
Para que el agente sea preciso, los flows deben definir sus entradas de forma estructurada.
- **Propuesta**: Utilizar modelos de **Pydantic** en los flows para auto-generar los JSON Schemas requeridos por el protocolo MCP.

## 3. Desafíos y Decisiones Pendientes

### A. Gestión de Identidad (Auth)
A diferencia de un servidor MCP tradicional, FAP es multi-empresa. 
- **Decisión**: ¿Cómo identifica el agente a la organización? 
    - *Opción A*: Una sesión MCP por organización (argumento de CLI).
    - *Opción B*: Herramienta `switch_organization` expuesta al agente.

### B. Modo de Ejecución
- **Síncrono**: El agente espera a que el flow termine (ideal para flows rápidos).
- **Asíncrono**: El servidor devuelve un `task_id` y el agente debe monitorear el estado (ideal para flows que requieren aprobación humana - HITL).

---
*Análisis generado como parte de la Fase de Arquitectura de Sistemas Agénticos - FAP v2.*
