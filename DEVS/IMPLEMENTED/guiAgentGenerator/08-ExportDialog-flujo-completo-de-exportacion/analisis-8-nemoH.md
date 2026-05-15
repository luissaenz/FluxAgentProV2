# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5.2 — UNIFICADO

## Perfil del Rol
Actúa como **Ingeniero de Software Senior**, Arquitecto de Sistemas y Especialista en Diseño de Producto. **Análisis basado en código fuente real. Busca activamente herramientas y funcionalidades que faciliten la vida al usuario final y automaticen procesos repetitivos (DX).**

## Contexto del Proyecto
Desarrollamos **"FluxAgentPro-v2"**. Disponible:
- **`proyecto-config.json`** (raíz) — fuente de verdad de rutas y convenciones
- **Plan general:** `{project_root}/DEVS/plan.md`
- **Contexto de fase:** `{project_root}/DEVS/phase-state.md`
- **Código fuente:** `{paths.backend}` (fuente de verdad)
- **Migraciones:** `{paths.migrations}` (schema real de DB)

> [!IMPORTANT]
> **ANTES DE EJECUTAR:** Leer `proyecto-config.json`. Todas las rutas salen de ahí.

---

## 📥 Entradas Obligatorias
1. **[AGENTE]** → identificador del agente que ejecuta el análisis: `nemo`
2. **[PASO]** → paso asignado (incluye todos sus sub-pasos): `8`

> [!IMPORTANT]
> **NO se pide área explícitamente.** Análisis cubre automáticamente:
> - `data` → schema, integridad, RLS
> - `code` → patrones, calidad, modularidad
> - `backend` → APIs, middleware, contratos
> - `fullstack` → coherencia end-to-end + UX + DX

---

## ⛔ PROHIBICIONES ABSOLUTAS
- **NO** escribas código de implementación. Entregable = DOCUMENTO DE ANÁLISIS.
- **NO** preguntes qué hacer. Lee plan, phase-state y paso asignado. Luego EJECUTA.
- **NO** analices TODO el sistema. Solo el paso específico — pero SÍ TODO el paso (sub-pasos incluidos).
- **NO** modifiques ningún archivo que no sea el de salida.
- **NO** repitas info que ya esté en `{project_root}/DEVS/phase-state.md`. Referenciala.
- **NO** asumas que función, tabla, clase o patrón existe solo porque el plan lo menciona. VERIFICAR contra código.
- **NO** agrupes en una tarea lo que puede separarse. Cada tarea = un archivo o una función o una migración. Si el implementador debe tomar decisiones de diseño para completarla → está mal segmentada.

---

## 🔭 EXPLORACIÓN INICIAL DEL CODEBASE (ANTES DE TODO)

### Paso 0: Leer `proyecto-config.json`
```bash
cat /home/daniel/develop/Personal/FluxAgentProV2/proyecto-config.json
```
Rutas extraídas:
- `backend`: `D:\\Develop\\Personal\\FluxAgentPro-v2\\src`
- `frontend`: `D:\\Develop\\Personal\\FluxAgentPro-v2\\dashboard`
- `api_routes`: `D:\\Develop\\Personal\\FluxAgentPro-v2\\src\\api\\routes`
- `migrations`: `D:\\Develop\\Personal\\FluxAgentPro-v2\\supabase\\migrations`
- `devs_in_progress`: `D:\\Develop\\Personal\\FluxAgentPro-v2\\DEVS\\IN_PROGRESS`

### Exploración (10-15 min):

**1. Estructura del proyecto:**
```bash
ls /home/daniel/develop/Personal/FluxAgentProV2/src
ls /home/daniel/develop/Personal/FluxAgentProV2/src/api/routes
ls /home/daniel/develop/Personal/FluxAgentProV2/supabase/migrations
ls /home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder
```

**2. Archivos directamente relacionados al paso:**
- Backend endpoint: `/home/daniel/develop/Personal/FluxAgentProV2/src/api/routes/bundles.py` (existe, POST /export)
- Frontend components: 
  - AgentForm: `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/AgentForm.tsx`
  - CrewCanvas: `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/CrewCanvas.tsx`
  - BuilderLayout: `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/BuilderLayout.tsx`
