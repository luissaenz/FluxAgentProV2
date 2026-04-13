# Análisis Técnico — Paso 4.4: Implementar `AnalyticalAssistantChat.tsx` (Frontend)

## 1. Diseño Funcional

### 1.1 Problema que Resuelve
El componente `AnalyticalAssistantChat.tsx` **ya existe** en `dashboard/components/analytical/AnalyticalAssistantChat.tsx` con una implementación funcional completa. El problema real es que **no está integrado en el dashboard** — ningún layout, página o componente lo importa ni lo renderiza. El usuario no tiene forma de acceder al chat analítico desde la UI.

El Step 4.4 no es "crear el componente" sino **hacerlo accesible y funcional desde el dashboard del Analítica**, cumpliendo el criterio de aceptación de Fase 4:

> *"El chat analítico lateral es accesible y funcional desde el dashboard del frontend (Step 4.4)."*

### 1.2 Estado Actual del Componente
El componente ya implementa:
- ✅ UI de chat lateral con Sheet (radix/ui)
- ✅ Botón flotante (FAB) con ícono `Brain` en esquina inferior derecha
- ✅ Integración con `POST /analytical/ask` via TanStack Query mutation
- ✅ Integración con `GET /analytical/queries` para consultas rápidas
- ✅ Manejo de estados: loading, error, empty state con quick queries
- ✅ DataPreview: tabla que muestra hasta 5 filas de datos retornados
- ✅ Badges de query_type en respuestas
- ✅ Timestamps en cada mensaje
- ✅ Auto-scroll al último mensaje
- ✅ Manejo de errores del API (429, 400, 500)

### 1.3 Happy Path
1. Usuario navega a cualquier página del dashboard (Overview, Kanban, Tasks, etc.)
2. Ve un botón flotante (FAB) con ícono de cerebro (`Brain`) en la esquina inferior derecha **O** un ítem en la sidebar llamado "Asistente Analítico"
3. Al hacer clic, se abre un panel lateral (Sheet) con el chat analítico
4. Usuario escribe una pregunta en lenguaje natural: *"¿Cuál es el agente con mayor tasa de éxito?"*
5. El sistema muestra indicador de carga ("Analizando datos...")
6. El asistente responde con:
   - Un badge indicando el tipo de consulta ejecutada
   - Una respuesta narrativa en Markdown
   - Una tabla preview con los datos (hasta 5 filas)
7. Usuario puede hacer consultas rápidas desde el empty state inicial
8. El panel se cierra al hacer clic fuera o en el botón de cerrar

### 1.4 Edge Cases (MVP)
| Edge Case | Comportamiento Esperado |
|-----------|------------------------|
| API retorna 429 (rate limit) | Mensaje de error: "Demasiadas consultas analíticas. Esperá un momento." |
| API retorna 400 (query unknown) | Mensaje de error con las queries disponibles (ya implementado en el onError del mutation) |
| API retorna 500 (error interno) | Mensaje genérico: "Error al procesar la consulta." |
| API tarda >5s | Spinner de carga con texto "Analizando datos..." (ya implementado via `isPending`) |
| Sin conexión al servidor | Error de red manejado por el onError del mutation |
| Usuario envía pregunta vacía | Botón deshabilitado (ya implementado: `disabled={askMutation.isPending || !input.trim()}`) |

### 1.5 Manejo de Errores (UI)
- **Error del API**: Burbuja roja con `bg-destructive/10` y borde rojo — ya implementado
- **Timeout implícito**: No hay timeout explícito en el mutation — **AGREGAR**: `gcTime` y `timeout` en la mutation
- **Reintento**: No hay botón de reintentar en errores — **AGREGAR**: botón "Reintentar" en burbujas de error

---

## 2. Diseño Técnico

### 2.1 Componentes Actuales vs Necesarios

