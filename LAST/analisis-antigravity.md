# 🧠 ANÁLISIS TÉCNICO: PASO 1.4 - REFINAMIENTO UI LISTA DE TICKETS

## 1. Diseño Funcional
- **Interacción de Ejecución**: Al hacer clic en el botón de "Play" de un ticket, el sistema debe proporcionar feedback visual inmediato y persistente durante todo el ciclo de vida de la ejecución (que puede durar varios segundos).
- **Happy Path**:
    1. El usuario presiona ejecutar en una fila específica.
    2. El botón de play se transforma en un spinner circular.
    3. La fila completa adquiere un estado visual de "procesando" (ej. opacidad reducida o un sutil pulso de fondo) para indicar que esa entidad está bajo operación.
    4. Las acciones de edición/eliminación de esa fila se deshabilitan para evitar estados inconsistentes (Race Conditions UI).
    5. Tras la respuesta del servidor, el estado visual vuelve a la normalidad y la información de la fila se actualiza (mostrando el nuevo estado `done`, `blocked` o `in_progress`).
- **Manejo de Errores**: 
    - Si la ejecución falla, el spinner desaparece y la fila vuelve a su estado normal. 
    - El feedback del error ya está cubierto por el sistema de Toasts (Paso 1.3), por lo que la UI de la lista solo debe preocuparse de restaurar la interactividad y reflejar el estado `blocked` si aplica.

## 2. Diseño Técnico
- **Entidades Afectadas**: `dashboard/app/(app)/tickets/page.tsx`.
- **Lógica de Estado**:
    - Se utilizarán las propiedades `isPending` y `variables` del hook `useExecuteTicket` para identificar la fila exacta en ejecución.
    - Condicionante: `isExecuting = executeTicket.isPending && executeTicket.variables?.ticketId === row.id`.
- **Componentes**:
    - **DataTable (Row)**: Se inyectarán clases dinámicas de Tailwind (`animate-pulse`, `pointer-events-none`) basadas en `isExecuting`.
    - **Botón de Acción**: Sustitución del icono `Play` por un componente `Loader2` (de Lucide) con rotación.
- **Refresco de Datos**: 
    - El hook `useExecuteTicket` ya gestiona el invalidar las queries en `onSettled`. 
    - Se debe asegurar que `useTickets` tenga un `refetchInterval` razonable (ej. 10s) para capturar cambios externos, pero el refresco tras ejecución debe ser instantáneo mediante la invalidación de caché de TanStack Query (`invalidateQueries(['tickets'])`).

## 3. Decisiones
- **Derivación de Estado**: No se creará un estado local `loadingIds[]` en el componente. En su lugar, se derivará directamente del estado de la mutación de React Query para garantizar que la UI refleje fielmente la realidad del proceso de red.
- **Micro-animaciones**: Se usará `animate-pulse` en el texto de la fila para dar una sensación de "sistema vivo" durante la espera del agente de IA.

## 4. Criterios de Aceptación
1. **Feedback Visual**: ¿Al ejecutar un ticket, el botón cambia a un spinner? [ ]
2. **Aislamiento**: ¿El spinner aparece SOLO en la fila del ticket ejecutado y no en toda la tabla? [ ]
3. **Bloqueo de UI**: ¿Se deshabilitan las acciones de la fila (editar/eliminar) mientras se ejecuta? [ ]
4. **Refresco**: ¿Tras un éxito, el estado del ticket en la tabla cambia automáticamente a `done` o `in_progress` sin que el usuario recargue manualmente? [ ]
5. **Robustez**: ¿Si la ejecución falla, desaparece el spinner y la fila es seleccionable nuevamente? [ ]

## 5. Riesgos
- **Latencia de Invalación**: React Query puede tardar unos milisegundos en disparar el refetch tras invalida.
    - *Mitigación*: Se mantendrá el spinner hasta que `isPending` sea falso, lo cual ocurre después de que `onSettled` (y por ende la invalidación) comience.
- **Sobrecarga de Red**: Si hay muchos tickets en ejecución simultánea, las múltiples invalidaciones podrían saturar.
    - *Mitigación*: El MVP asume ejecuciones unitarias por usuario. Por ahora, no se requiere un manejo de batches.

## 6. Plan
1. **Tarea 1**: Modificar `ColumnDef` en `tickets/page.tsx` para extraer `isExecuting` dentro de la celda de acciones. (Complejidad: Baja)
2. **Tarea 2**: Implementar el renderizado condicional del botón de ejecución (Spinner vs Play). (Complejidad: Baja)
3. **Tarea 3**: Aplicar estilos de "fila ocupada" (opacidad y pulse) basados en `isExecuting`. (Complejidad: Baja)
4. **Tarea 4**: Verificar que el hook `useExecuteTicket` incluya `ticketId` en sus variables para que la comparación en el punto 1 funcione. (Complejidad: Baja)

### 🔮 Roadmap (NO implementar ahora)
- **WebSockets/Real-time**: Cambiar el polling/invalidación por suscripciones reales de Supabase para actualizaciones instantáneas de estado de tickets sin disparar refetches completos.
- **Barra de Progreso**: Si el flow reporta pasos intermedios, mostrar una mini-barra de progreso dentro de la fila.
