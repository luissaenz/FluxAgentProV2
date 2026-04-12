# 📋 ANÁLISIS TÉCNICO — Paso 1.4 [Frontend]: Refinamiento UI en Lista de Tickets

**Agente:** oc  
**Fecha:** 2026-04-11  
**Paso:** 1.4 (Fase 1 - Hardening de Tickets)

---

## 1. Diseño Funcional

### 1.1 Happy Path Detallado

El usuario está en la lista de tickets y hace clic en el botón de ejecución de un ticket específico:

1. El usuario hace clic en el botón ▶ (Play) de una fila de ticket
2. El botón inmediatamente muestra un spinner animado (`animate-spin`) durante la ejecución
3. La fila adquiere un fondo de carga (`animate-pulse`) para indicar procesamiento activo
4. El hook `useExecuteTicket` muestra un toast de carga: "Ejecutando ticket \"{title}\"..."
5. El backend procesa la ejecución y retorna el ticket actualizado con el nuevo `task_id` y estado
6. Al recibir respuesta exitosa:
   - Se dismiss del toast de carga
   - Se muestra toast de éxito: "Ticket ejecutado correctamente (Task: {short_id})"
   - Se invalidan las queries `['tickets']` y `['ticket', ticketId]`
   - La tabla automáticamente refresca los datos
7. Si falla:
   - Se dismiss del toast de carga
   - Se muestra toast de error con mensaje específico (incluyendo detección de errores de red)

### 1.2 Edge Cases Relevantes para MVP

| Escenario | Comportamiento |
|-----------|-----------------|
| Ejecutar ticket sin `flow_type` | El botón de ejecución está deshabilitado (línea 120: `!!ticket.flow_type`) |
| Ejecutar ticket en estado `in_progress`, `done` o `cancelled` | Botón deshabilitado (líneas 117-119) |
| Error de red durante ejecución | Toast específico: "Error de conexión. Verifique su conexión e intente nuevamente." |
| Error de API (500, etc.) | Toast muestra mensaje de error del servidor |
| Timeout de red | Caught por el mismo manejo de error de red |

### 1.3 Manejo de Errores

- **Errores de red:** Se detectan explícitamente en `useTickets.ts:92-96` revisando `error.name === 'TypeError'` y mensajes que contienen "Failed to fetch", "NetworkError", "ENOTFOUND".
- **Errores de API:** Se muestra el mensaje del error devuelto por el backend.
- **Errores inesperados:** Mensaje genérico "Ocurrió un error inesperado..." con fallback al mensaje del error.

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Rol | Archivo |
|------------|-----|---------|
| `TicketsPage` | Página principal con DataTable | `dashboard/app/(app)/tickets/page.tsx` |
| `useExecuteTicket` | Hook de mutación con feedback | `dashboard/hooks/useTickets.ts` |
| `DataTable` | Componente genérico de tabla | `dashboard/components/data-table/index.tsx` |
| `StatusLabel` | Badge de estado | `dashboard/components/shared/StatusLabel.tsx` |

### 2.2 Interfaz del Hook `useExecuteTicket`

```typescript
interface UseExecuteTicket {
  mutate: (variables: { ticketId: string; ticketTitle?: string }) => void
  mutateAsync: (variables: { ticketId: string; ticketTitle?: string }) => Promise<any>
  isPending: boolean
  variables?: { ticketId: string; ticketTitle?: string }
}
```

### 2.3 Estados de la UI

- **Sin ejecutar:** Botón con icono Play, color muted
- **Ejecutando:** Spinner animado + `animate-pulse` en la fila + botón deshabilitado
- **Post-ejecución:** Refresco automático vía invalidación de queries

### 2.4 Modelo de Datos (Del backend, referenciado)

El ticket actualizado retorna:
```typescript
interface Ticket {
  id: string
  org_id: string
  title: string
  description: string
  flow_type: string
  priority: string
  status: 'backlog' | 'todo' | 'in_progress' | 'done' | 'blocked' | 'cancelled'
  task_id: string | null
  notes: string | null
}
```

---

## 3. Decisiones

### Decisión 1: Spinners por fila en lugar de spinner global

**Justificación:** Mantiene el contexto visual. El usuario sabe exactamente qué ticket se está ejecutando sin perder la vista de la lista completa.

### Decisión 2: Invalidación de queries vs polling

**Justificación:** `refetchInterval: 10_000` en `useTickets` (línea 23 de `useTickets.ts`) combinado con invalidación explícita garantiza datos frescos con overhead mínimo.

### Decisión 3: Detección de errores de red explícita

**Justificación:** Evita la confusión de mostrar "mensajes de error de API" cuando el problema real es de conectividad. El usuario puede actuar diferente según el tipo de error.

---

## 4. Criterios de Aceptación

- [x] El botón de ejecución muestra spinner durante la ejecución
- [x] La fila del ticket muestra `animate-pulse` durante la ejecución
- [x] El usuario ve un toast de carga con el título del ticket
- [x] Al completar, se muestra toast de éxito con el task_id
- [x] Al fallar, se muestra toast de error con mensaje descriptivo
- [x] Los errores de red muestran un mensaje diferente a los errores de API
- [x] La tabla refresca automáticamente tras ejecución exitosa
- [x] Los tickets en estados `in_progress`, `done`, `cancelled` tienen el botón deshabilitado
- [x] Los tickets sin `flow_type` tienen el botón deshabilitado

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| La invalidación de queries puede no ser instantánea | `refetchInterval` de 10s como backup |
| El usuario puede re-ejecutar el mismo ticket rapidamente | El botón se deshabilita durante `isPending` |
| El toast de carga puede ser dismissible accidentalmente | No se implementa dismiss manual (por defecto Sonner no permite dismiss de toasts de carga) |

---

## 6. Plan

### Tareas Atomicadas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Revisar implementación de spinners por fila en `tickets/page.tsx` | Baja | Ninguna |
| 2 | Verificar integración de `animate-pulse` | Baja | Ninguna |
| 3 | Validar `useExecuteTicket` con toasts | Baja | Ninguna |
| 4 | Confirmar invalidación de queries post-ejecución | Baja | Ninguna |
| 5 | Test E2E: ejecutar un ticket y verificar refresco | Media | Requires backend corriendo |

**Estado:** ✅ COMPLETADO — Las tareas están implementadas en los archivos actuales.

---

## 🔮 Roadmap (NO implementado en MVP)

1. **Loading skeleton más elaborado:** Reemplazar `animate-pulse` por skeleton con forma de ticket durante carga
2. **Streaming de estado:** Mostrar el estado del task en tiempo real (pending → running → completed)
3. **Cancelar ejecución:** Botón para cancelar un task en curso
4. **Batch execution:** Seleccionar múltiples tickets y ejecutar en paralelo
5. **Toast persistente hasta completado:** Mantener toast visible hasta que el task finalice (no solo hasta que la API responda)