| Componente | Estado Actual | Acción Requerida |
|------------|--------------|-----------------|
| `AnalyticalAssistantChat.tsx` | ✅ Existe completo en `dashboard/components/analytical/` | **Integrar**: agregar al layout o sidebar del dashboard |
| Botón FAB (floating action button) | ✅ Implementado dentro del componente | **Mantener**: es el trigger del Sheet |
| Sheet lateral | ✅ Implementado con shadcn/ui Sheet | **Mantener**: funciona correctamente |
| EmptyState con quick queries | ✅ Implementado | **Mantener** |
| ChatMessageBubble | ✅ Implementado | **Mantener** |
| DataPreview (tabla) | ✅ Implementado | **Mantener** |
| Integración API `/analytical/ask` | ✅ via `api.post()` | **Mantener** |
| Integración API `/analytical/queries` | ✅ via `api.get()` | **Mantener** |

### 2.2 Estrategia de Integración

**Opción A: Botón global en el AppLayout (RECOMENDADA)**
- Agregar `<AnalyticalAssistantChat />` directamente en el `AppLayout` (`dashboard/app/(app)/layout.tsx`)
- El componente ya tiene su propio FAB (floating button) con `position: fixed bottom-4 right-4`
- Estará disponible en TODAS las páginas del dashboard, no solo en una específica
- **Ventaja**: Acceso universal, coherente con el patrón de "asistente siempre disponible"
- **Desventaja**: Ninguna significativa para MVP

**Opción B: Ítem en la sidebar**
- Agregar un ítem "Asistente Analítico" en `nav-main.tsx`
- Requeriría crear una página dedicada `/analytics` o hacer que el click abra el Sheet
- **Ventaja**: Más visible en la navegación
- **Desventaja**: Más complejo, requiere página dedicada o hack de estado compartido

**Opción C: Ambas (A + B)**
- FAB global + ítem en sidebar que abre el mismo Sheet
- Requiere estado compartido para controlar `isOpen` desde múltiples triggers
- **Ventaja**: Máxima accesibilidad
- **Desventaja**: Complejidad adicional — overkill para MVP

**Decisión: Opción A** — Agregar el componente al `AppLayout`. Es la solución más simple y el FAB ya proporciona visibilidad suficiente.

### 2.3 Cambios en Archivos

#### 2.3.1 `dashboard/app/(app)/layout.tsx`
Agregar el componente al final del `<main>`:

```tsx
import { AnalyticalAssistantChat } from '@/components/analytical/AnalyticalAssistantChat'

// ... dentro del return, después de {children}:
<main className="...">
  <div className="@container/main ...">
    <div className="...">
      {children}
    </div>
  </div>
  {/* Chat analítico flotante — disponible en todas las páginas */}
  <AnalyticalAssistantChat />
</main>
```

#### 2.3.2 Mejoras opcionales al componente existente

**Mejora 1: Timeout en la mutation**
```tsx
// Agregar al useMutation:
meta: {
  timeout: 30_000, // 30 segundos máximo
},
```

**Mejora 2: Botón de reintentar en errores**
En `ChatMessageBubble`, cuando `isError === true`, agregar un botón "Reintentar" que re-envíe la última pregunta del usuario.

**Mejora 3: Soporte básico de Markdown en el resumen**
Actualmente el summary se renderiza con `whitespace-pre-wrap`. El backend retorna Markdown (negritas, listas). Se podría usar una librería ligera como `react-markdown` para renderizar correctamente.
- **Complejidad**: Baja (solo agregar dependencia y cambiar `<p>` por `<ReactMarkdown>`)
- **Decisión MVP**: **NO** agregar dependencia nueva. El `whitespace-pre-wrap` muestra negritas como `**texto**` que es legible. Roadmap.

### 2.4 Modelos de Datos — Sin Cambios
No se requieren nuevas interfaces TypeScript. Las existentes (`ChatMessage`, `AnalyticalQuery`) cubren todo lo necesario.

### 2.5 Coherencia con `estado-fase.md`
- **Contrato API**: El componente ya usa `POST /analytical/ask` y `GET /analytical/queries` — coherente con el documento de estado.
- **Rate limiting**: El componente maneja HTTP 429 en el `onError` del mutation — coherente.
- **Metadata de respuesta**: El componente muestra `query_type` como badge y `data` como tabla — coherente con `AnalyticalAskResponse`.

---

## 3. Decisiones

### D1: Integrar en AppLayout en vez de crear página dedicada
**Justificación**: El chat analítico es una herramienta de consulta transversal — el usuario debería poder acceder desde cualquier contexto (mientras ve el Kanban, mientras revisa tasks, etc.). Un FAB global cumple este requirement sin crear rutas adicionales.
**Alternativa rechazada**: Página `/analytics` con el chat embebido — agregaría navegación innecesaria para una herramienta conversacional.

