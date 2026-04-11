# 📋 ANÁLISIS TÉCNICO — Paso 1.3: Potenciar hook useExecuteTicket con Toasts

**Agente:** oc  
**Paso:** 1.3  
**Fecha:** 2026-04-11

---

## 1. Diseño Funcional

### 1.1 Comprensión del Paso

**Problema que resuelve:** Proporcionar feedback inmediato al usuario después de ejecutar un ticket, mostrando notificaciones visuales de éxito o error.

**Inputs:**
- `ticketId`: UUID del ticket a ejecutar

**Outputs:**
- Toast de éxito si la ejecución retorna HTTP 2xx
- Toast de error si la ejecución falla (HTTP 4xx/5xx)
- Invalidación de queries para refrescar datos

**Rol en la fase:** Este paso complementa el flujo existente añadiendo feedback visual al usuario.

### 1.2 Happy Path

```
1. Usuario hace click en "Ejecutar" en la UI
2. useExecuteTicket mutation se dispara
3. API retorna OK (200) con ticket actualizado
4. onSuccess callback:
   a. queryClient.invalidateQueries (refresca datos)
   b. toast() muestra notificación de éxito con task_id
5. UI muestra datos actualizados automáticamente
```

### 1.3 Edge Cases

| Edge Case | Manejo Actual Propuesto | ¿MVP? |
|----------|------------------------|-------|
| Ejecución exitosa | Toast "Éxito" + task_id vinculado | ✓ |
| Ticket sin flow_type | Toast error 400 antes de execute | ✓ |
| Flow no encontrado | Toast error 404 desde API | ✓ |
| Ticket ya en ejecución | Toast warning 409 | ✓ |
| Error de infraestructura (500) | Toast error con mensaje del backend | ✓ |
| Timeout de red | Toast error genérico de red | ✓ |
| Usuario hace click mientrasloading | Mutation deshabilitada via isPending | ✓ |

### 1.4 Manejo de Errores

**Errores que el usuario ve:**

| Código | Escenario | Feedback Propuesto |
|--------|----------|-----------------|
| 400 | Ticket sin flow_type | "El ticket no tiene un flow asociado" |
| 404 | Flow no encontrado | "Flow no encontrado" |
| 409 | Ya en ejecución | "El ticket ya está en ejecución" |
| 500 | Error de infraestructura | "Error al ejecutar: {detalle}" |

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Archivo | Rol |
|-----------|--------|-----|
| Hook existente | `dashboard/hooks/useTickets.ts:57` | mutation para ejecutar ticket |
| Componente Toaster | `dashboard/components/ui/sonner.tsx` | Contenedor visual de toasts |
| Providers | `dashboard/app/providers.tsx` | Toaster configurado globalmente |
| API Response | `src/api/routes/tickets.py:384` | Retorna ticket con task_id |

### 2.2 Integración Técnica

**API de Sonner ya integrada:**
- `sonner` package instalado
- `Toaster` renderizado en `providers.tsx`
- Solo requiere invocar `toast()` desde el hook

**Cambio requerido en useExecuteTicket:**

```typescript
// dashboard/hooks/useTickets.ts
import { toast } from 'sonner'

export function useExecuteTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ticketId: string) => api.post(`/tickets/${ticketId}/execute`),
    onSuccess: (data, ticketId) => {
      // Invalidación existente
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] })
      
      // Toast de éxito
      toast.success(`Ticket ejecutado`, {
        description: `Task ${data.task_id} iniciada`,
      })
    },
    onError: (error, ticketId, context) => {
      // Extraer mensaje del error
      const message = error?.detail?.message || error?.detail?.error || 'Error al ejecutar'
      toast.error(message)
    },
  })
}
```

### 2.3 Tipos de Error

**Estructura de error del backend (tickets.py:347-360):**
```python
raise HTTPException(
    status_code=500,
    detail={
        "message": "Flow execution failed",
        "ticket_id": ticket_id,
        "task_id": result.get("task_id"),
        "status": "blocked",
        "error": result.get("error"),
    }
)
```

El frontend Axios interceptor o manejo de error debe extraer:
- `error.response.data.detail.message` o
- `error.response.data.detail.error` o
- `error.message` fallback

### 2.4 Contratos Existentes

**Coherencia verificada con `estado-fase.md`:**
- ✓ Hook usa `api.post` (patrón consistente)
- ✓ Invalidación de queries ya implementada
- ✓sonner ya configurado globalmente

---

## 3. Decisiones

### Decisión 1: Posición del Toast

| Decisión | Justificación |
|----------|---------------|
| toast.success() en onSuccess | Mostrar feedback positivo inmediatamente |
| toast.error() en onError | Errores son casos excepcionales, merece visibilidad |

### Decisión 2: Mensaje de Éxito

| Decisión | Justificación |
|----------|---------------|
| "Ticket ejecutado" + taskID | Identificación clara de qué task se inició |

### Decisión 3: Manejo de Errores de Infraestructura

| Decisión | Justificación |
|----------|---------------|
| Mostrar error.detail.message | El backend provee contexto útil (error, task_id, status) |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificación |
|---|----------|--------------|
| CA-001 | Toast de éxito aparece tras ejecución exitosa | Inspección visual |
| CA-002 | Toast de error aparece si flow_type vacío | Probar con ticket sin flow_type |
| CA-003 | Toast de warning si ticket ya en ejecución (409) | Probar doble click |
| CA-004 | Toast muestra task_id en caso de éxito | Inspección visual |
| CA-005 | Datos se refrescan automáticamente tras ejecución | Verificar query invalidation |
| CA-006 | Toasts no appearing if componente no mounted | Casos edge |

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|-------|--------|------------|
| Error parsing incorrecto si estructura cambian | Media | Fallback a mensaje genérico |
| Toast shown antes de query invalidation | Baja | El order no critical |
| isPending no previene doble click | Baja | React Query deshabilita automáticamente |

**Nivel de riesgo técnico:** BAJO — APIs simples y already integrated.

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1.1 | Importar `toast` de sonner en useTickets.ts | Baja | Ninguna |
| 1.2 | Agregar onSuccess callback con toast.success | Baja | 1.1 |
| 1.3 | Agregar onError callback con toast.error | Baja | 1.2 |
| 1.4 | Test - verificar toast en ejecución exitosa | Media | 1.3 |
| 1.5 | Test - verificar toast en ejecución fallida | Media | 1.3 |

### Estimación Total

- **Complejidad:** Baja
- **Tiempo estimado:** 2-3 horas (incluye testing)
- **Dependencias externas:** Ninguna (sonner ya instalado)

---

## 🔮 Roadmap (NO implementar ahora)

### 5.1 Toasts para otras operaciones

**Descripción:** Añadir toasts similares para:
- `useCreateTicket()` — Toast "Ticket creado"
- `useUpdateTicket()` — Toast "Ticket actualizado"
- `useDeleteTicket()` — Toast "Ticket cancelado"

### 5.2 Toast con acción

**Descripción:** Añadir botón de acción en toast, ej. "Ver task" que navega a la página de la task.

### 5.3 Pending Toast

**Descripción:** Mostrar toast "Ejecutando..." usando `toast.promise()` para feedback inmediato durante ejecución.

---

## 📎 Referencias

- `dashboard/hooks/useTickets.ts:57` — Hook a modificar
- `dashboard/components/ui/sonner.tsx` — Toaster component
- `dashboard/app/providers.tsx` — Toaster configurado
- `src/api/routes/tickets.py:347-360` — Error response format
- `docs/estado-fase.md` — Contratos vigentes