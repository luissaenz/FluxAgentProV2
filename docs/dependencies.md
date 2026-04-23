# 📦 Dependencias del Proyecto

Este documento detalla las dependencias críticas de FluxAgentPro-v2 y la justificación técnica de su elección.

## 🔑 Autenticación y Seguridad

### PyJWT (`PyJWT>=2.0.0`)
- **Propósito**: Manejo de tokens JWT para autenticación inter-agente y validación de sesiones de Supabase.
- **Justificación**: Se utiliza como la **única librería de JWT** del proyecto, reemplajando a `python-jose`. Ofrece una integración superior con el estándar JWKS y mayor estabilidad con versiones modernas de `cryptography`.
- **Algoritmos en Uso**: ES256 (para validar firmas de Supabase) y HS256 (para tokens internos).

## 🚀 Núcleo de la API y Servidor

### FastAPI (`fastapi>=0.115.0`)
- **Propósito**: Framework principal para la API REST y el Gateway MCP.
- **Justificación**: Provee tipado estricto, validación automática mediante Pydantic y soporte nativo para operaciones asíncronas.

### Uvicorn (`uvicorn[standard]>=0.32.0`)
- **Propósito**: Servidor ASGI de alto rendimiento para la ejecución de la aplicación.

## 🤖 Ecosistema MCP (Model Context Protocol)

### MCP SDK (`mcp>=1.0.0`)
- **Propósito**: Implementación del estándar Model Context Protocol.
- **Justificación**: Es la base para la interoperabilidad de FluxAgentPro con clientes externos como Claude Desktop, exponiendo flows y herramientas de forma segura.

### sse-starlette (`sse-starlette>=0.21.0`)
- **Propósito**: Soporte para Server-Sent Events (SSE).
- **Justificación**: Habilita el transporte asíncrono `SSE` requerido por el protocolo MCP para notificaciones en tiempo real.

## 💾 Base de Datos y Persistencia

### Supabase SDK (`supabase>=2.10.0`)
- **Propósito**: Interacción con la infraestructura de base de datos, autenticación y storage de Supabase.

## 🛠️ Utilidades y Orquestación

### APScheduler (`apscheduler>=3.10.0`)
- **Propósito**: Programación y ejecución de tareas periódicas en segundo plano (ej: Health Checks de integraciones).

### Pydantic Settings (`pydantic-settings>=2.6.0`)
- **Propósito**: Gestión robusta de configuraciones mediante variables de entorno y validación de tipos.

## 🧹 Registro de Limpieza (Depuración)

### python-jose
- **Estado**: **ELIMINADO**.
- **Razón**: Redundancia con `PyJWT` y conflictos recurrentes en la gestión de dependencias de cifrado.
- **Fecha de Limpieza**: Fase 5 - Paso 7.
