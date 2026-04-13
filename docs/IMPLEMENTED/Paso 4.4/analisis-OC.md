# 📋 ANÁLISIS TÉCNICO — Paso 4.4: Implementar AnalyticalAssistantChat.tsx

## 1. Diseño Funcional

### 1.1 Objetivo del Paso
El paso 4.4 busca completar la experiencia analítica en el frontend proporcionando un chat lateral accesible desde cualquier vista del dashboard, permitiendo al usuario realizar consultas en lenguaje natural sobre datos históricos y métricas de negocio.

### 1.2 Happy Path Detallado
1. El usuario ve un botón flotante (FAB) con icono de cerebro en la esquina inferior derecha del dashboard.
2. Al hacer clic, se abre un Sheet (drawer) desde el lado derecho con el chat analítico.
3. El chat muestra un estado vacío con:
   - Mensaje de bienvenida: "Asistente Analítico"
   - Lista de consultas rápidas disponibles (obtenidas de `GET /analytical/queries`).
4. El usuario puede:
   - Escribir una pregunta en el input (ej: "¿Cuál es el agente con mayor tasa de éxito?") y presionar Enter o el botón de enviar.
   - Hacer clic en una consulta rápida para ejecutarla automáticamente.
5. Mientras se procesa la pregunta:
   - El input se deshabilita.
   - El botón de envío muestra un spinner.
   - Aparece un mensaje de "Analizando datos..." con spinner.
6. Al recibir la respuesta:
   - Se muestra el mensaje del asistente con el `summary` de la respuesta.
   - Debajo del texto, se renderiza una tabla con los datos (`data`) limitada a 5 filas (+indicador de más filas).
   - Se muestra un badge con el `query_type` detectado/ejecutado.
   - El timestamp del mensaje se muestra en formato HH:MM.
7. El usuario puede continuar interactuando, acumulando historial de conversación.
8. El usuario puede cerrar el sheet y elFAB vuelve a su posición.

### 1.3 Edge Cases Relevantes para MVP
- **Sin organización activa:** El chat no debe mostrar error visible; el backend rejected con 401/403 por `require_org_id`. El componente debe manejar esto gracefully (no está implementado actualmente, pero el API client maneja el header automáticamente).
- **Rate limiting (429):** El backend devuelve 429 si se exceden 10 req/min. El componente debe mostrar el mensaje del error: "Demasiadas consultas analíticas. Esperá un momento."
- **Query type inválido (400):** Si el LLM no puede clasificar la intención, el backend devuelve 400 con `message` y `available_queries`. Mostrar este mensaje al usuario.
- **Error de conexión (500):** El componente debe mostrar el mensaje de error del backend en un mensaje de tipo "error" (estilo rojo).
- **Sin datos en la respuesta:** El componente renderiza la tabla solo si hay datos; si `data` es array vacío, solo muestra el `summary`.
- **Mensajes muy largos:** El componente usa `whitespace-pre-wrap` para preservar saltos de línea del `summary`.

### 1.4 Manejo de Errores
- **API error (cualquier código 4xx/5xx):** El `onError` de la mutación extrae `error?.detail?.message` y lo agrega como mensaje de tipo "error" con estilos rojos.
- **Fallback visual:** Si no hay mensajes, se muestra el EmptyState con consultas rápidas.
- **Loading state:** Spinner en el botón de envío y mensaje "Analizando datos...".

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados
- **Nuevo componente:** `dashboard/components/analytical/AnalyticalAssistantChat.tsx` (ya existe implementado).
- **Dependencias de UI:**
  - `@/components/ui/sheet` (Shadcn UI) - para el drawer lateral.
  - `@/components/ui/scroll-area` - para scroll dentro del chat.
  - `@/components/ui/input` - para el campo de texto.
  - `@/components/ui/button` - para acciones.
  - `@/components/ui/badge` - para mostrar query_type.
  - `@/components/ui/skeleton` - para loading de consultas rápidas.
  - `@/lib/api` - para llamadas HTTP.
  - `@tanstack/react-query` - para estado de datos y mutaciones.

### 2.2 Integración Requerida (PENDIENTE)
El componente NO está integrado en ningún layout o página. Se DEBE agregar al layout principal `dashboard/app/(app)/layout.tsx` para que esté disponible globalmente:

```tsx
import { AnalyticalAssistantChat } from '@/components/analytical/AnalyticalAssistantChat'

// En el return del layout, después del children:
<main>...{children}<AnalyticalAssistantChat /></main>
```

### 2.3 Modelos de Datos
El componente consume la siguiente interfaz de la API:

```typescript
// GET /analytical/queries
interface AnalyticalQueryInfo {
  key: string       // ej: "agent_success_rate"
  description: string  // ej: "Tasa de éxito de agentes en los últimos 7 días"
}

// POST /analytical/ask
// Request: { question: string, query_type?: string }
// Response:
interface AnalyticalAskResponse {
  question: string
  query_type: string
  data: Record<string, unknown>[]  // Array de objetos para la tabla
  summary: string                    // Texto narrativo en Markdown
  metadata: { tokens_used: number, row_count: number }
}

// Estado interno del componente:
interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
  data?: Record<string, unknown>[]
  queryType?: string
  timestamp: Date
}
```

