# 🧠 Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** g3h  
**Paso:** 14  
**Fase:** `guiAgentGenerator`  
**Fecha:** 2026-05-18  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

En cumplimiento estricto del umbral mínimo de verificación para proyectos con más de 10 archivos afectados (mínimo de 22 elementos verificados), se ha realizado una auditoría exhaustiva y directa sobre el código fuente real del proyecto.

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Migración `030_agent_templates.sql` | `ls supabase/migrations` | ✅ VERIFICADO | Archivo existe en `supabase/migrations/030_agent_templates.sql` |
| 2 | Tabla `agent_templates` | Lectura de migración | ✅ VERIFICADO | Definida en `030_agent_templates.sql`, líneas 10-21 |
| 3 | Política RLS `agent_templates` | Lectura de migración | ✅ VERIFICADO | Políticas `agent_templates_read` y `agent_templates_write` en líneas 25-29 |
| 4 | Componente `AgentForm.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/AgentForm.tsx` |
| 5 | Hook de LLM Model en `AgentForm.tsx` | Lectura de líneas 224-229 | ✅ VERIFICADO | `useEffect` con `// eslint-disable-next-line react-hooks/exhaustive-deps` dependiente únicamente de `llmProvider` |
| 6 | Payload en `AgentForm.tsx` | Lectura de líneas 203-222 | ✅ VERIFICADO | Función `buildSingleAgentPayload` recrea el objeto completo en cada ciclo de render |
| 7 | Inputs sin Debounce en `AgentForm.tsx` | Lectura de líneas 240-264 | ✅ VERIFICADO | Inputs `role`, `goal` y `backstory` vinculados a `register` directo de react-hook-form sin debounce |
| 8 | Componente `ToolMultiSelect.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/ToolMultiSelect.tsx` |
| 9 | Click Outside en `ToolMultiSelect.tsx` | Lectura de líneas 32-40 | ✅ VERIFICADO | `handleClickOutside` inline adjuntado a listener `mousedown` global |
| 10 | Componente `AgentPlayground.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/AgentPlayground.tsx` |
| 11 | Scroll manual en `AgentPlayground.tsx` | Lectura de líneas 58-62 | ✅ VERIFICADO | `scrollRef.current.scrollTop = scrollRef.current.scrollHeight` sobre un `div` dentro de `<ScrollArea>` |
| 12 | Import de ScrollArea | Lectura de línea 11 | ✅ VERIFICADO | Importado desde `@/components/ui/scroll-area` (Radix UI) |
| 13 | Contexto `BuilderTabContext.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/BuilderTabContext.tsx` |
| 14 | Estado de tabs en Contexto | Lectura de líneas 25-30 | ✅ VERIFICADO | Usa `useState` local únicamente sin sincronización con router de Next.js |
| 15 | Componente `BuilderLayout.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/BuilderLayout.tsx` |
| 16 | Mapeador de plantillas | Lectura de líneas 28-50 | ✅ VERIFICADO | Función `mapTemplateToFormValues` acoplada inline dentro del archivo de Layout |
| 17 | Import de Contexto en Layout | Lectura de línea 10 | ✅ VERIFICADO | Importa `useBuilderTab` de `@/components/builder/BuilderTabContext` |
| 18 | Componente `CrewCanvas.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/CrewCanvas.tsx` |
| 19 | Estilos ReactFlow en Canvas | Lectura de línea 48 | ✅ VERIFICADO | Importación síncrona `import 'reactflow/dist/style.css'` en el nivel raíz del archivo |
| 20 | Componente `ExportDialog.tsx` | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/ExportDialog.tsx` |
| 21 | Fallback de Clipboard en Export | Lectura de líneas 94-99 | ✅ VERIFICADO | Implementado con fallback visual vía toast si la API del portapapeles no está disponible |
| 22 | Import de fapDownload | Lectura de línea 14 | ✅ VERIFICADO | Importado desde `@/lib/api` |
| 23 | Cliente HTTP `api.ts` | `ls dashboard/lib/` | ✅ VERIFICADO | Archivo existe en `dashboard/lib/api.ts` |
| 24 | Método HTTP en `fapDownload` | Lectura de líneas 54-94 | ✅ VERIFICADO | `fapDownload` tiene el método `'POST'` codificado directamente en duro en la petición fetch |
| 25 | Archivo `constants.ts` | `ls dashboard/lib/` | ✅ VERIFICADO | Archivo existe en `dashboard/lib/constants.ts` |
| 26 | Métodos HTTP centralizados | Lectura de constants.ts | ❌ DISCREPANCIA | No existen constantes ni enums para los verbos HTTP |
| 27 | Dependencias de cmdk | Lectura de package.json | ❌ DISCREPANCIA | No está declarada en el bloque `dependencies` de `dashboard/package.json` |
| 28 | Entrada de página `page.tsx` | `ls dashboard/app/(app)/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/app/(app)/builder/page.tsx` |
| 29 | Breadcrumb de Builder | `ls dashboard/components/builder/` | ✅ VERIFICADO | Archivo existe en `dashboard/components/builder/BuilderBreadcrumb.tsx` |

### Discrepancias encontradas y resoluciones propuestas:

1. **D1: CSS de ReactFlow rompe bundle crítico de carga inicial (`CrewCanvas.tsx:48`):**  
   * **Descripción:** Se importa `reactflow/dist/style.css` directamente en el cuerpo global del módulo. Aunque el canvas se cargue perezosamente con Next.js dynamic imports, el CSS se inyecta en el bloque principal del frontend, degradando los tiempos de primer renderizado interactivo (FID) y First Contentful Paint (FCP).  
   * **Resolución:** Encapsular la carga del CSS dentro de un import dinámico diferido asíncrono o inyectar dinámicamente mediante `useEffect` al montar el canvas del canvas.

2. **D2: Error estructural de scroll en Radix ScrollArea (`AgentPlayground.tsx:58-62`):**  
   * **Descripción:** La referencia `scrollRef` apunta a un `div` contenedor interno, pero se intenta hacer scroll asignando `scrollRef.current.scrollTop = scrollRef.current.scrollHeight`. Debido a que Radix ScrollArea encapsula los elementos dentro de un viewport virtual (`ScrollAreaPrimitive.Viewport` que tiene los selectores de overflow real), este scroll manual queda inoperativo o causa comportamientos inestables de renderizado en navegadores basados en Chromium.  
   * **Resolución:** Reemplazar el `<ScrollArea>` por un `div` con `className="flex-1 overflow-y-auto"` que permita control directo y predecible de la propiedad `scrollTop` sobre la referencia real del viewport de scroll, o bien modificar la arquitectura para referenciar el viewport real de Radix.

3. **D3: Ausencia de deep linking y persistencia de pestañas (`BuilderTabContext.tsx`):**  
   * **Descripción:** El estado `activeTab` del constructor visual se almacena puramente en memoria del componente. Si el usuario recarga la página o realiza un refresco tras guardar un agente, el builder vuelve a la primera pestaña (`agent-form`), perdiendo todo el contexto de navegación en el canvas de crews.  
   * **Resolución:** Sincronizar bidireccionalmente el contexto de pestañas con la URL a través de query parameters (`?tab=`). Modificar `BuilderTabProvider` para aceptar e inicializar dinámicamente el estado a partir de los `searchParams` y actualizar la barra de direcciones usando el router nativo de Next.js sin recargar el navegador.

4. **D4: Acoplamiento del mapeador de plantillas en capa de UI (`BuilderLayout.tsx`):**  
   * **Descripción:** La función `mapTemplateToFormValues` está definida de forma inline dentro de `BuilderLayout.tsx` (líneas 28-50). Esto impide probar unitariamente esta lógica o reutilizarla en flujos del CLI de diagnóstico o en integraciones futuras.  
   * **Resolución:** Extraer esta lógica a un archivo aislado e independiente `dashboard/lib/template-mapper.ts` y exportar interfaces seguras para su uso global en el frontend.

5. **D5: Inexistencia de constantes HTTP y rigidez en fapDownload (`api.ts:54-94`):**  
   * **Descripción:** El cliente de descarga `fapDownload` está hardcodeado a `POST`, imposibilitando descargas parametrizadas vía `GET` sin escribir una capa de bypass compleja. Adicionalmente, el proyecto carece de constantes de métodos HTTP en `constants.ts`.  
   * **Resolución:** Parametrizar el verbo HTTP en `fapDownload` con un valor por defecto en `'POST'` y añadir el enum `HTTP_METHODS` a `constants.ts`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

El Paso 14 está categorizado como optimización de experiencia de usuario y rendimiento en el frontend. Por tanto:
* **Modificaciones a nivel de base de datos:** **Ninguna.** No requiere migraciones ni alteraciones en las tablas existentes en Supabase.
* **RLS (Row Level Security):** **Sin cambios.** No afecta la seguridad de datos al ejecutarse íntegramente en la capa cliente.
* **Tipos de datos de frontend:** Se implementa un nuevo contrato de mapeo para plantillas. Se define la interfaz en `dashboard/lib/template-mapper.ts`.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### 2.1 Módulo `dashboard/lib/template-mapper.ts` (Nuevo)
Extrae el acoplamiento de la interfaz desde `BuilderLayout.tsx`.

* **Firma de la función:**
```typescript
import type { AgentFormData } from '@/components/builder/AgentForm'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'

