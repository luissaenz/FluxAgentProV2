# Análisis Técnico - Paso 1.4: Refinamiento UI Lista de Tickets

## 1. Diseño Funcional

### Happy Path
1. Usuario hace clic en el botón "Ejecutar" de una fila específica en la lista de tickets
2. El botón de esa fila muestra un indicador de carga (spinner animado) y se deshabilita
3. Aparece un toast de carga con mensaje personalizado incluyendo el título del ticket
4. El backend procesa la ejecución del ticket
5. Tras respuesta exitosa:
   - El toast de carga se reemplaza por toast de éxito
   - Los datos de la lista se refrescan automáticamente
   - El estado del ticket se actualiza en la UI (de "backlog" o "todo" a "in_progress")
6. El indicador de carga desaparece y el botón vuelve a estar disponible

### Edge Cases Relevantes para MVP
- **Error de red durante ejecución:** El toast de carga se reemplaza por mensaje específico de "Error de conexión" sin detalles técnicos
- **Error de API (ej: ticket ya ejecutándose):** Mensaje de error detallado del backend se muestra en toast
- **Múltiples clics:** El botón se deshabilita durante ejecución pendiente, previniendo ejecuciones duplicadas
- **Ticket sin flow_type:** El botón ejecutar no se muestra para tickets sin flujo asignado

### Manejo de Errores
- Errores de red: "Error de conexión. Verifique su conexión e intente nuevamente."
- Errores de API: Mensaje específico del backend (ej: "El ticket ya está en ejecución")
- En ambos casos, el indicador de carga desaparece y el botón se habilita nuevamente

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Modificación:** `dashboard/app/(app)/tickets/page.tsx` - Columna de acciones en DataTable
  - Añadir lógica de estado `isExecuting` específica por fila
  - Modificar el botón ejecutar para mostrar spinner condicional
  - Añadir clases CSS para animación de pulso durante carga

### Interfaces (Inputs/Outputs)
- **Input:** Estado del hook `useExecuteTicket` (isPending, variables.ticketId)
- **Output:** UI actualizada con indicadores visuales y datos refrescados

### Modelos de Datos
- Sin cambios en modelos de datos existentes (Ticket ya incluye status, task_id, etc.)

### Integraciones
- **Hook `useExecuteTicket`:** Utiliza onSettled para invalidar queries ['tickets'] y ['ticket', ticketId]
- **React Query:** Invalidation automática dispara refetch de datos
- **Toast system (Sonner):** Integración existente en el hook para feedback visual

## 3. Decisiones

- **Indicador de carga por fila:** Implementar `isExecuting` local en la celda de acciones para evitar afectar otras filas
- **Animación de pulso:** Usar `animate-pulse` de Tailwind para feedback visual sutil durante carga
- **Spinner personalizado:** Div con border animado en lugar de íconos predefinidos para consistencia con diseño
- **Auto-refresh inmediato:** Invalidar queries en onSettled para refresco síncrono tras respuesta, sin polling manual

## 4. Criterios de Aceptación
- El spinner aparece en el botón ejecutar inmediatamente al hacer clic
- El botón ejecutar se deshabilita durante la ejecución pendiente
- El toast de carga incluye el título del ticket específico
- Tras respuesta exitosa, el toast de éxito aparece y los datos se refrescan automáticamente
- En caso de error, el mensaje específico aparece y el botón se habilita nuevamente
- El indicador de carga desaparece solo después de recibir respuesta (éxito o error)
- Los cambios de estado del ticket (ej: a "in_progress") se reflejan inmediatamente en la lista

## 5. Riesgos

### Riesgos Concretos del Paso
- **Carrera de condiciones en múltiples ejecuciones:** Si el usuario hace clic rápido en varios botones, podría haber estados inconsistentes temporalmente
  - **Mitigación:** El botón se deshabilita globalmente durante cualquier ejecución pendiente (`disabled={executeTicket.isPending}`)

- **Delay en invalidation:** Si el backend responde rápido pero la invalidation es lenta, el usuario podría ver datos obsoletos por milisegundos
  - **Mitigación:** Usar onSettled que se ejecuta siempre, garantizando refresco post-respuesta

- **Sobrecarga de queries:** Invalidar queries frecuentemente podría causar requests innecesarios si hay muchas ejecuciones seguidas
  - **Mitigación:** El hook ya tiene staleTime de 5s y refetchInterval de 10s en useTickets, limitando sobrecarga

## 6. Plan

1. **Modificar columna actions en DataTable (Baja complejidad)**
   - Añadir variable `isExecuting` comparando `executeTicket.variables?.ticketId === ticket.id`
   - Modificar className del botón para incluir `animate-pulse` cuando ejecutando
   - Cambiar ícono del botón: spinner animado vs Play

2. **Verificar integración con hook existente (Baja complejidad)**
   - Confirmar que `onSettled` invalida queries correctamente
   - Probar flujo completo: clic -> carga -> éxito -> refresh

3. **Testing manual de edge cases (Media complejidad)**
   - Probar error de red (desconectar internet)
   - Probar múltiples clics en secuencia
   - Verificar que otros botones (editar, eliminar) no se afectan

## 🔮 Roadmap

### Optimizaciones
- **Skeleton loading:** Reemplazar spinner por skeleton loader más moderno para toda la fila durante carga
- **Transiciones suaves:** Añadir animaciones de entrada/salida para cambios de estado
- **Bulk actions:** Permitir ejecutar múltiples tickets seleccionados con indicadores agrupados

### Mejoras
- **Progress indicators:** Mostrar progreso porcentual para ejecuciones largas usando eventos en tiempo real (futuro E6)
- **Undo actions:** Permitir cancelar ejecución justo después de iniciar
- **Execution queue:** Mostrar cola de ejecuciones pendientes con indicadores de progreso

### Features Futuras
- **Real-time updates:** Integrar con transcripts en tiempo real para mostrar progreso detallado durante ejecución
- **Execution history:** Mostrar historial de ejecuciones previas con timestamps y resultados
- **Conditional execution:** Permitir ejecutar solo si ciertas condiciones se cumplen (dependencias entre tickets)

Decisiones tomadas pensando en roadmap:
- Arquitectura de hooks permite fácil extensión para bulk operations
- Invalidation pattern facilita integración con real-time subscriptions futuras
- Estado por fila permite granularidad para features avanzadas como queues