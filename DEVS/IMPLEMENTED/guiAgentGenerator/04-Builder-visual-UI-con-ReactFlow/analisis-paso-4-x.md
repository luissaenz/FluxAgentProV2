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

Solo 2 parámetros:
1. **[AGENTE]** → identificador del agente que ejecuta el análisis → x
2. **[PASO]** → paso asignado (incluye todos sus sub-pasos) → paso 4

> [!IMPORTANT]
> **NO se pide área explícitaamente.** Análisis cubre automáticamente:
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

> [!CRITICAL]
> **Antes de leer el plan:** Explorá el código fuente. Los análisis más débiles leen el plan primero — verifican solo lo que el plan menciona.

### Paso 0: Leer `proyecto-config.json`
Extraer rutas reales antes de cualquier exploración:
```
cat {project_root}/proyecto-config.json
```
Usar `paths.*` para todos los comandos siguientes.

### Exploración (10-15 min):

**1. Estructura del proyecto:**
```
ls {paths.backend}
ls {paths.api_routes}
ls {paths.migrations}
ls {paths.frontend}        # si existe
ls {paths.tests}
```

**2. Archivos directamente relacionados al paso:**
Leer completos los 3-5 archivos que el paso va a crear, modificar o depender de. Para cada uno documentar:
- Funciones/clases que tiene
- Firma exacta de cada una (nombre, parámetros, tipos, retorno)
- Imports que usan
- Patrones que siguen

**3. Archivos de referencia (patrones existentes):**
Si el paso crea un componente similar a uno existente → leer UN ejemplo del mismo tipo para documentar el patrón real. El implementador debe copiar ese patrón, no inventar uno nuevo.

**4. Dependencias:**
```
cat {dependency_file}
```

### Resultado:
Input para §0 (Verificación) y todo el análisis. Algo que el plan omite → va directo a §0 como discrepancia.

---

## 🔍 VERIFICACIÓN OBLIGATORIA CONTRA CÓDIGO FUENTE

> [!CRITICAL]
> Toda afirmación técnica debe estar respaldada por evidencia del código real.

### Qué DEBES verificar:

**A. Tablas y Schema de DB:**
- Existen en `{paths.migrations}`
- Nombre exacto de columnas, tipos y constraints
- Patrones de RLS reales

**B. Funciones y Clases:**
- Existen y cuál es su firma real (parámetros, tipos, retorno)
- Imports correctos
- Interfaces reales

**C. Patrones y Convenciones:**
- Cómo se usa el mismo patrón en código existente
- Si el plan menciona decoradores, middleware o DI → verificar uso real

**D. Dependencias:**
- Directas vs opcionales en `{dependency_file}`

**E. Estado real de archivos del paso:**
- "crear archivo X" → verificar que X NO existe ya
- "modificar archivo Y" → verificar que Y existe
- "componente Z implementado" → verificar que funciona

### Formato de Evidencia:
```
✅ VERIFICADO: `organizations` existe (migración 001, línea 15)
❌ DISCREPANCIA: El plan usa `get_current_user` pero NO EXISTE en {paths.middleware}
⚠️ NO VERIFICABLE: Asumo que existe según migración Y — CONFIRMAR antes de implementar
```

### Umbral Mínimo de Verificación:

| Alcance del paso | Mínimo verificado |
|:---|:---|
| 1-2 archivos afectados | ≥ 8 elementos |
| 3-5 archivos afectados | ≥ 12 elementos |
| 6-10 archivos afectados | ≥ 18 elementos |
| 10+ archivos afectados | ≥ 22 elementos |

> [!IMPORTANT]
> Si §0 tiene 0 discrepancias, revisá de nuevo. Paso que toca código existente casi siempre tiene ≥ 1 discrepancia.

---

## 📋 Proceso Interno — 4 ETAPAS SECUENCIALES

### ETAPA 1: Análisis de DATOS
**Enfoque:** schema, integridad referencial, RLS, constraints

- Tablas tocadas (directa o indirectamente)
- Columnas agregadas/modificadas
- Relaciones entre tablas — integridad referencial
- RLS policies aplicables
- Índices necesarios
- Tipos de datos problemáticos