### D2: No agregar react-markdown para MVP
**Justificación**: El backend ya retorna Markdown con negritas (`**texto**`). Con `whitespace-pre-wrap` es legible aunque no se rendericen los estilos. Agregar `react-markdown` introduce una dependencia nueva y potencialmente conflictos de tipos.
**Roadmap**: Renderizado Markdown completo con gráficos embebidos.

### D3: No agregar botón de reintentar para MVP
**Justificación**: El usuario puede simplemente re-escribir la pregunta. El costo de implementar retry (guardar último user message, botón de reintentar, lógica de re-disparo) no justifica el beneficio para MVP.
**Roadmap**: Botón de reintentar en mensajes de error.

### D4: No agregar estado compartido para múltiples triggers
**Justificación**: Con el FAB es suficiente para MVP. Si en el futuro se quiere un ítem en la sidebar que también abra el chat, se puede elevar el estado `isOpen` a un context.
**Roadmap**: `AnalyticalChatContext` para controlar apertura desde múltiples puntos.

---

## 4. Criterios de Aceptación

- [ ] El componente `AnalyticalAssistantChat` está importado y renderizado en `dashboard/app/(app)/layout.tsx`
- [ ] El botón flotante (FAB) con ícono de cerebro es visible en TODAS las páginas del dashboard (Overview, Kanban, Tasks, Agents, Workflows, Events, Architect, Approvals, Tickets)
- [ ] Al hacer clic en el FAB, se abre el panel lateral (Sheet) con el chat analítico
- [ ] El empty state muestra las consultas rápidas obtenidas de `GET /analytical/queries`
- [ ] Al escribir una pregunta y enviar, se llama a `POST /analytical/ask` con el texto correcto
- [ ] Durante la carga, se muestra el spinner "Analizando datos..."
- [ ] La respuesta del asistente muestra: badge de query_type, resumen narrativo, y tabla preview con datos
- [ ] Los errores del API (429, 400, 500) se muestran como burbujas rojas con el mensaje correspondiente
- [ ] El panel se cierra correctamente al hacer clic fuera o en el botón de cerrar
- [ ] El auto-scroll funciona correctamente al agregar nuevos mensajes
- [ ] El dashboard compila sin errores (`npm run build` o `next build` pasa)
- [ ] No hay warnings de TypeScript en los archivos modificados

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Conflicto de z-index** entre el FAB y otros elementos fijos del dashboard (sidebar, header) | Medio | El FAB ya tiene `z-50`. Verificar que no se superponga con la sidebar colapsada (z-40 en shadcn) ni con el header (z-30). Si hay conflicto, ajustar a `z-45`. |
| **El FAB tapa contenido** en pantallas pequeñas | Bajo | El FAB está en `bottom-4 right-4`. En móvil, el Sheet ocupa toda la pantalla — verificar que el FAB no tape el botón de cerrar del Sheet. Si hay conflicto, mover FAB a `bottom-20 right-4` en pantallas < 768px. |
| **La mutation no tiene timeout** y puede colgarse indefinidamente si el backend no responde | Medio | Agregar `AbortController` o `signal` al fetcher de la mutation. Para MVP, confiar en el timeout por defecto de TanStack Query (que es `Infinity` — no ideal). **Mitigación MVP**: El usuario puede cerrar y reabrir el chat si se queda colgado. |
| **El Sheet no se resetea** al reabrir (mensajes anteriores persisten) | Bajo | Comportamiento esperado para MVP — el usuario puede ver el historial de la sesión. Si se desea limpiar al cerrar, agregar `onOpenChange={(open) => { if (!open) setMessages([]) }}`. **Decisión MVP**: Mantener historial de sesión. |
| **Dependencia de `@tanstack/react-query`** no instalada | Bajo | Ya está instalada (se usa en todo el dashboard). Verificar en `package.json` si hay dudas. |

---

## 6. Plan

