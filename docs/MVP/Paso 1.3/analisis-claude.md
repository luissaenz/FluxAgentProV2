# ANÁLISIS — Paso 1.3: Potenciar hook `useExecuteTicket` con Toasts
**Agente:** claude
**Fecha:** 2026-04-11

---

## 1. Resumen

El paso 1.3 requiere integrar notificaciones toast en el hook `useExecuteTicket` de `dashboard/hooks/useTickets.ts`, para informar al usuario sobre el resultado de la ejecución de un ticket (éxito o error).

**Contexto:** El hook actual solo invalida queries en `onSuccess`, sin feedback visual al usuario. El sistema ya tiene `sonner` configurado (`dashboard/components/ui/sonner.tsx`) y el `Toaster` está registrado en `dashboard/app/providers.tsx`.

---

## 2. Diseño Funcional

### Happy Path

1. Usuario hace clic en el botón Play de un ticket.
2. `executeTicket.mutate(ticket.id)` se dispara.
3. Durante ejecución, el botón muestra estado `isPending`.
4. **Si éxito:** Toast de tipo `success` con mensaje "Ticket ejecutado correctamente".
5. **Si error:** Toast de tipo `error` con mensaje del error devuelto por el endpoint.

### Edge Cases

- **Error de red:** El toast debe mostrar un mensaje genérico ("Error de conexión") ya que el `onError` de react-query recibe el error de red.
- **Error de servidor (500):** El endpoint retorna JSON con `detail`. Mostrar ese texto en el toast.
- **Ticket no encontrado (404):** Toast de error con mensaje del endpoint.
- **Ticket ya en ejecución (409):** Toast de warning con mensaje "Ticket ya está en ejecución".
- **Sin conexión a la API:** Toast de error antes de llegar al endpoint.

### Manejo de Errores

| Escenario | Mensaje del Toast |
|---|---|
| Éxito | "Ticket ejecutado correctamente" |
| Error 404 | "Ticket no encontrado" |
| Error 409 | "El ticket ya está en ejecución" |
| Error 500 (infraestructura) | "Error interno del servidor" |
| Error de red | "Error de conexión. Intenta de nuevo." |

---

## 3. Diseño Técnico

### Componentes existentes

- **`sonner`** instalado como dependencia (`sonner@^1.7.0` o equivalente).
- **`Toaster`** configurado en `providers.tsx:26` con `richColors position="top-right"`.
- **`api.post`** en `dashboard/lib/api.ts` lanza errores HTTP como excepciones.

### Modificación: `dashboard/hooks/useTickets.ts`

Se extiende `useExecuteTicket` con callbacks `onError` y `onSettled` que invocan `toast()` de `sonner`:

```typescript
// En useExecuteTicket()
onSuccess: () => {
  toast.success("Ticket ejecutado correctamente")
  queryClient.invalidateQueries({ queryKey: ['tickets'] })
  queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
},
onError: (error: Error) => {
  // Extraer mensaje del error HTTP o fallback genérico
  const message = isAxiosError(error) ? error.response?.data?.detail : error.message
  toast.error(message || "Error al ejecutar el ticket")
},
onSettled: () => {
  // Cleanup si fuera necesario
}
```

### Alternativa: hook dedicado `useExecuteTicketWithToast`

Para no alterar el comportamiento base de `useExecuteTicket` (que podría ser reutilizado en otros contextos sin toast), se crea un wrapper:

```typescript
export function useExecuteTicketWithToast(orgId: string) {
  const base = useExecuteTicket()
  return {
    ...base,
    mutate: (ticketId: string) => {
      toast.promise(
        base.mutateAsync(ticketId),
        {
          loading: "Ejecutando ticket...",
          success: "Ticket ejecutado correctamente",
          error: (err) => err?.response?.data?.detail || "Error al ejecutar",
        }
      )
    }
  }
}
```

**Decisión:** Se adopta la alternativa de wrapper `useExecuteTicketWithToast` para preservar la composibilidad del hook base y permitir uso sin toast donde sea necesario.

### API de respuesta de `/execute`

El endpoint `POST /tickets/{id}/execute` retorna:
- **200 OK:** `{ ticket_id, task_id, status: "done" | "blocked", error?: string }`
- **4xx/5xx:** Lanza `HTTPException` que `api.post` convierte en error.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable mediante |
|---|----------|---------------------|
| 1 | Al ejecutar un ticket exitosamente, se muestra toast de éxito con mensaje "Ticket ejecutado correctamente" | Test visual/manual |
| 2 | Al fallar la ejecución, se muestra toast de error con el mensaje del servidor | Test visual/manual |
| 3 | El botón Play permanece deshabilitado durante la ejecución (`isPending`) | Test visual/manual |
| 4 | Los toasts usan `richColors` (colores significativos) según configuración del Toaster | Test visual |
| 5 | Toast de error de red muestra mensaje legible (no stack trace) | Test manual desconectando red |
| 6 | El hook base `useExecuteTicket` no se rompe (sigue invalidando queries) | Tests existentes de queries |

---

## 5. Decisiones

- **D1:** Se crea `useExecuteTicketWithToast` como wrapper del hook base, en lugar de modificar directamente `useExecuteTicket`. Esto mantiene la composibilidad — otros puntos que usen el hook base no получит toasts no deseados.
- **D2:** Se usa la API `toast.promise()` de sonner para mostrar estados loading/success/error automáticamente, en lugar de manejar `isPending` manualmente.
- **D3:** Se muestra el `detail` del error HTTP en el toast de error, extrayéndolo de `error.response?.data?.detail` para errores 4xx/5xx del backend.

---

## 6. Plan de Implementación

### Tarea 1: Crear wrapper `useExecuteTicketWithToast`
- **Archivo:** `dashboard/hooks/useTickets.ts`
- **Complejidad:** Baja
- **Dependencias:** Ninguna (usa `useExecuteTicket` existente)
- **Agregar import:** `import { toast } from 'sonner'`

### Tarea 2: Actualizar `tickets/page.tsx` para usar el wrapper
- **Archivo:** `dashboard/app/(app)/tickets/page.tsx`
- **Cambio:** `const executeTicket = useExecuteTicket()` → `const executeTicket = useExecuteTicketWithToast(orgId)`
- **Complejidad:** Baja

---

## 7. Riesgos

- **R1:** Si `sonner` no está instalado, el build fallará. **Mitigación:** Verificar `package.json` antes de implementar. Si no está, agregar con `npm install sonner`.
- **R2:** El `toast.promise` requiere que `mutateAsync` retorne una Promise. El `mutationFn` de `useExecuteTicket` ya retorna el resultado de `api.post()`, que es una Promise. ✅

---

## 8. Consideraciones Futuras

- Los toasts pueden personalizarse por tipo de flow (ej: "Flow de análisis ejecutado" vs "Ticket de facturación procesado").
- Se podría agregar un historial de toasts en el dashboard para revisión posterior.
- El hook `useExecuteTicketWithToast` podría moverse a un archivo separado si crece en complejidad.