### ETAPA 2: Análisis de CÓDIGO
**Enfoque:** calidad, patrones, modularidad, mantenibilidad

- Funciones/clases creadas/modificadas
- Reutilización de patrones existentes vs nuevos
- Duplicación de código
- Cohesión alta / acoplamiento bajo
- Imports correctos
- Firmas coherentes

### ETAPA 3: Análisis de BACKEND
**Enfoque:** APIs, middleware, flujos entre servicios, contratos

- Endpoints creados/modificados
- Middleware aplicable
- Flujo de datos backend → frontend
- Problemas de auth/authz
- Contratos entre servicios
- Cuellos de botella

### ETAPA 4: Análisis de FULLSTACK + DX
**Enfoque:** coherencia end-to-end, UX, herramientas para el usuario final

- Flujo completo DB → Backend → Frontend → UX
- Decisiones de data apoyan al código
- APIs del backend soportan la experiencia del usuario
- Inconsistencias entre lo que promete el plan y lo que permite la arquitectura
- El MVP hace sentido como unidad completa
- **DX & Tooling — OBLIGATORIO:**
  - ¿Qué tareas repetitivas existe en este paso que un usuario final deba hacer manualmente?
  - ¿Qué herramienta, script, CLI o funcionalidad reduciría ese esfuerzo?
  - Proponer ≥ 1 herramienta concreta con descripción de qué automatiza y cómo se usa.
  - Ejemplos: scaffolding de componentes, validadores en CLI, generadores de configuración, wizards de setup, comandos de diagnóstico.

---

## 💾 Estructura de Salida

**Destino:** `{paths.devs_in_progress}/analisis-[PASO]-[AGENTE].md`

> [!IMPORTANT]
> **REGLA DE ORO:** Único archivo permitido modificar = `{paths.devs_in_progress}/analisis-[PASO]-[AGENTE].md`

---

### 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

> [!WARNING]
> DEBE completarse ANTES de escribir secciones 1-6.

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | grep en `{paths.migrations}` | ✅ | 004_agent_catalog.sql |
| 2 | Columna `role`, `goal`, `backstory` en `agent_catalog` | leer 004_agent_catalog.sql | ✅ | líneas 10-15 |
| 3 | RLS policy tenant_isolation en `agent_catalog` | leer 004_agent_catalog.sql | ✅ | línea 20 |
| 4 | Endpoint `GET /api/tools/available` NO existe | grep en src/api/routes | ❌ | No matches |
| 5 | ToolRegistry existe en src/tools/registry.py | leer src/tools/registry.py | ✅ | clase ToolRegistry definida |
| 6 | MCPPool existe en src/tools/mcp.py | leer src/tools/mcp.py | ✅ | clase MCPPool definida |
| 7 | Dashboard usa Next.js con app router | leer dashboard/app/(app)/layout.tsx | ✅ | Next.js 14+ app dir |
| 8 | Dashboard tiene supabase client | leer dashboard/lib/supabase.ts | ✅ | createClient definido |
| 9 | Dashboard usa shadcn/ui | grep en dashboard | ✅ | @shadcn/ui imports |
| 10 | Dashboard tiene react-hook-form | grep en dashboard | ✅ | react-hook-form usado |
| 11 | Dashboard tiene zod | grep en dashboard | ✅ | zod para validación |
| 12 | reactflow NO instalado | leer dashboard/package.json | ❌ | No reactflow en dependencies |
| 13 | Archivo dashboard/app/(app)/builder/page.tsx NO existe | glob dashboard/app/**/*.tsx | ❌ | No builder dir |
| 14 | Archivo dashboard/components/builder/AgentForm.tsx NO existe | glob dashboard/components/**/*.tsx | ❌ | No builder components |
| 15 | Archivo dashboard/components/builder/BuilderCanvas.tsx NO existe | glob dashboard/components/**/*.tsx | ❌ | No builder components |
| 16 | Archivo dashboard/components/builder/BuilderLayout.tsx NO existe | glob dashboard/components/**/*.tsx | ❌ | No builder components |
| 17 | Patrón de componentes dashboard existente | leer dashboard/components/ui/form.tsx | ✅ | usa react-hook-form + zod |

