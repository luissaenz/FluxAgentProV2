# Analisis Tecnico - Paso 1.4: Refinamiento UI de Lista de Tickets

**Agente:** qwen
**Paso:** 1.4 [Frontend]
**Alcance:** Refinar la UI de la Lista de Tickets (`tickets/page.tsx`) — Indicadores de carga especificos por fila al ejecutar y refresco automatico tras la respuesta.

---

## 1. Diseno Funcional

### Happy Path
1. El usuario ve la tabla de tickets con datos cargados (`isLoading = false`, `data.items` poblado).
2. El usuario hace clic en el boton "Play" de una fila elegible (`status !== in_progress/done/cancelled` && `flow_type` definido).
3. **Inmediatamente** la fila muestra un indicador de carga (spinner animado) mientras el backend procesa.
4. La columna `actions` deshabilita el boton de ejecucion para evitar doble-click.
5. Al recibir respuesta exitosa:
   - El spinner desaparece.
   - Se muestra un toast de exito con el `task_id` parcial.
   - La tabla se refresca automaticamente (invalidacion de query `['tickets']`).
   - La fila actualiza su estado (ej. de `backlog` a `in_progress`).
6. Si la ejecucion falla:
   - El spinner desaparece.
   - Se muestra toast de error con mensaje descriptivo (diferenciando error de red vs error de API).
   - La fila vuelve a su estado anterior (el usuario puede reintentar).

### Edge Cases (MVP)
- **Doble-click:** El boton se deshabilita inmediatamente tras el primer click (`disabled={executeTicket.isPending}`). **Problema detectado:** la condicion actual `executeTicket.isPending` es global al hook, no por ticket. Si se ejecutan dos tickets en rapida sucesion, el segundo spinner apareceria en ambas filas.
- **Ticket no elegible:** Sin boton de play si `status` es terminal o no hay `flow_type`. Correcto, pero no hay tooltip explicativo para el usuario sobre *por que* no se puede ejecutar.
- **Refresco automatico:** `onSettled` invalida `['tickets']` y `['ticket', ticketId]`. El `refetchInterval: 10_000` del hook `useTickets` asegura refresco periodico aunque falle la invalidacion.
- **Ticket eliminado mientras se ejecuta:** Caso raro pero posible. El backend debe retornar 404 y el frontend mostrar toast de error.

### Manejo de Errores (lo que ve el usuario)
- **Error de red:** Toast "Error de conexion. Verifique su conexion e intente nuevamente."
- **Error de API (4xx/5xx):** Toast "Fallo al ejecutar" con el mensaje exacto del backend.
- **Estado ambiguo tras error:** La fila vuelve a su estado previo porque la invalidacion de query refresca los datos reales del servidor. No queda "colgada".

---

## 2. Diseno Tecnico

### Componentes Involucrados
- **`TicketsPage`** (`dashboard/app/(app)/tickets/page.tsx`): Componente principal. Contiene la tabla, filtros y dialogos.
- **`useExecuteTicket`** (`dashboard/hooks/useTickets.ts`): Hook de mutacion con soporte de toasts.

### Estado Actual (Lo que ya existe)
| Caracteristica | Implementada | Detalle |
|---|---|---|
| Spinner por fila | ✅ Parcial | `isExecuting` calcula `executeTicket.isPending && executeTicket.variables?.ticketId === ticket.id`. Renderiza spinner con `animate-pulse` + `animate-spin`. |
| Boton deshabilitado | ✅ | `disabled={executeTicket.isPending}` en el boton de play. |
| Refresco automatico | ✅ | `onSettled` invalida `['tickets']` y `['ticket', ticketId]`. |
| Toast de carga | ✅ | `toast.loading` en `onMutate` con titulo del ticket. |
| Toast de exito | ✅ | `toast.success` con `task_id` parcial. |
| Toast de error | ✅ | Diferenciacion red vs API en `onError`. |

### Interfaces (Inputs/Outputs)