### Tarea 1: Integrar `AnalyticalAssistantChat` en el AppLayout
- **Complejidad**: Baja
- **Dependencias**: Ninguna
- **Detalle**:
  1. Abrir `dashboard/app/(app)/layout.tsx`
  2. Agregar import: `import { AnalyticalAssistantChat } from '@/components/analytical/AnalyticalAssistantChat'`
  3. Agregar `<AnalyticalAssistantChat />` después de `{children}` dentro del `<main>`
  4. Verificar que el FAB es visible en todas las páginas

### Tarea 2: Verificar build sin errores
- **Complejidad**: Baja
- **Dependencias**: Tarea 1
- **Detalle**:
  1. Ejecutar `cd dashboard && npm run build` (o el comando de build del proyecto)
  2. Verificar que no hay errores de compilación
  3. Verificar que no hay warnings de TypeScript en los archivos modificados
  4. Si hay errores, resolverlos (probablemente ajustes de import path)

### Tarea 3: Verificación visual y funcional
- **Complejidad**: Baja
- **Dependencias**: Tarea 2
- **Detalle**:
  1. Levantar el dev server: `cd dashboard && npm run dev`
  2. Navegar a cada página del dashboard y verificar que el FAB es visible
  3. Abrir el chat y enviar una pregunta de prueba
  4. Verificar que la respuesta se muestra correctamente con datos y tabla preview
  5. Verificar que los errores se muestran correctamente (probar con pregunta fuera de dominio)
  6. Verificar que el auto-scroll funciona

### Orden y Dependencias
```
T1 (Integrar en Layout) ──→ T2 (Build) ──→ T3 (Verificación visual)
```

### Estimación de Complejidad Relativa
| Tarea | Complejidad |
|-------|-------------|
| T1: Integrar en Layout | Baja (3 líneas de cambio) |
| T2: Verificar build | Baja |
| T3: Verificación visual | Baja |

---

## 🔮 Roadmap (NO implementar ahora)

### Renderizado Markdown Completo
- **Qué**: Usar `react-markdown` o similar para renderizar negritas, listas, y formato del summary del LLM
- **Por qué no ahora**: El `whitespace-pre-wrap` es suficiente para MVP. Agregar dependencia y configurar tipos toma tiempo.
- **Preparación**: El contenido ya viene en Markdown del backend — solo falta el renderer.

### Botón de Reintentar en Errores
- **Qué**: Cuando un mensaje de error se muestra, agregar botón "Reintentar" que re-envía la última pregunta
- **Por qué no ahora**: El usuario puede re-escribir la pregunta manualmente
- **Preparación**: Guardar `lastUserQuestion` en el estado del componente

### Estado Compartido para Múltiples Triggers
- **Qué**: Crear `AnalyticalChatContext` para poder abrir el chat desde FAB + ítem de sidebar + atajo de teclado
- **Por qué no ahora**: El FAB es suficiente para MVP
- **Preparación**: Elevar `isOpen` y `setIsOpen` del componente a un Context Provider en el AppLayout

### Persistencia de Historial de Sesión
- **Qué**: Guardar los mensajes en `localStorage` o IndexedDB para que el historial persista entre recargas
- **Por qué no ahora**: MVP no requiere persistencia — cada sesión de navegación es suficiente
- **Preparación**: El estado `messages` ya es un array serializable — fácil de persistir

### Gráficos Embebidos en Respuestas
- **Qué**: Si la respuesta incluye datos numéricos, renderizar un mini gráfico (barras, línea) junto al summary
- **Por qué no ahora**: Requiere integrar librería de gráficos (recharts, chart.js) y lógica de mapeo datos→gráfico
- **Preparación**: El `data` field ya viene estructurado en la respuesta — listo para alimentar un gráfico

### Atajo de Teclado (Cmd+Shift+A)
- **Qué**: Abrir el chat analítico con un keyboard shortcut
- **Por qué no ahora**: Feature de conveniencia, no esencial para MVP
- **Preparación**: El `isOpen` state puede ser controlado por un listener de teclado en el AppLayout

### Streaming de Respuestas
- **Qué**: Mostrar la respuesta del LLM mientras se genera (SSE o chunked transfer)
- **Por qué no ahora**: El backend actual retorna la respuesta completa — requeriría cambiar el endpoint a SSE
- **Preparación**: El frontend ya tiene un estado `isPending` — fácil de migrar a streaming con `onMessage` en vez de `onSuccess`