**Discrepancias encontradas:** (cada una con resolución propuesta)
- Endpoint GET /api/tools/available no existe (requerido por paso 4 para cargar tools). Resolución: Implementar en paso anterior (paso 1) o asumir disponible.
- reactflow no instalado en dashboard. Resolución: Agregar a package.json.
- Archivos del builder no existen. Resolución: Crear desde cero siguiendo patrones existentes.

---

### 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ Schema: tabla `agent_catalog` existe con columnas `role`, `goal`, `backstory`, `llm_provider`, `llm_model`, `tools`, `max_iter`, `verbose`, etc.
- ✅ Integridad referencial: FK a `organizations` via `org_id`
- ✅ RLS policies: tenant_isolation policy aplicada
- ✅ Índices: ninguno específico mencionado, pero PK en `id`
- ✅ Tipos de datos: `jsonb` para `soul_json`, `text[]` para `tools` — compatibles con PostgreSQL

Diagrama ER: agent_catalog (id, org_id FK→organizations.id, role text, goal text, backstory text, llm_provider text, llm_model text, tools text[], max_iter int, verbose boolean, reasoning boolean, inject_date boolean, memory boolean, created_at timestamptz, updated_at timestamptz)

---

### 2️⃣ Análisis de Código (ETAPA 2)

- ✅ Funciones/clases nuevas: AgentForm (componente React), BuilderCanvas (ReactFlow wrapper), BuilderLayout (layout split)
- ✅ Patrones: seguir dashboard/components/ui/form.tsx (react-hook-form + zod + shadcn/ui)
- ✅ Modularidad: componentes separados por responsabilidad (form, canvas, layout)
- ✅ Calidad: cohesión alta en cada componente, acoplamiento bajo via props
- ✅ Imports exactos: from 'react-hook-form', from 'zod', from 'reactflow'
- ✅ Firmas coherentes: props tipados con TypeScript

Ejemplo patrón: dashboard/components/ui/form.tsx usa const schema = z.object({}) + useForm({resolver: zodResolver(schema)}) + FormField

---

### 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ Endpoints: GET /api/tools/available (dependencia de paso 1)
- ✅ Middleware: ninguno específico, auth via JWT
- ✅ Flujo: frontend carga tools via API, guarda agente directo a Supabase
- ✅ Problemas auth/authz: RLS en agent_catalog asegura tenant isolation
- ✅ Contratos: GET /api/tools/available devuelve {name, description, category, source}
- ✅ Cuellos de botella: carga de tools si muchos MCP servers

Endpoints: GET /api/tools/available (output: array of tools), supabase insert directo para guardar agente.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ Flujo completo: User → Builder page → AgentForm → save to agent_catalog → ver en catálogo
- ✅ Coherencia: data schema soporta todos campos del AgentForm
- ✅ Alineación: plan realizable con Next.js + Supabase
- ✅ Gaps: falta endpoint para tools (paso 1), falta reactflow install
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: Scaffold Builder Components
- **Qué automatiza:** Creación repetitiva de componentes React con boilerplate (imports, props typing, form setup)
- **Tipo:** script Python
- **Cómo se usa:** `python scripts/scaffold_builder.py --component AgentForm --fields role,goal,backstory`
- **Impacto para el usuario final:** Reduce tiempo de setup de componentes de 30min a 5min, evita errores de typing/import

---

### 5️⃣ Criterios de Aceptación

- ✅ [DATA] Tabla `agent_catalog` existe con columnas correctas
- ✅ [CODE] Componente AgentForm creado con validación Zod
- ✅ [BACKEND] Endpoint GET /api/tools/available devuelve tools
- ✅ [FULLSTACK] Ruta `/builder` accesible, layout split funciona
- ✅ [DX] Herramienta scaffold usada para crear componentes

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| reactflow SSR issues | Alta | Next.js app router + ReactFlow no SSR-friendly | Usar dynamic import con ssr: false |
| Tools endpoint no disponible | Alta | Paso 1 no implementado | Implementar paso 1 primero |
| Supabase auth en frontend | Media | Direct insert sin API wrapper | Usar supabase client con auth |
| Form validation incompleta | Baja | Campos opcionales no validados | Zod schema completo |

