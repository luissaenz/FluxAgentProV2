# 🏛️ ANÁLISIS UNIFICADO: PASO 1.4 - REFINAMIENTO UI LISTA DE TICKETS

**Fecha de unificación:** 2026-04-11
**Agentes participantes:** antigravity, kilo, oc, qwen, claude
**Paso:** 1.4 (Fase 1 - Hardening de Tickets)
**Estado:** ✅ COMPLETADO

---

## 1. Resumen Ejecutivo

El paso 1.4 implementa feedback visual de carga en la lista de tickets del dashboard. Cuando un usuario ejecuta un ticket, el botón "Play" de esa fila específica se reemplaza por un spinner animado, indicando procesamiento activo. El sistema ya contaba con toasts de feedback (Paso 1.3), por lo que este paso se enfoca en la señalización visual dentro de la tabla.

La implementación está **completa y funcional**. El archivo principal es `dashboard/app/(app)/tickets/page.tsx`, con soporte del hook `useExecuteTicket` en `dashboard/hooks/useTickets.ts`.

---

## 2. Diseño Funcional Consolidado

### Happy Path

1. Usuario hace clic en el botón `Play` de una fila elegible.
2. **Inmediatamente:**
   - El botón `Play` se reemplaza por un spinner circular (`animate-spin`).
   - El botón adquiere clase `animate-pulse text-primary`.
   - El botón se deshabilita globalmente (`disabled={executeTicket.isPending}`).
3. Se muestra toast de carga con el título del ticket (gestionado por `useExecuteTicket`).
4. Backend procesa la ejecución.
5. **Al recibir respuesta:**
   - Toast de carga se reemplaza por toast de éxito con `task_id` parcial.
   - Se invalidan queries `['tickets']` y `['ticket', ticketId]`.
   - La tabla refresca automáticamente.
   - El spinner desaparece y el botón vuelve a `Play`.

### Edge Cases MVP

| Escenario | Comportamiento |
|-----------|----------------|
| Ticket sin `flow_type` | Botón `Play` no se renderiza |
| Ticket en `in_progress`, `done`, `cancelled` | Botón `Play` no se renderiza |
| Error de red | Toast específico de conexión + spinner desaparece |
| Error de API (4xx/5xx) | Toast con mensaje del backend + spinner desaparece |
| Ticket inexistente | Toast de error + fila no existe |
| Ejecución simultánea de distinto ticket | Cada fila maneja su propio `isExecuting` correctamente |

### Manejo de Errores (UX)

- **Error de red:** Toast: "Error de conexión. Verifique su conexión e intente nuevamente."
- **Error de API:** Toast con mensaje exacto del backend.
- **Spinner desaparece** en ambos casos al resolverse la promesa.

---

## 3. Diseño Técnico Definitivo

### Archivo Principal

**`dashboard/app/(app)/tickets/page.tsx`** (líneas 113-169)

### Derivación de Estado de Ejecución

```typescript
const isExecuting = executeTicket.isPending && executeTicket.variables?.ticketId === ticket.id
```

**Nota importante:** Esta comparación funciona porque `mutate({ ticketId, ticketTitle })` pasa `ticketId` en las variables. El `optional chaining` (`?.`) previene errores si `variables` es `undefined`.

### Lógica de Elegibilidad

```typescript
const canExecute =
  ticket.status !== 'in_progress' &&
  ticket.status !== 'done' &&
  ticket.status !== 'cancelled' &&
  !!ticket.flow_type
```

### Renderizado del Botón

```tsx
<Button
  variant="ghost"
  size="icon"
  onClick={() => executeTicket.mutate({ ticketId: ticket.id, ticketTitle: ticket.title })}
  disabled={executeTicket.isPending}  // ← GLOBAL: bloquea TODOS los play
  className={isExecuting ? 'animate-pulse text-primary h-8 w-8' : 'h-8 w-8 text-muted-foreground hover:text-primary'}
  title="Ejecutar"
>
  {isExecuting ? (
    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
  ) : (
    <Play className="h-4 w-4" />
  )}
</Button>
```

### Contrato con Hook `useExecuteTicket`

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `mutate({ ticketId, ticketTitle })` | Función | Dispara la ejecución |
| `isPending` | boolean | Estado global de cualquier ejecución |
| `variables?.ticketId` | string \| undefined | ID del ticket en ejecución |

### Integración con React Query

- `onSettled` en `useExecuteTicket` invalida:
  - `['tickets']` → refresca la lista completa
  - `['ticket', ticketId]` → refresca el ticket individual

---

## 4. Decisiones Tecnológicas

### D1: Spinner en botón, no en fila completa