### 2.4 APIs y Endpoints Consumidos
| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/analytical/queries` | GET | Obtener lista de consultas disponibles para Quick Actions |
| `/analytical/ask` | POST | Enviar pregunta en NL y obtener respuesta analítica |

### 2.5 Coherencia con Estado-Fase
El paso 4.4 es coerente con:
- Contrato de API `POST /analytical/ask` definido en estado-fase (sección 3).
- Allowlist analítico de `analytical_queries.py` (5 queries pre-aprobadas).
- Rate limiting de 10 req/min por organización (ya implementado en backend).
- Aislamiento multi-tenant vía `org_id` inyectado en middleware.

---

## 3. Decisiones

### 3.1 Decisión: UI como Sheet (Drawer) en lugar de Modal/Página
**Justificación:** Un Sheet lateral permite mantener el contexto de la página actual mientras se interactúa con el asistente. Es menos intrusivo que un modal y más accesible que navegar a una página dedicada. El usuario puede cerrar el sheet y seguir trabajando en su vista actual.

### 3.2 Decisión: Integración Global via Layout
**Justificación:** El chat analítico debe estar disponible desde cualquier vista del dashboard (tasks, flows, agents, etc.), no solo desde una página específica. Por eso se instancia en el layout global `(app)/layout.tsx`.

### 3.3 Decisión: Fallback por Keywords en Backend
**Justificación:** El paso 4.3 ya implementó el fallback por keywords para garantizar una respuesta (aunque simplificada) ante fallos de conectividad con el LLM. El frontend no necesita lógica adicional de retry; el backend ya hace el trabajo.

---

## 4. Criterios de Aceptación

- [ ] El botón flotante (FAB) con icono de cerebro aparece en la esquina inferior derecha del dashboard.
- [ ] Al hacer clic en el botón, se abre un Sheet desde el lado derecho.
- [ ] En estado vacío, se muestran las consultas rápidas obtenidas de `/analytical/queries`.
- [ ] El usuario puede escribir una pregunta y enviarla; se muestra un spinner de carga.
- [ ] La respuesta del asistente se renderiza con: badge de query_type, texto del summary, tabla de datos (si existen), y timestamp.
- [ ] Si la respuesta tiene datos, se muestra una tabla con máximo 5 filas + indicador de más filas.
- [ ] Los errores del backend (429, 400, 500) se muestran como mensajes de error dentro del chat.
- [ ] El componente está integrado en `dashboard/app/(app)/layout.tsx` y es accesible desde cualquier página.
- [ ] El componente usa el `org_id` automáticamente (injectado por el interceptor de API).

---

## 5. Riesgos

### 5.1 Riesgo: El componente no está integrado en el layout
**Severidad:** Alta. El componente existe pero no es visible para el usuario.
**Mitigación:** Agregar `<AnalyticalAssistantChat />` al final del children en `dashboard/app/(app)/layout.tsx`.

### 5.2 Riesgo: Rate limiting no friendly
**Severidad:** Media. El usuario puede alcanzar el límite de 10 req/min rápidamente si hace pruebas.
**Mitigación:** El mensaje de error 429 es amigable ("Esperá un momento"). Considerar mostrar un contador de requests restantes en una versión futura.

### 5.3 Riesgo: Datos vacíos confunden al usuario
**Severidad:** Baja. Si el backend devuelve `data: []` pero con `summary` informativo, puede parecer que no pasó nada.
**Mitigación:** El componente ya muestra el `summary` siempre. El DataPreview solo se renderiza si `data.length > 0`.

---

## 6. Plan

### Tareas Atómicas (Orden Recomendado)

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Integrar `AnalyticalAssistantChat` en `dashboard/app/(app)/layout.tsx` | Baja | Ninguna (el componente ya existe) |
| 2 | Verificar que las llamadas a `/analytical/queries` y `/analytical/ask` funcionan correctamente desde el frontend (test manual) | Baja | Task 1 |
| 3 | Probar escenario de rate limiting (enviar más de 10 requests en 1 minuto) | Media | Task 2 |
| 4 | Probar consulta rápida (click en una de las opciones) | Baja | Task 2 |
| 5 | Validar renderizado de tabla con datos reales (si hay datos en la DB) | Baja | Task 2 |

### Estimación Total
Las tareas son mayormente de complejidad baja. La integración completa del paso 4.4 debería tomar entre 1-2 horas incluyendo testing manual.

---

## 🔮 Roadmap (NO implementar ahora)

1. **Historial persistente:** Guardar los mensajes del chat en localStorage para que persistan entre sesiones.
2. **Suggest chips:** Mostrar sugerencias de preguntas basadas en el historial de la organización.
3. **Exportación:** Permitir exportar la respuesta (summary + datos) como CSV o PDF.
4. **UI de feedback:** Agregar botones de "👍 / 👎" para que el usuario califique la respuesta del asistente.
5. **Voice input:** Agregar input por voz para preguntas en mobile.
6. **Indicador de rate limit remaining:** Mostrar cuántos requests quedan en el minuto actual.