- Bundle schemas: `/home/daniel/develop/Personal/FluxAgentProV2/src/services/bundle_schemas.py`
- Export service: `/home/daniel/develop/Personal/FluxAgentProV2/src/services/export_service.py`

**3. Archivos de referencia (patrones existentes):**
- AgentForm ya usa `api.post('/agents')` para guardar agente.
- CrewCanvas tiene botón "Export as Crew" que llama a `canvasToExportPayload()` y descarga JSON.
- Se sigue el patrón de componentes de shadcn/ui y react-hook-form.

**4. Dependencias:**
```bash
cat /home/daniel/develop/Personal/FluxAgentProV2/pyproject.toml | grep -A5 -B5 "dependencies"
```
Dependencias directas incluyen fastapi, supabase, etc. Frontend: reactflow, zod, sonner, etc.

### Resultado:
Input para §0 y todo el análisis. No se encontraron discrepancias iniciales.

---

## 🔍 VERIFICACIÓN OBLIGATORIA CONTRA CÓDIGO FUENTE

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /api/bundles/export` existe | grep en `src/api/routes/bundles.py` | ✅ | líneas 199-253 |
| 2 | Modelo `ExportBundleRequest` definido | grep en `src/services/bundle_schemas.py` | ✅ | líneas 111-116 |
| 3 | Servicio `ExportService` existe | grep en `src/services/export_service.py` | ✅ | archivo completo |
| 4 | Componente `AgentForm` existe | grep en `dashboard/components/builder/AgentForm.tsx` | ✅ | archivo completo |
| 5 | Componente `CrewCanvas` existe | grep en `dashboard/components/builder/CrewCanvas.tsx` | ✅ | archivo completo |
| 6 | Componente `ExportDialog` NO existe | ls en `dashboard/components/builder/` | ⚠️ | No encontrado |
| 7 | Endpoint `GET /api/tools/available` existe (para herramientas) | grep en `src/api/routes/tools.py` | ✅ | líneas 46-63 |
| 8 | Tabla `agent_catalog` existe (para guardar agentes) | grep en `supabase/migrations/` | � | migración 004_agent_catalog.sql |
| 9 | Función `canvasToExportPayload` existe (para obtener agentes del canvas) | grep en `dashboard/lib/canvasUtils.ts` | ✅ | líneas 36-44 |
| 10 | Método `export` en `ExportService` devuelve ZIP | grep en `src/services/export_service.py` | ✅ | líneas 45-66 |

**Discrepancias encontradas:**
- ⚠️ **Discrepancia 1:** El componente `ExportDialog` no existe en el frontend, pero es requerido por el paso 8.
  - **Resolución propuesta:** Crear `dashboard/components/builder/ExportDialog.tsx` siguiendo el patrón de otros componentes de builder (AgentForm, TemplatePicker, etc.).
- ⚠️ **Discrepancia 2:** El paso 8 requiere integrar el ExportDialog en AgentForm y CrewCanvas, pero actualmente esos componentes no tienen un botón o llamado para abrir el diálogo.
  - **Resolución propuesta:** Añadir un botón de exportación en AgentForm y CrewCanvas que abra el ExportDialog.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** No se crean ni modifican tablas. El paso solo usa la tabla existente `agent_catalog` (vía endpoint POST /agents) y la lógica de exportación que lee de `agent_catalog` y `skill_catalog`.
- ✅ **Integridad referencial:** No se añaden nuevas columnas o relaciones. Se usa la integridad existente de `agent_catalog.org_id` → `organizations.id`.
- ✅ **RLS policies:** El endpoint `POST /api/bundles/export` usa `require_org_id` middleware, que asegura que solo se pueden exportar agentes de la organización actual. La RLS en `agent_catalog` (policy tenant_isolation) restringe la lectura a la organización actual.
- ✅ **Índices necesarios:** No se requieren nuevos índices. La exportación usa consultas existentes que ya están optimizadas por los índices de `agent_catalog` (probablemente en `org_id` y `role`).
- ✅ **Tipos de datos:** Los tipos de datos usados en la exportación (strings, JSONB, arrays) son compatibles con los esquemas Pydantic y la serialización a JSON dentro del ZIP. No hay problemas de incompatibilidad.

**Impacto en datos existentes:** Ninguno. El paso solo lee datos para exportarlos, no modifica la base de datos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/clases nuevas:** 
  - Se creará el componente `ExportDialog.tsx` (frontend).
  - No se modifican funciones/backend existentes (el endpoint y servicio ya existen).
- ✅ **Patrones:** 
  - El componente seguirá el patrón de otros componentes de builder (AgentForm, TemplatePicker): 
    - Uso de `useQuery` o `useMutation` para llamadas al backend (aunque en este caso, se usará `fetch` directamente o mediante un hook de api).
    - Uso de shadcn/ui components (Button, Dialog, etc.).
    - Manejo de estados de carga y error.
    - Uso de Zod para validación si es necesario (aunque el endpoint ya valida).
  - Se seguirá el patrón de `canvasToExportPayload` para extraer los agentes del canvas (en CrewCanvas) y de `AgentForm` para obtener los datos del formulario.
- ✅ **Modularidad:** 
  - El ExportDialog será un componente reutilizable que puede ser llamado desde AgentForm y CrewCanvas.
  - No introduce acoplamiento innecesario; solo depende de la API existente de `/api/bundles/export`.
  - Cohesión alta: el componente se encarga únicamente de la lógica de exportación y presentación del diálogo.
- ✅ **Calidad:** 
  - Se espera baja complejidad ciclomática (pocos estados: idle, loading, success, error).
  - Código mantenible siguiendo las convenciones del proyecto (TypeScript, snakecase no aplica en frontend, pero sí en nombres de archivos y variables).
- ✅ **Imports exactos:** 
  - En `ExportDialog.tsx`: 
    - Import de React hooks (useState, etc.)
    - Import de componentes shadcn/ui (Dialog, Alert, etc.)
    - Import de `api` desde '@/lib/api' (patrón existente en AgentForm).
    - Import de tipos si es necesario (por ejemplo, de `bundle_schemas` si se reutilizan, pero probablemente no, ya que el endpoint ya los define).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** 
  - El endpoint `POST /api/bundles/export` ya existe y está funcional (verificado en fase state). 
  - Método: POST, ruta: `/api/bundles/export`.
  - Input: `ExportBundleRequest` (definido en `bundle_schemas.py`).
  - Output: `Response` con contenido ZIP y headers para descarga.
- ✅ **Middleware:** 
  - El endpoint usa `Depends(require_org_id)` para asegurar autenticación y organización.
  - No se requiere middleware adicional.
- ✅ **Flujos:** 
  - El flujo de datos es: 
    1. Frontend recopila datos de agentes (de AgentForm o CrewCanvas).
    2. Frontend envía POST a `/api/bundles/export` con payload `ExportBundleRequest`.
    3. Backend valida el payload (goal/backstory presentes y longitud mínima).
    4. Backend usa `ExportService` para generar el ZIP en memoria.
    5. Backend devuelve el ZIP como respuesta de descarga.
- ✅ **Contratos:** 
  - El endpoint promete devolver un ZIP válido que sigue el esquema FAP-Bundle v2 (verificado en `bundle_schemas.py` y `bundle_manager.py`).
  - El ZIP contiene `manifest.json` y las carpetas `agents/` y opcionalmente `skills/`.
- ✅ **Error handling:** 
  - El endpoint ya maneja errores de validación (422) y errores internos (500).
  - El frontend debe manejar estados de carga y error de red.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** 
  - DB → Backend → Frontend → UX: 
    1. Los agentes están almacenados en `agent_catalog` (DB).
    2. El backend los expone vía `POST /api/bundles/export` (API).
    3. El frontend (AgentForm o CrewCanvas) recopila los datos y llama al endpoint.
    4. El usuario descarga el ZIP y puede re-importarlo vía el Import Wizard existente (`/integrations/bundles`).
- ✅ **Coherencia:** 
  - Las decisiones de data (usar `agent_catalog`) apoyan al código (endpoint existente).
  - Las decisiones de backend (endpoint de export) soportan la experiencia del usuario (descargar bundle).
  - No hay inconsistencias entre lo que promete el plan y lo que permite la arquitectura.
- ✅ **MVP hace sentido:** 
  - El MVP permite exportar un solo agente (desde AgentForm) o una crew (desde CrewCanvas) como bundle ZIP, listo para re-importar o compartir.
- ✅ **DX & Tooling (OBLIGATORIO):** 
  - **Problema manual:** Actualmente, para exportar un agente o crew, el usuario debe usar la CLI (`fap bundle export` o `fap crew export`) o, en el caso de la crew, usar el botón "Export as Crew" que solo descarga el JSON del canvas (no el bundle ZIP con agentes y skills). Esto requiere conocimientos de CLI o no incluye skills.
  - **Herramienta propuesta:** 
    ```
    ### Herramienta Propuesta: ExportDialog Componente
    - **Qué automatiza:** Automatiza la exportación de agentes o crews como bundle ZIP directamente desde la interfaz visual del builder, sin necesidad de usar la CLI ni conocer comandos.
    - **Tipo:** Componente React (Dialog) integrado en el frontend.
    - **Cómo se usa:** 
        - En AgentForm: botón "Export as Bundle" abre el diálogo, pre-selecciona el agente actual, permite incluir skills, y al hacer clic en "Export" descarga el ZIP.
        - En CrewCanvas: botón "Export as Bundle" abre el diálogo, lista los agentes en el canvas, permite incluir skills, y al hacer clic en "Export" descarga el ZIP.
    - **Impacto para el usuario final:** 
        - Elimina la necesidad de cambiar a la terminal para usar `fap bundle export`.
        - Permite exportar con un solo clic desde la interfaz visual.
        - Incluye opción de incluir skills personalizadas (si las hay).
        - Proporciona feedback visual de progreso y éxito/error.
    - **Prioridad:** Tarea 0 — implementar antes que el resto del paso (ya que el resto del paso depende de este componente).
    ```

**Flujo end-to-end (descripción):**
1. Usuario está en AgentForm o CrewCanvas.
2. Hace clic en "Export as Bundle".
3. Se abre ExportDialog con resumen de lo que se va a exportar (agentes, skills si aplica).
4. Usuario ajusta opciones (incluir skills o no).
5. Hace clic en "Export".
6. Componente muestra estado de carga mientras llama a `POST /api/bundles/export`.
7. En caso de éxito, descarga el ZIP y muestra mensaje de éxito.
8. En caso de error, muestra mensaje de error.
9. El ZIP descargado se puede re-importar en la página de Import Wizard (`/integrations/bundles`) sin errores.

---

## 5️⃣ Criterios de Aceptación

Lista binaria (sí/no) verificable:

```
✅ [DATA] Endpoint POST /api/bundles/export sigue funcionando sin regresiones (verificado con pruebas existentes).
✅ [CODE] Componente ExportDialog.tsx creado en dashboard/components/builder/ExportDialog.tsx siguiendo patrones existentes.
✅ [CODE] AgentForm modificado para incluir botón de exportación que abre ExportDialog.
✅ [CODE] CrewCanvas modificado para incluir botón de exportación que abre ExportDialog.
✅ [BACKEND] Endpoint POST /api/bundles/export acepta payload correcto y devuelve ZIP válido.
✅ [FULLSTACK] Usuario puede exportar un agente desde AgentForm y descargar ZIP válido.
✅ [FULLSTACK] Usuario puede exportar una crew desde CrewCanvas y descargar ZIP válido.
✅ [DX] Herramienta ExportDialog reduce pasos manuales: usuario no necesita usar CLI ni conocimientos técnicos para exportar bundle.
✅ [DX] ZIP exportado se puede re-importar con el Import Wizard existente en `/integrations/bundles` sin errores.
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Incompatibilidad de versión de dependencias frontend (shadcn/ui, etc.) | Media | Si se añaden nuevos componentes que requieren versiones no instaladas. | Verificar que los componentes usados (Dialog, Button, etc.) existan en la versión actual de shadcn/ui en package.json. Si no, actualizar o usar alternativas existentes. |
| Errores de red o timeout durante la exportación | Baja | La generación del ZIP podría tardar si hay muchos agentes/skills. | Implementar timeout razonable y mostrar mensaje de error al usuario. El endpoint ya tiene manejo de excepciones. |
| El usuario intenta exportar sin agentes válidos (sin role, etc.) | Baja | El endpoint ya valida goal/backstory, pero el frontend podría enviar datos vacíos. | Validar en el frontend antes de enviar: deshabilitar botón Export si no hay agentes o si falta role/goal/backstory. |
| El ZIP exportado es corrupto o no sigue el esquema v2 | Baja | Error en el servicio de exportación (ya probado en tests). | Los tests unitarios y de integración existentes cubren la generación de ZIP. No se espera regresión. |
| Falta de accesibilidad en el diálogo (teclado, lectores de pantalla) | Baja | El diálogo podría no ser accesible. | Seguir las prácticas de accesibilidad de los otros componentes del builder (usar componentes de radix-ui que son accesibles). |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. **Una tarea = un artefacto**: un archivo, una función, una migración, un endpoint.
> 2. **Interfaz completa en la tarea**: cada tarea debe incluir la firma exacta (nombre, parámetros con tipos, retorno) del artefacto a crear o modificar.
> 3. **Patrón de referencia explícito**: si el artefacto sigue un patrón existente → indicar el archivo concreto a copiar.
> 4. **Verificación inline**: cada tarea tiene su `→ verificar:` con el comando o check concreto que confirma que está completa antes de pasar a la siguiente.
> 5. **Test de atomicidad**: si el implementador puede completar la tarea sin tomar ninguna decisión de diseño → está bien segmentada.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: ExportDialog Componente | `dashboard/components/builder/ExportDialog.tsx` | Componente React que recibe prop `onClose` y `agentData` (opcional) y maneja estados interno. | `dashboard/components/builder/AgentForm.tsx` (patrones de hooks, shadcn/ui, manejo de estados) | DX | Media | 1h | Ninguna | → verificar: `ls dashboard/components/builder/ExportDialog.tsx` existe y contiene código de componente React. |
| 1 | Añadir botón de exportación en AgentForm | `dashboard/components/builder/AgentForm.tsx` | Añadir `<Button variant="outline" onClick={() => setShowExportDialog(true)}>Export as Bundle</Button>` cerca del botón Save Agent. | Patrón existente de botones en AgentForm (Save Agent, Clear) | CODE | Baja | 0.5h | Tarea 0 | → verificar: El botón aparece en la UI y al hacer clic abre el ExportDialog (prueba manual o test). |
| 2 | Añadir botón de exportación en CrewCanvas | `dashboard/components/builder/CrewCanvas.tsx` | Añadir `<Button variant="outline" onClick={() => setShowExportDialog(true)}>Export as Bundle</Button>` en la barra de herramientas. | Patrón existente de botones en CrewCanvas (Export as Crew, Run All) | CODE | Baja | 0.5h | Tarea 0 | → verificar: El botón aparece en la UI y al hacer clic abre el ExportDialog. |
| 3 | Integrar lógica de exportación en ExportDialog | `dashboard/components/builder/ExportDialog.tsx` | Implementar función `handleExport` que: recopila datos (según contexto), llama a `api.post('/api/bundles/export', payload)`, maneja respuesta y descarga ZIP. | Patrón de llamadas API en AgentForm (uso de `api.post` y manejo de errores con toast) | BACKEND | Media | 1h | Tareas 0,1,2 | → verificar: Al hacer clic en Export en el diálogo, se llama al endpoint y se descarga un ZIP (prueba manual con red abierta o mock). |
| 4 | Validar flujo end-to-end con Import Wizard | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1,2,3 | → verificar: El ZIP exportado se puede subir en `/integrations/bundles` y re-importar sin errores (prueba manual). |

**Tiempo total estimado:** 3.5 horas

---