**Decisión:** El `animate-pulse` y spinner se aplican **únicamente al botón de acción**, no a la fila completa.

**Justificación:** El análisis de `qwen` identificó que algunos análisis mencionaban "fila completa con fondo de carga", pero **el código no implementa esto**. La propuesta de fila completa se descarta porque:
- Añadiría complejidad CSS con potential conflictos de hover/focus
- El spinner en el botón ya es suficientemente visible
- Los análisis de `antigravity`, `oc`, `kilo` y `claude` indican "implementado" sin mencionar fila completa como feature

**Estado:** ✅ Confirmado por implementación existente.

### D2: Deshabilitación global vs por-fila

**Decisión:** `disabled={executeTicket.isPending}` bloquea **todos** los botones de play durante cualquier ejecución.

**Justificación ( противоречие ):** El análisis de `qwen` propuso:
> *"si se ejecutan dos tickets en rápida sucesión, el segundo spinner aparecería en ambas filas"*

Sin embargo:
- El `isExecuting` por fila sigue funcionando correctamente para mostrar el spinner donde corresponde.
- La deshabilitación global es **conservadora y segura**: previene envios duplicados al backend.
- Para el MVP, ejecuciones simultáneas de múltiples tickets por el mismo usuario es un edge case improbable.

**Trade-off aceptado:** Un usuario que quiera ejecutar Ticket A y luego Ticket B rápidamente deberá esperar que termine A.

### D3: Detección explícita de errores de red

**Decisión:** Errores de red muestran mensaje diferenciado ("Error de conexión...").

**Justificación:** Implementado en `useTickets.ts`. Esta decisión ya estaba tomada en la fase anterior (Paso 1.3) y se mantiene.

---

## 5. Criterios de Aceptación MVP ✅

### Criterios Funcionales

| # | Criterio | Verificable |
|---|----------|-------------|
| F1 | Al hacer clic en "Play", el botón cambia a spinner animado | Visual: click → spinner |
| F2 | El spinner aparece SOLO en la fila del ticket ejecutado | Visual: otras filas sin spinner |
| F3 | El botón "Play" se deshabilita durante ejecución (no clickeable) | DOM: `disabled` attribute |
| F4 | Si no hay `flow_type`, el botón Play no se renderiza | DOM: verificar filas sin flow |
| F5 | Si status es `in_progress`, `done` o `cancelled`, el botón Play no se renderiza | DOM: verificar filas en esos estados |
| F6 | Tras éxito, la tabla muestra el nuevo estado del ticket sin recarga | Visual + Network tab |
| F7 | Tras error, el spinner desaparece y el botón vuelve a estar habilitado | Visual |

### Criterios Técnicos

| # | Criterio | Verificable |
|---|----------|-------------|
| T1 | La invalidación de `['tickets']` ocurre en `onSettled` | Código: `useTickets.ts` |
| T2 | `isExecuting` compara `variables?.ticketId` con `row.id` | Código: línea 115 |
| T3 | El componente usa `animate-spin` de Tailwind para el spinner | Código: línea 140 |
| T4 | El botón pasa `ticketId` y `ticketTitle` a `mutate` | Código: línea 134 |

### Criterios de Robustez

| # | Criterio | Verificable |
|---|----------|-------------|
| R1 | Si la ejecución falla, el usuario ve toast de error descriptivo | Manual: forzar error |
| R2 | Errores de red muestran mensaje diferenciado | Manual: desconectar red |
| R3 | El spinner desaparece incluso si la promesa nunca se resuelve (timeout) | Edge case: no aplicar |

---

## 6. Plan de Implementación

**Estado: ✅ COMPLETADO**

No se requieren tareas de implementación. El paso ya está implementado y validado según `estado-fase.md`.

| # | Tarea | Estado | Notas |
|---|-------|--------|-------|
| 1 | Derivar `isExecuting` por fila en `ColumnDef` | ✅ Implementado | Línea 115 |
| 2 | Spinner condicional vs icono Play | ✅ Implementado | Líneas 139-143 |
| 3 | Estilos `animate-pulse` en botón ejecutando | ✅ Implementado | Línea 136 |
| 4 | `canExecute` para estados no ejecutables | ✅ Implementado | Líneas 116-120 |
| 5 | Integración con toasts (Paso 1.3) | ✅ Implementado | `useExecuteTicket` |
| 6 | Invalidación de queries post-ejecución | ✅ Implementado | `onSettled` |

**Tareas de validación pendientes:**

