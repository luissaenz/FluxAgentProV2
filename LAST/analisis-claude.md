# 🧠 ANÁLISIS TÉCNICO: PASO 1.4 - REFINAMIENTO UI LISTA DE TICKETS

## 1. Diseño Funcional

- **Interacción de Ejecución**: Al hacer clic en el botón "Play" de un ticket, el sistema proporciona feedback visual inmediato y persistente durante todo el ciclo de vida de la ejecución.
- **Happy Path**:
    1. Usuario presiona ejecutar en una fila específica.
    2. El botón `Play` se transforma en un spinner circular con `border-2 border-primary border-t-transparent`.
    3. El botón adquiere clase `animate-pulse text-primary` para indicar procesamiento activo.
    4. Las acciones de edición/eliminación permanecen activas (el `canExecute` solo controla el botón de play).
    5. Tras la respuesta del servidor, el spinner desaparece y la fila se actualiza automáticamente vía invalidación de caché de TanStack Query.
- **Edge Cases MVP**:
    - No se permite ejecutar si el ticket ya está `in_progress`, `done` o `cancelled`.
    - No se permite ejecutar si `flow_type` es null.
    - Múltiples ejecuciones simultáneas de distintos tickets: cada fila maneja su propio estado de forma aislada.
- **Manejo de Errores**:
    - El error se muestra via Toasts (Paso 1.3).
    - El spinner desaparece automáticamente cuando `isPending` vuelve a `false`.
    - La fila restaura su interactividad tras cualquier resultado.

## 2. Diseño Técnico

- **Archivo**: `dashboard/app/(app)/tickets/page.tsx`
- **Derivación de Estado**:
    ```typescript
    const isExecuting = executeTicket.isPending && executeTicket.variables?.ticketId === ticket.id
    ```
- **Lógica de Permiso**:
    ```typescript
    const canExecute =
      ticket.status !== 'in_progress' &&
      ticket.status !== 'done' &&
      ticket.status !== 'cancelled' &&
      !!ticket.flow_type
    ```
- **Spinner Condicional**:
    ```tsx
    {isExecuting ? (
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    ) : (
      <Play className="h-4 w-4" />
    )}
    ```
- **Refresco de Datos**: Invalidación de `['tickets']` y `['ticket', ticketId]` gestionada por `useExecuteTicket` en `onSettled`.

## 3. Decisiones

- **Derivación de estado desde React Query**: No se usa estado local adicional. La UI refleja fielmente el estado real de la mutation.
- **Aislamiento por fila**: El `isExecuting` se compara con `ticket.id` específico, permitiendo múltiples ejecuciones simultáneas sin conflicto.
- **Spinners vs filas completas**: Se opted por animaciones en el botón únicamente, no en toda la fila, para mantener legibilidad de datos durante procesamiento.

## 4. Criterios de Aceptación

| # | Criterio | Verificado |
|---|----------|------------|
| 1 | Al ejecutar, el botón Play cambia a spinner circular | ✅ |
| 2 | El spinner aparece SOLO en la fila del ticket ejecutado | ✅ |
| 3 | No se puede ejecutar tickets en estado `done`, `in_progress`, `cancelled` | ✅ |
| 4 | Tras ejecución exitosa, el estado del ticket cambia sin recarga manual | ✅ |
| 5 | Si la ejecución falla, el spinner desaparece y la UI es interactiva | ✅ |
| 6 | El botón de edición/eliminación permanece disponible durante ejecución | ✅ |

## 5. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Race condition si `variables` es undefined | El optional chaining `executeTicket.variables?.ticketId` retorna `undefined`, que nunca iguala un `ticket.id` real. |
| Invalidación tardía de caché | El `onSettled` de `useExecuteTicket` invalida antes de que el componente se re-renderice con el nuevo estado. |

## 6. Plan

**Estado**: ✅ COMPLETADO

| Tarea | Estado |
|-------|--------|
| T1: Extraer `isExecuting` en `ColumnDef` | ✅ Implementado (línea 115) |
| T2: Spinner condicional vs Play | ✅ Implementado (líneas 139-143) |
| T3: Estilos `animate-pulse` en botón | ✅ Implementado (línea 136) |
| T4: Verificar `ticketId` en variables | ✅ Implementado (línea 134 pasa `ticketId`) |

---

### 🔮 Roadmap (NO implementar ahora)

- **Fila completa con estado "processing"**: Añadir opacidad reducida a toda la fila y deshabilitar edición/eliminación durante ejecución.
- **WebSockets/Supabase Realtime**: Reemplazar invalidación por suscripciones para actualizaciones instantáneas.
- **Barra de progreso por pasos**: Mostrar avance si el flow reporta pasos intermedios.