export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
```
* **Imports exactos requeridos:**
```typescript
import type { AgentFormData } from '@/components/builder/AgentForm'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'
```
* **Patrón de referencia a seguir:** `dashboard/lib/canvasUtils.ts` (módulos de transformación pura).

### 2.2 Hook `dashboard/hooks/useClickOutside.ts` (Nuevo)
Proporciona un hook reutilizable de detección de clics externos para selectores como `ToolMultiSelect.tsx` y futuros componentes interactivos.

* **Firma de la interfaz:**
```typescript
import { RefObject } from 'react'

export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: (event: MouseEvent | TouchEvent) => void,
  enabled?: boolean
): void
```
* **Patrón de referencia a seguir:** `dashboard/hooks/use-theme.tsx` (estilo de ciclo de vida con useEffect).

### 2.3 Hook `dashboard/hooks/useDebounce.ts` (Nuevo)
Previene re-renders interactivos masivos y costosos en los inputs de texto dinámicos (`goal`, `backstory`, etc.) y filtros de búsqueda instantánea.

* **Firma de la interfaz:**
```typescript
export function useDebounce<T>(value: T, delay?: number): T
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

El backend de FastAPI no recibe nuevos endpoints. Sin embargo, se optimiza el cliente HTTP del frontend `dashboard/lib/api.ts` para soportar contratos de API flexibles en descargas de bundles.

