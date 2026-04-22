# 📚 API MCP — Manual de Handlers y Herramientas

Este documento detalla los endpoints y herramientas disponibles en el servidor MCP de FluxAgentPro-v2.

## 1. Transporte JSON-RPC (HTTP)

El Gateway HTTP está disponible en `POST /api/v1/mcp`. Requiere autenticación mediante Bearer Token (Supabase JWT) y el encabezado `x-org-id`.

### Métodos Disponibles

#### `execute_flow`
Inicia la ejecución de un flujo de trabajo.
- **Parámetros**:
  - `flow_type` (string, requerido): Nombre del flujo (ej: `generic_flow`).
  - `input_data` (object, opcional): Datos de entrada para el flujo.
  - `correlation_id` (string, opcional): ID para seguimiento.
- **Respuesta**:
  ```json
  {
    "task_id": "uuid",
    "status": "running",
    "correlation_id": "mcp-..."
  }
  ```

#### `get_task`
Consulta el estado de una tarea.
- **Parámetros**:
  - `task_id` (string, requerido): UUID de la tarea.
- **Respuesta**: Retorna el objeto `BaseFlowState` completo (status, result, error, logic_state).

#### `approve_task` / `reject_task`
Gestiona la aprobación humana (HITL).
- **Parámetros**:
  - `task_id` (string, requerido): UUID de la tarea.
- **Respuesta**: `{ "task_id": "...", "status": "completed", "decision": "approved" }`

---

## 2. Herramientas MCP (Stdio / Claude Desktop)

Las mismas funcionalidades están expuestas como herramientas para agentes LLM.

| Herramienta | Descripción | Argumentos |
|:---|:---|:---|
| `list_flows` | Lista flujos disponibles | - |
| `[flow_name]` | Ejecuta un flujo específico | Los definidos por el flujo |
| `get_task` | Consulta estado de tarea | `task_id` |
| `approve_task` | Aprueba tarea pausada | `task_id` |
| `reject_task` | Rechaza tarea pausada | `task_id` |

### Ejemplo de uso (Claude)
"Ejecuta el flujo `generic_flow` con el prompt 'Analiza este reporte'. Luego dime el `task_id`."

---

## 3. Manejo de Errores

El servidor utiliza códigos JSON-RPC estándar:
- `-32601`: Método no encontrado (Flow no existe).
- `-32602`: Parámetros inválidos.
- `-32001`: Error de autenticación/autorización.
- `-32004`: Recurso no encontrado (Task ID inválido).
- `-32603`: Error interno del servidor.
