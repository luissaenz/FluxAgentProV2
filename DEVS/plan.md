# Builder Visual de Agentes — Integración FAP

> Fase: `guiAgentGenerator`  
> Objetivo: Replicar la experiencia de creación visual de agentes de CrewAI AMP (Crew Studio) dentro del dashboard FAP existente, construido 100% sobre stack propio (Next.js + ReactFlow + FastAPI + Supabase), sin dependencia de código cerrado.

---

## Paso 01: Crear endpoint `GET /api/tools/available`

### Objetivo
Exponer el `ToolRegistry` y `MCPPool` del backend como API REST para que el builder visual pueda listar herramientas disponibles.

### Tareas
- [ ] Añadir endpoint `GET /api/tools/available` en módulo `src/api/routes/tools.py` (nuevo archivo)
- [ ] Registrar router en `src/api/__init__.py`
- [ ] Devolver lista de tools con: name, description, category, source (local/mcp)
- [ ] Incluir filtro `?source=local|mcp`

### Criterios de aceptación
- Endpoint responde 200 con array de tools
- Las tools de MCPPool aparecen con prefijo `mcp:server:tool`
- Las tools locales aparecen con su nombre registrado
- Timeout < 500ms

---

## Paso 02: Crear endpoint `POST /api/bundles/export`

### Objetivo
Permitir al builder visual exportar agentes como bundle ZIP (formato `bundle-schema-v2.md`), igual que el import existente pero en reversa.

### Tareas
- [ ] Añadir endpoint `POST /api/bundles/export` en `src/api/routes/bundles.py`
- [ ] Aceptar payload: `{ agents: [{role, soul_json, allowed_tools, max_iter}], skills?: [{name, code}] }`
- [ ] Generar estructura ZIP: `manifest.json` + `agents/*.json` + `skills/*.py`
- [ ] Devolver `StreamingResponse` con ZIP para descarga directa
- [ ] Validar que los agentes tengan `role`, `goal`, `backstory` antes de empaquetar

### Criterios de aceptación
- POST con datos válidos → ZIP descargable
- ZIP contiene `manifest.json` válido según schema v2
- `manifest.json` incluye `bundle_info` + `hashes`
- POST con datos inválidos → 422 con errores específicos
- ZIP se puede re-importar con `POST /api/bundles/import` sin errores

---

## Paso 03: Endpoints CRUD para templates de agentes

### Objetivo
Crear tabla `agent_templates` en Supabase + endpoints REST para alimentar la librería de templates del builder (equivalente al Template Library de Crew Studio).

### Tareas
- [ ] Crear migración Supabase: tabla `agent_templates` (id UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN)
- [ ] Añadir migración en `supabase/migrations/`
- [ ] Crear módulo `src/api/routes/templates.py` con:
  - `GET /api/templates` — listar templates (filtro `?category=`)
  - `GET /api/templates/{id}` — obtener template específico
- [ ] Registrar router en `src/api/__init__.py`
- [ ] Seed inicial con 8 templates predefinidos (Research Agent, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant)

### Criterios de aceptación
- Tabla `agent_templates` creada con migración versionada
- `GET /api/templates` devuelve array de templates
- `GET /api/templates/{id}` devuelve template completo con `soul_json`
- Filtro `?category=` funciona
- Seed contiene al menos 8 templates con `is_system: true`
- RLS aplicado: lectura pública, escritura solo system

---

## Paso 04: Página del builder — layout y formulario de agente

### Objetivo
Añadir ruta `/dashboard/app/builder` con el layout del builder visual: panel izquierdo (canvas ReactFlow) + panel derecho (formulario de agente). El formulario replica todos los campos del `Agent` de CrewAI.

### Tareas
- [ ] Instalar `reactflow` en el dashboard (`npm install reactflow`)
- [ ] Crear `dashboard/app/(app)/builder/page.tsx` — entrada del builder
- [ ] Crear `dashboard/components/builder/AgentForm.tsx` con campos:
  - Role (input), Goal (textarea), Backstory (textarea)
  - LLM Provider (select: Groq/OpenAI/Anthropic/OpenRouter)
  - LLM Model (select dinámico según provider)
  - Tools (multi-select desde `GET /api/tools/available`)
  - Max Iterations (slider 1-10, default 3)
  - Toggles: Verbose, Reasoning, Inject Date, Memory