* **Firma del método optimizado en `dashboard/lib/api.ts`:**
```typescript
export async function fapDownload(
  path: string, 
  body: unknown, 
  method?: string
): Promise<Response>
```
* **Contrato cliente/servidor:**
```json
// POST /api/bundles/export - Payload esperado
{
  "bundle_name": "string",
  "agents": [
    {
      "role": "string",
      "soul_json": {},
      "allowed_tools": ["string"],
      "max_iter": 3
    }
  ]
}
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo de datos optimizado (End-to-End):

```
+------------------+     Tab Sync & Deep Linking     +---------------------+
|   Usuario/URL    | ==============================> | BuilderTabProvider  |
|  (?tab=canvas)   |                                 | (searchParams Sync) |
+------------------+                                 +---------------------+
                                                                ||
                                                     Renders active tab layout
                                                                ||
                                                                \/
                                                     +---------------------+
                                                     |    BuilderLayout    |
                                                     +---------------------+
                                                       /                 \
                                                      /                   \
                                                     \/                   \/
                                            +------------+         +-------------+
                                            | AgentForm  |         | CrewCanvas  |
                                            +------------+         +-------------+
                                            | - Debounce |         | - Lazy CSS  |
                                            | - useMemo  |         | - ReactFlow |
                                            +------------+         +-------------+
```

### DX & Tooling (OBLIGATORIO)

Para mitigar regresiones de rendimiento y asegurar que los estándares de diseño premium del dashboard se respeten en el futuro, se propone extender la CLI del sistema con una herramienta de diagnóstico estático y dinámico orientada al frontend.

```
### Herramienta Propuesta: fap doctor frontend
- **Qué automatiza:** Realiza auditorías automatizadas del código fuente del frontend, evaluando:
  1. Que los hooks de useEffect cumplan con la regla exhaustive-deps.
  2. Que los imports de CSS de ReactFlow estén cargados de manera diferida.
  3. Que las dependencias en package.json no contengan dependencias pesadas no autorizadas.
  4. Que la navegación con query params de deep linking (?tab=) esté configurada correctamente.
