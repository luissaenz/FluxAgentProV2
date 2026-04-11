# Análisis Técnico — Paso 1.3: Potenciar hook `useExecuteTicket` con Notificaciones

## 1. Diseño Funcional

### Happy Path
1. El usuario hace clic en el botón "Ejecutar" (icono Play) en la lista de tickets o en el detalle.
2. Se dispara la mutación `useExecuteTicket.mutate(ticketId)`.
3. **Inmediatamente** aparece un toast de carga: "Ejecutando ticket {title}...".
4. La API responde exitosamente con `{ task_id: "...", status: "in_progress" }`.
5. Se invalidan las queries de tickets (ya ocurre actualmente).
6. Se muestra un toast de éxito: "Ticket ejecutado correctamente. Task ID: {task_id.slice(0,8)}..." con un enlace opcional a la tarea.
7. El toast desaparece automáticamente tras 5 segundos o el usuario lo cierra.

### Edge Cases (MVP)
- **Error de API (4xx/5xx):** La API retorna `{ detail: "mensaje de error" }`. Se debe mostrar un toast de error con el mensaje exacto. El usuario puede cerrar el toast y reintentar.
- **Error de red (timeout, offline):** Se muestra un toast genérico: "Error de conexión. Intente nuevamente."
- **Doble clic accidental:** El botón ya está deshabilitado mientras `isPending === true` (implementado actualmente), pero el toast de carga solo debe mostrarse una vez por intento.
- **Ticket ya en ejecución:** La API puede retornar un error indicando que ya hay una tarea vinculada. El toast debe comunicar: "Este ticket ya tiene una tarea en ejecución."

### Manejo de Errores — Qué ve el usuario
| Escenario | Toast | Acción disponible |
|-----------|-------|-------------------|
| Éxito | Verde: "Ticket ejecutado. Task: abc123..." | Clic en el ID para ir a `/tasks/{task_id}` |
| Error de negocio (API 4xx) | Rojo: Mensaje específico del backend | Reintentar desde el botón |
| Error de servidor (API 5xx) | Rojo: "Error interno del servidor. Intente más tarde." | Reintentar desde el botón |
| Error de red | Rojo: "Error de conexión. Verifique su conexión." | Reintentar desde el botón |

---

## 2. Diseño Técnico

### Componentes Involucrados
No se crean componentes nuevos. Se modifica exclusivamente:
- **`dashboard/hooks/useTickets.ts`** — hook `useExecuteTicket`

### Dependencias Requeridas
- **`sonner`** — ya instalada en `package.json` (v2.0.7) y configurada en `providers.tsx` via `<Toaster />`.
- **`@/lib/api`** — ya importado y usado para las llamadas HTTP.

### Modificación del Hook `useExecuteTicket`

**Antes:**
```ts
export function useExecuteTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ticketId: string) => api.post(`/tickets/${ticketId}/execute`),
    onSuccess: (_data, ticketId) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}
```

**Después (diseño conceptual):**
- Se añade import de `toast` desde `sonner`.
- Se necesita el `title` del ticket para el toast de carga. **Problema:** `mutationFn` solo recibe `ticketId`, no el título.
- **Solución:** Cambiar la firma para recibir un objeto `{ ticketId, ticketTitle? }` en lugar de solo `ticketId`. El título es opcional para no romper los call sites existentes.
- `onMutate`: muestra toast de carga con `toast.loading()`.
- `onSuccess`: dismiss del toast de carga + `toast.success()` con enlace a la task.
- `onError`: dismiss del toast de carga + `toast.error()` con el mensaje extraído del error.

### Interface de Entrada del Hook
```ts
type ExecuteTicketParams = {
  ticketId: string
  ticketTitle?: string  // Opcional para retrocompatibilidad
}
```

### Toast Messages (textos en español, coherente con la UI)
- **Carga:** `"Ejecutando ticket..."` (sin título si no está disponible)
- **Éxito:** `"Ticket ejecutado correctamente. Task: {task_id_short}"`
- **Error de negocio:** `error.detail` extraído de la respuesta JSON de la API.
- **Error genérico:** `"Error al ejecutar el ticket. Intente nuevamente."`

### Call Sites a Actualizar
1. **`dashboard/app/(app)/tickets/page.tsx` (línea ~110):**
   - Actualmente: `executeTicket.mutate(ticket.id)`
   - Debe pasar: `executeTicket.mutate({ ticketId: ticket.id, ticketTitle: ticket.title })`
   - La variable `ticket` ya está disponible en el scope de la columna `actions`.

2. **`dashboard/app/(app)/tickets/[id]/page.tsx` (línea ~67):**
   - Actualmente: `executeTicket.mutate(ticket!.id)`
   - Debe pasar: `executeTicket.mutate({ ticketId: ticket!.id, ticketTitle: ticket!.title })`
   - La variable `ticket` ya está disponible en el scope del componente.