- [ ] Crear `dashboard/components/builder/BuilderCanvas.tsx` — contenedor ReactFlow (vacío inicialmente, se poblará en Paso 07)
- [ ] Crear `dashboard/components/builder/BuilderLayout.tsx` — layout split panel (60% izquierda canvas / 40% derecha formulario)
- [ ] Validación con Zod: `role`, `goal`, `backstory` requeridos
- [ ] Botón "Save Agent" → guarda en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)
- [ ] Botón "Clear" → resetea formulario

### Criterios de aceptación
- Ruta `/builder` accesible desde la navegación del dashboard
- Layout responsive: panel izquierdo + panel derecho
- Formulario con todos los campos del Agent de CrewAI
- Validación Zod: no permite guardar sin role/goal/backstory
- Guardado persiste en Supabase `agent_catalog`
- Select de tools carga desde el endpoint real

---

## Paso 05: Template Picker — librería de templates

### Objetivo
Añadir el selector de templates al builder (equivalente al Template Library de Crew Studio). El usuario elige un template y el formulario se auto-completa.

### Tareas
- [ ] Crear `dashboard/components/builder/TemplatePicker.tsx` — grid/modal de templates
- [ ] Cargar templates desde `GET /api/templates`
- [ ] Mostrar cards con: nombre, descripción, categoría, tools sugeridos
- [ ] Botón "Use Template" → rellena el formulario AgentForm con los datos del template
- [ ] Filtro por categoría (chips: Research, Development, Support, General)
- [ ] Barra de búsqueda por nombre

### Criterios de aceptación
- TemplatePicker visible desde el builder (botón "Templates" o panel superior)
- Templates cargan desde API real
- Al hacer clic en "Use Template", el formulario se rellena
- Filtro por categoría funciona
- Búsqueda por texto funciona
- Estado de carga y error manejados

---

## Paso 06: Agent Playground — prueba en tiempo real

### Objetivo
Añadir panel de chat para probar un agente en tiempo real (equivalente al "Real-time testing" de Crew Studio). Permite enviar un mensaje al agente recién creado/editado y ver la respuesta + tool calls.

### Tareas
- [ ] Crear `dashboard/components/builder/AgentPlayground.tsx` — panel de chat
- [ ] Conectar con `POST /agents/{role}/run` del backend
- [ ] Implementar polling a `GET /tasks/{task_id}` para obtener resultado
- [ ] Mostrar: mensaje del usuario, respuesta del agente, tool calls ejecutadas (con nombre y argumentos)
- [ ] Indicador de carga mientras el agente procesa
- [ ] Usar `TaskResponse.tokens_used` para mostrar tokens consumidos
- [ ] Historial local de mensajes durante la sesión (no persiste)

### Criterios de aceptación
- Input de chat funcional: write message → Enter → enviar
- Respuesta del agente se muestra debajo del mensaje
- Tool calls se listan con nombre + argumentos (formato colapsable)
- Indicador de carga durante ejecución
- Tokens usados visibles al finalizar
- Manejo de errores: agente no encontrado, timeout, fallo de ejecución

---

## Paso 07: Canvas visual — ensamblaje de crews

### Objetivo
Implementar el canvas ReactFlow con nodos drag-and-drop para ensamblar crews visualmente. El usuario arrastra agentes y tareas, los conecta, y genera una crew ejecutable.

### Tareas
- [ ] Crear `dashboard/components/builder/nodes/AgentNode.tsx` — nodo visual para agente
- [ ] Crear `dashboard/components/builder/nodes/TaskNode.tsx` — nodo visual para tarea
- [ ] Crear `dashboard/components/builder/nodes/ToolNode.tsx` — nodo visual para herramienta
- [ ] Crear `dashboard/components/builder/CrewCanvas.tsx` — canvas completo con:
  - Sidebar de nodos arrastrables (lista de agentes existentes, tareas disponibles)
  - Área de drop donde se ensambla el crew
  - Conexiones entre nodos (agent → task)
  - Validación visual: agentes sin tareas = warning