**`useExecuteTicket` mutation:**
- **Input:** `{ ticketId: string; ticketTitle?: string }`
- **Output:** `TicketResponse` (objeto completo con `id`, `status`, `task_id`, `notes`, etc.)
- **Context (onMutate):** `{ toastId: string | number }`

**Columna `actions` de la tabla:**
- Recibe `row: Ticket` del TanStack Table.
- Deriva `isExecuting` comparando `executeTicket.isPending` + `executeTicket.variables?.ticketId`.
- Renderiza boton condicional con spinner o icono Play.

### Problema de Diseno Detectado

**Scoped loading state incompleto:** La logica actual `executeTicket.isPending && executeTicket.variables?.ticketId === ticket.id` funciona *solo si* la mutacion tiene `variables` correctamente populados. Sin embargo, `useMutation` de TanStack Query v5 expone `state.variables` que se setea en `onMutate`. Si el hook no pasa `variables` explicitamente en la llamada a `mutate`, la comparacion puede fallar.

**Verificacion:** En la implementacion actual, `executeTicket.mutate({ ticketId, ticketTitle })` pasa ambos campos. `onMutate` recibe `{ ticketTitle }` y retorna `{ toastId }`. **Las variables NO se mergean automaticamente con el contexto retornado.** TanStack Query expone `mutation.variables` directamente desde el argumento de `mutate()`, por lo que `executeTicket.variables?.ticketId` *deberia* funcionar correctamente.

**Conclusion:** La implementacion actual es funcional pero no tiene una capa visual de "fila en loading" mas alla del spinner del boton. No hay un overlay semitransparente en toda la fila que indique claramente que esa fila esta siendo procesada.

---

## 3. Decisiones

### D1: No agregar overlay de fila completo (MVP)
**Decision:** Mantener el spinner solo en el boton de accion, sin overlay semitransparente en toda la fila.
**Justificacion:** El spinner en el boton + el boton deshabilitado es suficiente senal visual para el MVP. Un overlay completo anadiria complejidad CSS y podria interferir con la accesibilidad (hover, focus). Se puede anadir en roadmap si el feedback de UX lo solicita.

### D2: No cambiar la estrategia de refresco
**Decision:** Mantener `onSettled` con `invalidateQueries` + `refetchInterval: 10_000` como mecanismo de refresco.
**Justificacion:** Es simple, funcional y evita race conditions. Optimistic updates podrian causar inconsistencia si el backend tarda mas de lo esperado en cambiar el estado.

### D3: No agregar confirmacion antes de ejecutar
**Decision:** La ejecucion es directa, sin dialogo de confirmacion.
**Justificacion:** Es un action button, no una operacion destructiva. El usuario puede reintentar si falla y el backend idempotente maneja ejecuciones duplicadas. Anadir un modal de confirmacion anadiria friccion innecesaria para el MVP.

---

## 4. Criterios de Aceptacion