---

## 3. Decisiones

| Decisión | Justificación |
|----------|---------------|
| Usar `sonner` (ya instalado) en vez de `@radix-ui/react-toast` directamente | `sonner` ya está configurado en `providers.tsx` con `<Toaster richColors />`, ofrece una API imperativa simple (`toast.success`, `toast.error`, `toast.loading`) y es la librería de facto en el stack shadcn/ui. Evita añadir un segundo proveedor de toasts. |
| Hacer `ticketTitle` opcional en los parámetros del hook | Permite migrar los call sites de forma incremental. Si algún sitio llama con solo `ticketId` (string), TypeScript forzará el cambio, pero el diseño acepta ambos patrones durante la transición. |
| No agregar toast de "cancelado" | El hook no expone `onCancel` porque React Query v5 no lo dispara de forma fiable para mutaciones. No es necesario para MVP. |
| Extraer el mensaje de error de `error.detail` o `error.message` | La API FastAPI retorna errores en el campo `detail` (convención de Pydantic). El cliente `api` ya lanza `Error` con ese mensaje. Se intenta parsear si el error es un objeto JSON de la respuesta HTTP. |

---

## 4. Criterios de Aceptación

- [ ] Al ejecutar un ticket exitosamente, aparece un toast verde con el mensaje "Ticket ejecutado correctamente" y los primeros 8 caracteres del `task_id`.
- [ ] Al fallar la ejecución (error de API), aparece un toast rojo con el mensaje de error exacto retornado por el backend.
- [ ] Al fallar la conexión (network error), aparece un toast rojo con un mensaje genérico de error de conexión.
- [ ] Durante la ejecución, aparece un toast de carga (spinner) que desaparece al recibir la respuesta.
- [ ] El botón de ejecutar permanece deshabilitado durante la ejecución (comportamiento existente, debe preservarse).
- [ ] Las queries de tickets se invalidan tras éxito o error (comportamiento existente, debe preservarse).
- [ ] Los dos call sites (lista y detalle) se actualizan para pasar `ticketTitle` sin errores de TypeScript.
- [ ] El build de Next.js (`npm run build`) compila sin errores de TypeScript.

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| El hook `api.post` lanza un `Error` con un mensaje sin estructurar (string plano) en vez de un objeto con `detail` | Media | Medio | En `onError`, verificar si `error` es instancia de `Error` y usar `error.message`. Si es un objeto, extraer `error.detail`. |
| Los toasts se acumulan si el usuario hace clic rápidamente en múltiples tickets | Baja | Bajo | El botón ya se deshabilita con `isPending`. Si el usuario cambia de página y ejecuta otro, cada toast es independiente (comportamiento esperado de sonner). |
| `sonner` no está correctamente importado o el `Toaster` no está montado en algún layout anidado | Baja | Alto | Verificar que el componente `Toaster` en `providers.tsx` envuelve toda la app. Ya está confirmado en el código actual. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Modificar `useExecuteTicket` en `useTickets.ts`: importar `toast`, cambiar firma a `{ ticketId, ticketTitle? }`, añadir `onMutate`, `onSuccess`, `onError` con lógica de toasts | Baja | Ninguna |
| 2 | Actualizar call site en `tickets/page.tsx` (columna actions) para pasar objeto con `ticketId` y `ticketTitle` | Baja | Tarea 1 |
| 3 | Actualizar call site en `tickets/[id]/page.tsx` para pasar objeto con `ticketId` y `ticketTitle` | Baja | Tarea 1 |
| 4 | Ejecutar `npm run build` en `dashboard/` y verificar cero errores de TypeScript | Baja | Tareas 2, 3 |
| 5 | Prueba manual: crear ticket → ejecutar desde lista → verificar toast de éxito → verificar toast de error (inyectar error temporal en API o desconectar red) | Baja | Tarea 4 |

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 (secuencial).

---

## 🔮 Roadmap (NO implementar ahora)

- **Toast con enlace clicable a la task:** Sonner soporta contenido JSX personalizado. Se podría renderizar un toast de éxito con un `<Link>` directo a `/tasks/{task_id}` en vez de solo el texto plano.
- **Polling automático post-ejecución:** Tras ejecutar con éxito, iniciar un polling de 30s para refrescar el estado del ticket hasta que cambie a `in_progress` o `done`.
- **Sonido de notificación:** Emitir un sonido sutil cuando un ticket de larga ejecución termina (requiere permiso de audio del navegador).
- **Toast de "ticket ya en ejecución" como warning (amarillo):** Diferenciar visualmente los errores de negocio (409 Conflict) de los errores de servidor (500).
- **Agrupación de toasts:** Si el usuario ejecuta múltiples tickets en ráfaga, agrupar los toasts de éxito en uno solo: "3 tickets ejecutados correctamente".