- [ ] Botón "Export as Crew" → serializa el grafo a:
  - JSON compatible con `bundle-schema-v2.md`
  - Código Python equivalente (vista previa)
- [ ] Botón "Run Crew" → ejecuta el crew vía `POST /flows/{flow_type}/run` y muestra resultado
- [ ] Mini-mapa y controles de zoom en el canvas

### Criterios de aceptación
- Drag & drop de agentes desde sidebar al canvas
- Conexiones visuales entre nodos (edges)
- Nodo de agente muestra role + tools asignadas
- Nodo de tarea muestra description + expected_output
- Export genera JSON compatible con bundle-schema-v2.md
- Vista previa de código Python generado
- Canvas tiene minimapa + zoom controls

---

## Paso 08: ExportDialog + flujo completo de exportación

### Objetivo
Diálogo de exportación que consume el endpoint `POST /api/bundles/export` y permite descargar el crew ensamblado como bundle ZIP listo para importar o compartir.

### Tareas
- [ ] Crear `dashboard/components/builder/ExportDialog.tsx`
- [ ] Mostrar resumen pre-export: agentes incluidos, skills, flows
- [ ] Opción "Include skills" (checkbox) — si hay herramientas personalizadas
- [ ] Botón "Export" → llama `POST /api/bundles/export` → descarga ZIP
- [ ] Feedback visual: progreso de generación, nombre del archivo, tamaño
- [ ] Integrar ExportDialog en:
  - AgentForm (exportar un solo agente)
  - CrewCanvas (exportar crew completo con tareas)
- [ ] Opción "Copy as JSON" — copia el JSON del bundle al portapapeles sin descargar ZIP

### Criterios de aceptación
- Diálogo muestra resumen de lo que se va a exportar
- Botón Export descarga un ZIP válido
- ZIP se puede re-importar con el Import Wizard existente en `/integrations/bundles`
- "Copy as JSON" copia al portapapeles correctamente
- Manejo de errores: ZIP vacío, agentes sin role, timeout

---

## Paso 09: Navegación, breadcrumbs e integración

### Objetivo
Integrar el builder en la navegación del dashboard existente, con breadcrumbs, acceso desde el sidebar, y coherencia visual con el resto de páginas.

### Tareas
- [ ] Añadir enlace "Builder" en el sidebar del dashboard (componente existente)
- [ ] Breadcrumbs: Dashboard > Builder > [New Agent | Crew Canvas | Templates]
- [ ] Añadir ruta en la barra de navegación principal
- [ ] Asegurar consistencia visual (shadcn/ui components, colores, tipografía)
- [ ] Loading states para todas las páginas del builder
- [ ] Error boundaries para el canvas (ReactFlow puede fallar en SSR)

### Criterios de aceptación
- Builder accesible desde sidebar con ícono + label
- Breadcrumbs funcionales en todas las subpáginas del builder
- Estilo visual consistente con el resto del dashboard
- Canvas no rompe en SSR (cargado solo en cliente con `dynamic import`)
- Loading skeletons mientras cargan tools/templates

---

## Paso 10: Tests E2E del builder

### Objetivo
Tests end-to-end que validen el flujo completo del builder: crear agente → probarlo → ensamblar crew → exportar → re-importar.

### Tareas
- [ ] Test: crear agente con formulario y guardar en Supabase
- [ ] Test: seleccionar template y verificar que rellena el formulario
- [ ] Test: probar agente en playground y verificar respuesta
- [ ] Test: ensamblar crew en canvas (drag agent + task + conectar)
- [ ] Test: exportar crew como ZIP y validar estructura
- [ ] Test: importar ZIP exportado y verificar agentes en catálogo
- [ ] Test: endpoint `GET /api/tools/available` devuelve tools reales
- [ ] Test: endpoint `POST /api/bundles/export` genera ZIP válido
- [ ] Test: endpoint `GET /api/templates` devuelve templates

### Criterios de aceptación
- Todos los tests pasan en `uv run pytest tests/e2e/ -k builder`
- Cobertura de flujo completo: crear → probar → ensamblar → exportar → importar
- Tests usan Supabase real (no mock) para validar integración
