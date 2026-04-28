# Multi-tenant Registry System

FluxAgentPro-v2 utiliza un sistema de registros dinámicos con caché de dos niveles para gestionar agentes, flujos y herramientas de forma eficiente en un entorno multi-tenant.

## 1. Arquitectura de Caché
Para minimizar la latencia de base de datos y maximizar la escalabilidad, se implementan dos niveles de acceso:

- **L1 (Memoria)**: Los objetos instanciados (Clases de Flows, Funciones de Skills) residen en el proceso de FastAPI.
- **L2 (Base de Datos)**: Las definiciones persistentes (JSON/Python) residen en Supabase/PostgreSQL.

## 2. Registro de Flujos (`FlowRegistry`)
El `FlowRegistry` (`src/flows/registry.py`) gestiona la resolución de tipos de flujo:

1.  **Búsqueda en L1**: Intenta encontrar el flujo en memoria usando la clave `{org_id}:{flow_type}`.
2.  **Lazy Loading (L2)**: Si no está en L1, consulta `workflow_templates`. Si existe, instancia un `DynamicWorkflow` y lo sube a L1.
3.  **Jerarquía**: Soporta flujos estáticos (definidos en código) y dinámicos (generados por el Architect).

## 3. Registro de Herramientas (`ToolRegistry`)
El `ToolRegistry` (`src/tools/registry.py`) gestiona las "Skills":

1.  **Carga Dinámica**: Ejecuta código Python validado en un entorno seguro.
2.  **Wrappers**: Envuelve funciones simples en clases `BaseTool` compatibles con CrewAI.
3.  **Aislamiento**: Cada tenant tiene su propio set de herramientas cargadas en memoria.

## 4. Servicio de Warmup
Para evitar "cold starts" (latencia en el primer uso), el sistema cuenta con un servicio de pre-calentamiento:

- **Ejecución**: Se dispara en el `lifespan` de FastAPI.
- **Lógica**: Identifica todos los tenants activos y precarga sus flows y herramientas en el caché L1.
- **Configuración**: `src/services/warmup.py`.

## 5. Mantenimiento y Extensibilidad
- **Hot-Reload**: (Hito Post-MVP) El sistema está diseñado para invalidar el caché L1 cuando se importa un nuevo bundle, permitiendo actualizaciones sin reinicio.
- **Validación de Ciclos**: El registro realiza una validación completa del grafo de dependencias durante el registro de nuevos flujos.