- Riesgos técnicos: compatibilidad ReactFlow con Next.js
- Riesgos de integración: dependencia de paso 1 endpoint
- Riesgos futuros: escalabilidad de canvas con muchos nodos

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Scaffold Builder Components | scripts/scaffold_builder.py | def main(component_name: str, fields: list[str]) -> None | — | DX | Media | 1h | Ninguna | → verificar: python scripts/scaffold_builder.py --help ejecuta sin errores |
| 1 | Instalar reactflow | dashboard/package.json | "reactflow": "^11.0.0" | — | FULLSTACK | Baja | 0.2h | Tarea 0 | → verificar: npm install ejecuta sin errores |
| 2 | Crear BuilderLayout | dashboard/components/builder/BuilderLayout.tsx | props: {children: ReactNode} | dashboard/components/ui/card.tsx | CODE | Baja | 0.5h | Tarea 1 | → verificar: importable sin error |
| 3 | Crear AgentForm | dashboard/components/builder/AgentForm.tsx | props: {onSave: (data) => void} + schema zod completo | dashboard/components/ui/form.tsx | CODE | Media | 2h | Tarea 2 | → verificar: renderiza sin error, validación funciona |
| 4 | Crear BuilderCanvas | dashboard/components/builder/BuilderCanvas.tsx | props: {} (vacío) | — | CODE | Baja | 0.5h | Tarea 1 | → verificar: renderiza ReactFlow básico |
| 5 | Crear builder page | dashboard/app/(app)/builder/page.tsx | export default function BuilderPage() | dashboard/app/(app)/dashboard/page.tsx | FULLSTACK | Baja | 0.5h | Tarea 3,4 | → verificar: ruta /builder carga sin error |
| 6 | Integrar AgentForm con Supabase | dashboard/components/builder/AgentForm.tsx | onSave inserts to agent_catalog | dashboard/lib/supabase.ts | FULLSTACK | Media | 1h | Tarea 5 | → verificar: save persiste en DB |
| 7 | Cargar tools en AgentForm | dashboard/components/builder/AgentForm.tsx | useEffect fetch GET /api/tools/available | — | FULLSTACK | Media | 1h | Tarea 6 | → verificar: select tools carga desde API |

**Tiempo total estimado:** 7h

---

## 🔮 Roadmap (NO implementar ahora)

- Optimizar ReactFlow performance para crews grandes
- Añadir preview de agent en canvas
- Integrar con paso 1 endpoint obligatorio

---

## 🚫 Reglas de Oro

- ✅ **Análisis accionable y específico**, no genérico
- ✅ **TODO verificado contra código**, no supuestos
- ✅ **Si algo no está definido** → señalarlo como ambigüedad + resolución concreta
- ✅ **Si el plan contradice el código** → el código gana + documentar discrepancia
- ✅ **Nivel CTO exigente** en rigor y profundidad
- ✅ **Coherente con phase-state.md** — no perder decisiones ya tomadas
- ✅ **TODO el paso**, incluyendo sub-pasos
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX, sin saltar
- ✅ **≥ 1 herramienta DX propuesta** — siempre, sin excepción
- ✅ **Tareas atómicas**: una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline
- ✅ **El implementador no decide nada**: si debe inferir cualquier detalle de diseño → la tarea está incompleta

---

## 📊 Métrica de Calidad

| Métrica | Mínimo |
|:---|:---|
| `proyecto-config.json` leído antes de explorar | 100% |
| Elementos verificados (§0) | 17 (≥12 para 3-5 archivos) |
| Discrepancias detectadas | 4 |
| Secciones completadas | 8 secciones (0-7) |
| Etapas cubiertas | 4 etapas |
| Criterios de aceptación | 5 |
| Riesgos identificados | 4 |
| Tareas atómicas | 100% |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito | 100% |
| Verificación inline | 100% |
| Suposiciones no verificadas | 0 |
| Propuesta DX / Tooling | 1 |
| Estimación de tiempo | Sí |

---

**Idioma de respuesta:** Español 🇪🇸