- **Tipo:** Comando de terminal integrado en la CLI corporativa de FluxAgentPro
- **Cómo se usa:** `python scripts/fap_doctor_frontend.py` o bien `fap doctor frontend`
- **Impacto para el usuario final:** Garantiza que cada cambio de desarrollo mantenga la latencia del Builder por debajo de los 150ms y libre de fugas de memoria por re-renders.
- **Prioridad:** Tarea 0 — Implementar y validar antes del inicio del despliegue del paso.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] El hook de detección `useClickOutside` existe en `dashboard/hooks/useClickOutside.ts` con tipado TypeScript estricto.
✅ [CODE] El componente `ToolMultiSelect.tsx` elimina el listener inline y consume el hook reusable `useClickOutside`.
✅ [CODE] El mapper de plantillas `mapTemplateToFormValues` se encuentra aislado en `dashboard/lib/template-mapper.ts`.
✅ [CODE] El componente `AgentForm.tsx` implementa `useCallback` sobre `buildSingleAgentPayload` para estabilizar referencias.
✅ [CODE] El hook de optimización `useDebounce` se encuentra disponible en `dashboard/hooks/useDebounce.ts`.
✅ [CODE] Se implementa debounce de 150ms en inputs reactivos de `AgentForm.tsx` y filtros de búsqueda de `TemplatePicker.tsx`.
✅ [CODE] `CrewCanvas.tsx` elimina la importación estática de `reactflow/dist/style.css` y la carga diferidamente con useEffect.
✅ [CODE] La función de descarga `fapDownload` en `dashboard/lib/api.ts` acepta un parámetro flexible para el verbo HTTP.
✅ [CODE] El enum `HTTP_METHODS` se encuentra centralizado en `dashboard/lib/constants.ts` y es importado de forma coherente.
✅ [FULLSTACK] La navegación de Builder sincroniza activamente la pestaña en URL query params `?tab=agent-form` o `?tab=crew-canvas`.
✅ [FULLSTACK] El refresco de pantalla o deep-linking sobre `/builder?tab=crew-canvas` inicializa correctamente la vista del canvas.
✅ [FULLSTACK] `AgentPlayground.tsx` realiza scroll automático interactivo al final de los mensajes usando un contenedor nativo.
✅ [DX] El comando `fap doctor frontend` corre con éxito y valida el cumplimiento de las directrices del análisis.
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Bucle infinito de renders por sincronización de Query Params | **Alta** | Un cambio reactivo en `BuilderTabContext` usando `useRouter` de Next.js puede gatillar re-renders recurrentes al invocar efectos en cascada en `BuilderLayout.tsx`. | Implementar un guardia condicional en `useEffect` que compare el estado en memoria con el valor exacto de `searchParams.get('tab')` antes de ejecutar la actualización. |
| Inconsistencias de estilos en carga diferida de ReactFlow CSS | **Media** | Retrasar la carga de `style.css` de ReactFlow puede causar un FOUC (Flash of Unstyled Content) momentáneo en la cuadrícula y nodos del canvas al montarse el componente. | Implementar un spinner o loader skeleton estilizado con Tailwind CSS mientras la hoja de estilos de ReactFlow no se haya inyectado al DOM. |
| Degradación de typing al desacoplar el mapeador | **Baja** | Diferencias de tipos entre la entidad interna del catálogo de Supabase y el schema de Zod. | Mantener interfaces de TypeScript estrictamente alineadas importando y extendiendo `TemplateDetail` y `AgentFormData` directamente en el mapper. |

---

## 7️⃣ Plan de Implementación

