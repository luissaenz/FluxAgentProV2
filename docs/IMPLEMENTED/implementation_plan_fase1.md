# Plan de Implementación: Fase 1 — Motor Base

Este plan de implementación está diseñado basado en la especificación final del documento `FASE1-FinalDefinition.html`. El objetivo de esta fase es construir un sistema de orquestación base capaz de:
1. Recibir un evento vía webhook externo.
2. Registrar y ejecutar un Flow en _background_.
3. Orquestar el estado conectándolo a agentes de IA usando CrewAI.
4. Persistir el estado y eventos con `TenantClient` en Supabase con soporte RLS.
5. Devolver resultados de la ejecución a través de _polling_.

El sistema final debe pasar la suite de pruebas al **100% sin depender de LLMs o infraestructura real** en los tests.

---

## 1. Configuración de Entorno y Preparación
Antes de escribir el código de negocio, debemos asegurar que las dependencias, carpetas y configuraciones base existan.

- [ ] **1.1. Dependencias Base (`pyproject.toml`)**
  - Instalar `crewai`, `crewai-tools`, `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `supabase`, `psycopg2-binary`, `anthropic`, `openai` y herramientas de testeo.
- [ ] **1.2. Configuración Global (`src/config.py`)**
  - Configurar las variables de entorno usando `pydantic-settings` (URL y API Keys de Supabase, LLMs).
- [ ] **1.3. Archivo `.env` y `.env.example`**
  - Declaración de las claves `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.

## 2. Base de Datos y Seguridad (RLS)
Soporte de _Tenant_ (Multi-org) habilitando funciones RPC y `TenantClient`.

- [ ] **2.1. Funciones RPC y RLS en base de datos**
  - Crear archivo `supabase/migrations/001_set_config_rpc.sql`.
  - Definir la función RPC `set_config` para ajustar `app.org_id` y `app.user_id` en PostgreSQL.
  - Definir `current_org_id()` para leer local settings.
  - Asegurar aplicación del RLS en todas las tablas usando el context `app.org_id`.
- [ ] **2.2. Cliente Manejador de Sesiones (`src/db/session.py`)**
  - Crear el _Context Manager_ `TenantClient` / `get_tenant_client` para conectar e inyectar el context del Tenant usando la función RPC `set_config`.

## 3. Registros (_Registries_)
Mecanismos para desacoplar el Gateway de la instanciación directa de Flows y Tools.

- [ ] **3.1. Registry de Flows (`src/flows/registry.py`)**
  - Implementar contenedor de clases `Flow` con el patrón `@register_flow()`.
- [ ] **3.2. Registry de Tools (`src/tools/registry.py`)**
  - Implementar el decorador `@register_tool()` para centralizar herramientas utilizables por CrewAI junto con la metadata.
- [ ] **3.3. Herramientas Integradas (`src/tools/builtin.py`)**
  - Implementar archivo con algunas herramientas mockeadas o registradas para validar.

## 4. Patrón Flow y Event Sourcing
El core duro de la fase 1, donde vive la lógica para ejecutar y resguardar resultados asincrónicamente.

- [ ] **4.1. BaseFlowState (`src/flows/state.py`)**
  - Definir el Enum `FlowStatus`.
  - Crear el modelo Pydantic `BaseFlowState` con validación fuerte de UUIDs y _timestamps_.
- [ ] **4.2. Event Store (`src/events/store.py`)**
  - Centralizar dominio de eventos inmutables.
  - Crear la función `append()` en memoria y `flush()` transaccional hacia la tabla `domain_events`.
- [ ] **4.3. Implementación Ciclo de Vida del Flow (`src/flows/base_flow.py`)**
  - Crear clase base `BaseFlow`.
  - Implementar manejo genérico de error con `@with_error_handling`.
  - Crear la orquestación: `validate_input()`, `create_task_record()`, `start()`, `_run_crew()`, `complete()/fail()`, y `emit_event()`. 

## 5. Implementación del Caso de Uso Específico (Dummy)
Primer Flujo funcional usando el motor base creado.

- [ ] **5.1. Crew Genérico (`src/crews/generic_crew.py`)**
  - Crear Factory Method `create_generic_crew()` que devuelva el Crew mock configurado con un Text Processor Agent.
- [ ] **5.2. Flow Genérico (`src/flows/generic_flow.py`)**
  - Extender `BaseFlow` y auto-registrarse.
  - Recibe entrada tipo cadena de texto y dispara el `generic_crew` para el proceso.

## 6. API y Capa de Ingreso (Endpoints)
Exposición de la API HTTP con FastAPI hacia sistemas clientes.

- [ ] **6.1. Identidad mediante Middlewares (`src/api/middleware.py`)**
  - Configurar extracción del Header `X-Org-ID`.
- [ ] **6.2. Webhooks HTTP Route (`src/api/routes/webhooks.py`)**
  - Implementar `POST /webhooks/trigger` que instancie la ejecución genérica como _background_task_ de FastAPI y devuelva código `202`.
- [ ] **6.3. Tareas (Polling HTTP Route) (`src/api/routes/tasks.py`)**
  - Implementar `GET /tasks/{task_id}` para evaluar el cierre / estado de los flujos activos conectándose a Supabase mediante variables controladas por `TenantClient()`.
  - Implementar `GET /tasks` con filtros de límite.
- [ ] **6.4. Inicialización Global API (`src/api/main.py`)**
  - Declaración del Router unificado de FastAPI con carga adelantada de `generic_flow` para activar su registro.

## 7. Pruebas y Consolidación (Testing)
Pruebas integradas completas, garantizando que todo el pipeline corre sin depender de infraestructuras de pagos.

- [ ] **7.1 Fixtures Universales (`tests/conftest.py`)**
  - Mockear cliente de Supabase y contexto Async, eliminando impactos en la DB real.
  - Definir IDs y data estandarizada para las pruebas (`sample_org_id`, etc).
- [ ] **7.2. Test de Ciclo Unitario (`tests/unit/test_baseflow.py`)**
  - Validar correctamente estados: validación fallida, `validate_input()`, inserción, retornos finalizados y errores explícitos mediante el patrón mock.
- [ ] **7.3. Test End-to-End (`tests/e2e/test_webhook_to_completion.py`)**
  - Verificar en contexto integral el trigger desde `TestClient(app)` hasta el estado `completed`.

---

## Reglas Invariables del Proyecto
Para mantener la escalabilidad del producto, se asumen por sistema las siguientes normas estrictas para desarrollo:

1. **Estado canónico en DB**: El estado vive siempre en las tablas de `snapshots` o `tasks`. La memoria solo retiene el tránsito. 
2. **RLS Obligatorio**: Absolutamente toda inserción/modificación y lectura debe venir apalancado del `TenantClient()`.
3. **Event Sourcing**: Modificación de estado impacta y emite asincrónicamente un log temporal inmutable (`domain_events`).
4. **Zero Hardcoding**: Los keys, auth tokens y credenciales de usuario/sistema provienen siempre del Request (`headers`, `payload`) u ambiente OS.
5. **No Instanciamiento Directo de Flujos**: Todo `BaseFlow` debe llamarse dinámicamente utilizando `flow_registry.get("...")`. 
6. **Tests como criterio total**: Toda historia se reporta funcional única y exclusivamente cuando la cobertura `pytest tests/` llega a 100%.
