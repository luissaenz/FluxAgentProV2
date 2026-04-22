# Especificación API MCP (JSON-RPC)

Este documento detalla la interfaz del servidor Model Context Protocol (MCP) de FluxAgentPro-v2.

## Endpoint
`POST /api/v1/mcp`

## Autenticación
Todas las solicitudes deben incluir el encabezado `Authorization`:
`Authorization: Bearer <JWT_TOKEN>`

El servidor soporta:
- **ES256**: Tokens de Supabase Auth (Clerk, etc. vía JWKS).
- **HS256**: Tokens firmados internamente.

## Protocolo
Se utiliza JSON-RPC 2.0. Todas las respuestas exitosas tienen código HTTP 200.

## Métodos Soportados

### 1. `execute_flow`
Inicia la ejecución de un flujo de agentes.

**Parámetros:**
- `flow_name` (string): Nombre del flujo en el `FlowRegistry`.
- `input_data` (dict): Datos de entrada para el flujo.
- `metadata` (dict, opcional): Metadatos adicionales para el ticket/task.

**Ejemplo de Solicitud:**
```json
{
  "jsonrpc": "2.0",
  "method": "execute_flow",
  "params": {
    "flow_name": "branding_flow",
    "input_data": { "client": "ACME Corp" }
  },
  "id": 1
}
```

### 2. `get_task`
Obtiene los detalles de una tarea específica, incluyendo su estado actual y snapshots.

**Parámetros:**
- `task_id` (uuid): ID de la tarea a consultar.

### 3. `approve_task`
Resuelve una interrupción Human-In-The-Loop (HITL) aprobando la continuación del flujo.

**Parámetros:**
- `task_id` (uuid): ID de la tarea bloqueada.
- `feedback` (dict, opcional): Instrucciones adicionales para el agente.

### 4. `reject_task`
Resuelve una interrupción HITL rechazando o cancelando la tarea.

**Parámetros:**
- `task_id` (uuid): ID de la tarea a rechazar.
- `reason` (string, opcional): Motivo del rechazo.

## Errores (MCPError)
El servidor devuelve errores JSON-RPC estándar con códigos específicos:

| Código | Mensaje | Descripción |
| :--- | :--- | :--- |
| -32601 | Method not found | El método solicitado no existe. |
| -32602 | Invalid params | Los parámetros de la solicitud son inválidos. |
| 401 | Authentication failed | Token inválido o expirado. |
| 403 | Access denied | El usuario no pertenece a la organización. |
| 500 | Internal error | Error inesperado en el servidor. |