| # | Validación | Complejidad | Dependencias |
|---|------------|-------------|--------------|
| V1 | Verificar spinner solo en fila correcta con ejecución real | Baja | App corriendo |
| V2 | Verificar mensaje de error de red vs API | Baja | Simular desconexión |
| V3 | Verificar que estados terminales no muestran Play | Baja | Ninguna |

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| `variables` es `undefined` en algún caso borde | Baja | Medio: spinner no aparece en la fila correcta | `?.` optional chaining retorna `undefined`, que no iguala ningún `ticket.id` real. El botón globalmente deshabilitado sigue funcionando. |
| Invalidación de caché tardía | Baja | Bajo: usuario ve estado stale por ms | `refetchInterval: 10_000` como red de seguridad en `useTickets` |
| Doble-click antes de que `isPending` sea `true` | Muy baja | Medio: 2 requests al backend | `disabled={executeTicket.isPending}` previene clicks adicionales. Backend debe ser idempotente. |
| Deshabilitación global de todos los Play durante ejecución | N/A | Bajo: feature, no bug | Decisión de diseño conservadora. Si es problemático, cambiar a `disabled={isExecuting}` en lugar de `isPending` global. |

---

## 8. Testing Mínimo Viable

### Tests Manuales

1. **Happy Path:**
   - Crear ticket con `flow_type`
   - Ejecutar → spinner aparece → toast de éxito → estado cambia a `in_progress`

2. **Error de API:**
   - Ticket con `flow_type` mal configurado
   - Ejecutar → spinner → toast de error específico

3. **Error de Red:**
   - Desconectar red
   - Ejecutar → toast "Error de conexión"

4. **Estados Terminales:**
   - Ticket en `done` → no debe mostrar botón Play
   - Ticket en `done` → tiene `task_id` vinculado

5. **Sin flow_type:**
   - Ticket sin `flow_type` → no debe mostrar botón Play

### Cobertura de Edge Cases

| Edge Case | Método de verificación |
|-----------|------------------------|
| `isExecuting` por fila específico | Click en Play de Ticket A, confirmar que solo A muestra spinner |
| Doble-click prevention | Click rápido dos veces → solo 1 request en Network tab |
| Refresco automático | Ejecutar, verificar `task_id` aparece sin reload |
| Restauración de UI en error | Forzar error, confirmar spinner desaparece y botón vuelve |

---

## 9. 🔮 Roadmap (NO implementar ahora)

### Optimizaciones UI

| Mejora | Descripción | Bloqueador actual |
|--------|-------------|-------------------|
| **Overlay de fila completa** | Capa semitransparente con spinner en toda la fila | Decisión D1: complejidad CSS, sin request del negocio |
| **Skeleton loader** | Reemplazar `animate-pulse` por skeleton shaped | UX nice-to-have, MVP funciona |
| **Transiciones suaves** | Animaciones de entrada/salida | Prioridad baja |

### Features Futuras (Fases 2-4)

| Feature | Fase destino | Pre-requisito |
|---------|--------------|---------------|
| **Cancelar ejecución** | E6 (Transcripts) | Endpoint de cancel + UI de transcript |
| **Real-time updates** | E6 | Supabase Realtime subscriptions |
| **Batch execution** | E4 (Analytical) | Selección multiple + endpoint batch |
| **Execution queue UI** | E6 | Eventos de progreso por paso |

### Decisiones de Diseño para Futuro

- **Arquitectura de hooks:** `useExecuteTicket` es agnóstico de UI, permite extensión para bulk.
- **Invalidation pattern:** Compatible con futuras suscripciones de Supabase Realtime.
- **`ticketId` en variables:** Facilita tracking granular para features de cola/cancelación.

---

## Anexo: Evaluación de Análisis Pre-proces

| Análisis | Calidad | Aportes Clave | Contradicciones |
|----------|---------|----------------|-----------------|
| antigravity | Alta | Descripción detallada de estados, decisión de no crear estado local | Menciona "fila completa con animate-pulse" - no implementado |
| kilo | Alta | Similar a antigravity, perspectiva en español | Mismas imprecisiones |
| oc | Alta | Tabla de edge cases clara, énfasis en toasts | Mismas imprecisiones |
| qwen | **Alta +** | ⚠️ Detectó correctamente que la fila NO tiene overlay. Identificó el riesgo de deshabilitación global. Mención explícita de D1/D2/D3. | Una observación incorrecta: dice que spinner global afectaría filas - pero el código usa `isExecuting` por fila para el spinner |
| claude | Media | Confirmó implementación vs código real | Baseline para comparación |

**Conclusión:** El análisis de `qwen` aporta la evaluación más precisa de la implementación real, identificando la diferencia entre lo propuesto conceptualmente y lo implementado.