### Reglas de segmentación atómica aplicadas al 100%:
1. Cada tarea aborda única y exclusivamente **un archivo o artefacto**.
2. Las firmas e interfaces están especificadas de forma **rígida y exacta**, eliminando cualquier espacio a decisiones de diseño en fase de implementación.
3. Se proporcionan referencias a patrones de código existentes en el proyecto.
4. Cada paso incluye un comando explícito de **verificación inline**.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX Tooling:** Crear comando `fap doctor frontend` | `scripts/fap_doctor_frontend.py` | `def main(check_css: bool = True, check_hooks: bool = True) -> None` | `scripts/validate_builder_nav.py` | DX | Media | 1.0h | Ninguna | `python scripts/fap_doctor_frontend.py` responde sin errores. |
| 1 | Crear constantes HTTP | `dashboard/lib/constants.ts` | `export const HTTP_METHODS = { GET: 'GET', POST: 'POST', PUT: 'PUT', PATCH: 'PATCH', DELETE: 'DELETE' } as const` | Enums en `dashboard/lib/constants.ts` | CODE | Baja | 0.2h | Tarea 0 | Importable desde `dashboard/lib/api.ts` y compila sin errores. |
| 2 | Flexibilizar `fapDownload` | `dashboard/lib/api.ts` | `export async function fapDownload(path: string, body: unknown, method: string = HTTP_METHODS.POST): Promise<Response>` | Estructura de `fapFetch` | BACKEND | Baja | 0.3h | Tarea 1 | `npm run build` compila con éxito la firma flexible. |
| 3 | Crear hook `useClickOutside` | `dashboard/hooks/useClickOutside.ts` | `export function useClickOutside(ref: RefObject<HTMLElement>, handler: () => void): void` | `dashboard/hooks/use-theme.tsx` | CODE | Baja | 0.4h | Tarea 0 | `tsc --noEmit` valida la definición del hook de clics. |
| 4 | Refactorizar `ToolMultiSelect` | `dashboard/components/builder/ToolMultiSelect.tsx` | Reemplazar `useEffect` (líneas 32-40) por `useClickOutside(containerRef, () => setOpen(false))` | Consumo básico de custom hooks | CODE | Baja | 0.3h | Tarea 3 | Interacción de apertura y cierre de herramientas funciona en UI. |
| 5 | Crear módulo de mapeo | `dashboard/lib/template-mapper.ts` | `export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData` | `dashboard/lib/canvasUtils.ts` | CODE | Baja | 0.5h | Tarea 0 | Importación desde `BuilderLayout.tsx` sin discrepancias de TS. |
| 6 | Refactorizar `BuilderLayout` | `dashboard/components/builder/BuilderLayout.tsx` | Eliminar lines 28-50. Importar `mapTemplateToFormValues` de `@/lib/template-mapper`. | Imports absolutos de librerías del stack | CODE | Baja | 0.2h | Tarea 5 | Selección de plantilla auto-completa el formulario con éxito. |
| 7 | Crear hook `useDebounce` | `dashboard/hooks/useDebounce.ts` | `export function useDebounce<T>(value: T, delay: number = 150): T` | Estructura de hooks puros en React | CODE | Baja | 0.4h | Tarea 0 | Compila sin errores en `/hooks`. |
| 8 | Debounce de campos de texto | `dashboard/components/builder/AgentForm.tsx` | Envolver `watch` de `role`, `goal` y `backstory` en `useDebounce` antes de invocar los handlers reactivos. | Implementación estándar de debounce de estado | CODE | Media | 0.5h | Tarea 7 | `npm run lint` pasa sin advertencias de Exhaustive Deps. |
| 9 | Diferir carga de CSS de ReactFlow | `dashboard/components/builder/CrewCanvas.tsx` | Reemplazar `import 'reactflow/dist/style.css'` en línea 48 con carga dinámica vía `useEffect` al montar `FlowCanvas`. | dynamic imports asíncronos en React | CODE | Media | 0.5h | Tarea 0 | `reactflow/dist/style.css` cargado en DOM solo al inicializar canvas. |
| 10 | Sincronizar Tabs con URL query params | `dashboard/components/builder/BuilderTabContext.tsx` | `BuilderTabProvider` inicializa estado desde `searchParams.get('tab')` y muta vía `router.replace` al cambiar de pestaña. | Next.js navigation API | FULLSTACK | Alta | 1.0h | Tarea 0 | `/builder?tab=crew-canvas` inicializa la vista directamente en el canvas. |
| 11 | Corregir scroll en AgentPlayground | `dashboard/components/builder/AgentPlayground.tsx` | Reemplazar el contenedor `<ScrollArea>` de Radix UI por un div estándar con scroll nativo reactivo e interactivo. | Contenedores scroll viewport puros | CODE | Media | 0.5h | Tarea 0 | Al recibir respuestas del playground de agentes, se hace scroll al final. |
| 12 | Asegurar consistencia de tests | `tests/unit/test_ui_contracts.py` | Ejecutar pruebas unitarias para validar las nuevas rutas y constantes. | `tests/unit/` | FULLSTACK | Baja | 0.5h | Todas las anteriores | `uv run pytest tests/unit/` corre con éxito al 100%. |

**Tiempo total estimado de desarrollo:** 6.8 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Memoización Avanzada en Canvas:** Evaluar el uso de `React.memo` en los nodos personalizados del canvas (`AgentNode.tsx`, `TaskNode.tsx`) para reducir los ciclos de pintado cuando los edges son reordenados de forma manual por el usuario en el canvas.
2. **Combobox Completo via `cmdk`:** Llevar a cabo la integración definitiva de `cmdk` sobre `ToolMultiSelect.tsx` para mejorar la accesibilidad y permitir búsquedas avanzadas difusas (fuzzy search) cuando el catálogo de herramientas exceda los 50 elementos.
3. **Persistencia Local de Borrador de Pestañas:** Persistir de manera persistente las configuraciones del borrador activo en `localStorage` si el usuario decide cambiar de pestaña a mitad de la construcción de un flujo de crew.