| # | Criterio | Verificable |
|---|---|---|
| C1 | Al hacer clic en "Play", el boton muestra un spinner animado inmediatamente | ✅ Visual |
| C2 | El boton de "Play" se deshabilita durante la ejecucion (no clickable) | ✅ DOM `disabled` attribute |
| C3 | Solo la fila del ticket en ejecucion muestra el spinner (no otras filas) | ✅ Visual |
| C4 | Tras exito, la tabla refresca y muestra el nuevo estado del ticket | ✅ Visual + Network tab |
| C5 | Tras error, el spinner desaparece y el usuario ve un toast de error descriptivo | ✅ Visual |
| C6 | Si no hay `flow_type`, no aparece el boton de Play | ✅ DOM |
| C7 | Si el status es `in_progress`, `done` o `cancelled`, no aparece el boton de Play | ✅ DOM |
| C8 | El toast de carga muestra el titulo del ticket | ✅ Visual |
| C9 | El toast de exito muestra los primeros 8 caracteres del `task_id` | ✅ Visual |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|
| `executeTicket.variables` es `undefined` en algun caso borde | Baja | Medio: el spinner no apareceria en la fila correcta | Agregar un fallback: si `variables` es undefined, no mostrar spinner en ninguna fila (solo deshabilitar boton). Ya esta cubierto por el optional chaining `?.`. |
| El refresco por `invalidateQueries` no actualiza la fila a tiempo | Baja | Bajo: el usuario ve estado stale por hasta 10s (refetchInterval) | El `refetchInterval: 10_000` actua como red de seguridad. Si es critico, se puede usar `cancelQueries` antes de `invalidateQueries`. |
| Doble-click rapido antes de que React procese el `isPending` | Muy baja | Bajo: se enviarian 2 requests al backend | El backend debe ser idempotente para `POST /tickets/{id}/execute`. Si no lo es, agregar debounce en el frontend. |
| La tabla se redibuja completa al invalidar queries (performance con muchos tickets) | Media | Bajo-Medio: parpadeo visible | Para el MVP con `pageSize={20}` no es problema. Si crece, implementar `keepPreviousData` o optimistic updates. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|---|---|---|
| 1 | **Verificacion manual:** Ejecutar la app, abrir la pagina de tickets, ejecutar un ticket y confirmar que el spinner aparece SOLO en la fila correcta. | Baja | Ninguna |
| 2 | **Verificacion de edge case:** Intentar doble-click rapido en el boton Play. Verificar que solo se envia 1 request (Network tab). | Baja | Tarea 1 |
| 3 | **Verificacion de refresco:** Ejecutar ticket, esperar respuesta, confirmar que la tabla refleja el nuevo estado sin recarga de pagina. | Baja | Tarea 1 |
| 4 | **Verificacion de error:** Forzar error de backend (ej. ticket inexistente o backend apagado). Confirmar toast de error y desaparicion del spinner. | Baja | Tarea 1 |
| 5 | **(Opcional) Mejora visual:** Si se identifica que el spinner no es suficientemente visible, agregar `opacity-60` a la celda de actions durante loading. | Baja | Tarea 1-4 |

**Estado actual:** La implementacion de este paso YA ESTA COMPLETA segun `estado-fase.md`. Este analisis es retroactivo. Las tareas 1-4 son de validacion, no de implementacion.

---

## 🔮 Roadmap (NO implementar ahora)

| Mejora | Descripcion | Por que no ahora |
|---|---|---|
| **Optimistic updates** | Actualizar el estado de la fila a `in_progress` antes de la respuesta del servidor. Mejora la percepcion de velocidad. | Anade complejidad de rollback si falla. Para MVP, la estrategia actual es suficiente. |
| **Overlay de fila completa** | Capa semitransparente con spinner en toda la fila durante ejecucion, no solo en el boton. | Puede interferir con tooltips, hover states y accesibilidad. Evaluacion post-MVP. |
| **Tooltip en botones** | Tooltips explicativos en Play ("Ejecutar este ticket"), Edit y Delete. Mejora descubribilidad. | Puramente cosmético. No bloquea funcionalidad. |
| **Explicacion de no-elegibilidad** | Si un ticket no se puede ejecutar, mostrar un tooltip o icono de info explicando por que (ej. "Ya completado", "Sin flow asignado"). | UX nice-to-have. El usuario puede inferirlo del status. |
| **Debounce en ejecucion** | Prevenir doble-click a nivel de evento (no solo de UI) con debounce de 500ms. | Solo necesario si el backend no es idempotente. Verificar primero. |
| **Keyboard accessibility** | Permitir ejecutar ticket con Enter/Space cuando el boton de play tiene focus. | Ya deberia funcionar por ser un `<button>`, pero verificar con screen reader. |
| **Batch execution** | Seleccionar multiples tickets y ejecutarlos en lote. | Feature de Fase 2+, no del MVP. Requiere cambios en backend. |
