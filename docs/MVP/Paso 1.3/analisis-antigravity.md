# 🧠 ANÁLISIS TÉCNICO: PASO 1.3 - Potenciación de `useExecuteTicket` con Notificaciones

## 1. Diseño Funcional

El objetivo es mejorar la experiencia de usuario (UX) al ejecutar tickets, proporcionando retroalimentación inmediata sobre el éxito o fracaso del proceso mediante notificaciones tipo Toast.

### Happy Path
1. El usuario hace clic en el botón de ejecución de un ticket.
2. Se inicia la mutación; el frontend muestra un estado de carga (gestionado en el Paso 1.4).
3. Al recibir un código **200 OK** con los datos del ticket actualizados a `done`:
   - Se muestra un Toast de éxito: **"Ticket ejecutado con éxito"**.
   - Descripción opcional: *"El proceso ha finalizado y el ticket ha sido marcado como resuelto."*
   - Las listas y detalles del ticket se refrescan automáticamente.

### Manejo de Edge Cases para MVP
1. **Error de Lógica/Flow (500 Error):**
   - El backend marca el ticket como `blocked` y devuelve el detalle del error del agente.
   - El hook captura la excepción.
   - Se muestra un Toast de error: **"Error en la ejecución"**.
   - Descripción: El mensaje específico devuelto por la API (ej. *"El agente no tiene acceso a la herramienta X"*).
2. **Conflicto de Estado (409 Conflict):**
   - El ticket ya está `in_progress` o `done`.
   - Se muestra un Toast de advertencia: **"Acción no permitida"** con descripción *"El ticket ya está siendo procesado o ya ha finalizado."*
3. **Error de Red o Infraestructura:**
   - Si la API no responde, se muestra un Toast de error genérico: **"Error de conexión"** solicitando reintento.

### Manejo de Errores Visuales
- Se utilizarán colores semánticos (verde para éxito, rojo para errores, naranja para conflictos/warnings) a través de la librería `sonner`.

---

## 2. Diseño Técnico

### Componentes y Hooks
- **Archivo:** `dashboard/hooks/useTickets.ts`
- **Llamada:** Modificación de `useExecuteTicket`.
- **Librería de Toasts:** `sonner` (ya integrada en `dashboard/components/ui/sonner.tsx`).

### Interfaz del Hook (Pseudodiseño)
```typescript
// useExecuteTicket utilizará el objeto 'toast' de sonner
onSuccess: (data) => {
  toast.success("Ejecución finalizada", { 
    description: `El ticket ${data.id} se ha procesado correctamente.` 
  });
  // Invalida las queries existentes
}

onError: (error) => {
  const message = error.response?.data?.detail?.error || "Ocurrió un error inesperado.";
  toast.error("Error al ejecutar", { description: message });
}
```

### Modelos de Datos
- No se requieren cambios en los modelos de datos existentes en el backend. 
- Se asume el contrato definido en `src/api/routes/tickets.py` donde los errores de ejecución devuelven un objeto con un campo `detail`.

---

## 3. Decisiones

1. **Uso de `sonner` sobre `react-hot-toast` o `shadcn/toast`:** 
   - **Justificación:** Ya existe un componente `dashboard/components/ui/sonner.tsx` en el proyecto. Es más ligero y tiene un mejor sistema de apilamiento de toasts.
2. **Inclusión de Toasts en el Hook en lugar de en la Vista:**
   - **Justificación:** Centraliza la lógica de retroalimentación. Cualquier componente que ejecute un ticket (lista, detalle, dashboard) tendrá automáticamente la notificación, garantizando consistencia.
3. **Extracción Profunda de Errores:**
   - **Justificación:** El backend de FluxAgentPro devuelve errores anidados en `detail.error` para fallos de flow. El frontend debe ser capaz de alcanzar este nivel para no mostrar un "500 Internal Server Error" genérico al usuario.

---

## 4. Criterios de Aceptación (NUEVO)

1. [ ] ¿Aparece un toast de éxito al finalizar una ejecución exitosa? (Sí/No)
2. [ ] ¿El toast de éxito contiene información relevante (ej. nombre o ID del ticket)? (Sí/No)
3. [ ] ¿Aparece un toast de error rojo cuando el backend devuelve un error 500/400? (Sí/No)
4. [ ] ¿El mensaje de error en el toast refleja la causa real devuelta por el backend (ej. "Flow not found")? (Sí/No)
5. [ ] ¿Las queries de React Query se invalidan correctamente tras el éxito? (Sí/No)
6. [ ] ¿El hook sigue exportando los estados `isPending` y `status` para consumo de la UI? (Sí/No)

---

## 5. Riesgos

- **Riesgo:** Bombardeo de notificaciones si el usuario hace clic repetidamente.
- **Mitigación:** El Paso 1.4 implementará bloqueos de botones (`disabled={isPending}`), pero `sonner` por defecto limita las visualizaciones simultáneas.
- **Riesgo:** Formato de error de la API inconsistente.
- **Mitigación:** Asegurar un "fallback" a un mensaje genérico si `error.response.data.detail` no tiene la estructura esperada.

---

## 6. Plan de Implementación

1. **Tarea 1 (Baja):** Importar `toast` desde `@/components/ui/sonner` en `dashboard/hooks/useTickets.ts`.
2. **Tarea 2 (Media):** Refactorizar `useExecuteTicket` para añadir el objeto de configuración a `useMutation`.
3. **Tarea 3 (Media):** Implementar lógica de extracción de mensajes de error de la respuesta de Axios/API.
4. **Tarea 4 (Baja):** Añadir llamadas a `toast.success` y `toast.error` en los callbacks correspondientes.
5. **Tarea 5 (Baja):** Verificar que la invalidación de queries siga funcionando correctamente.

---

### Sección Final: 🔮 Roadmap (NO implementar ahora)
- **Acciones en Toasts:** Permitir "Deshacer" o "Ver log" directamente desde el toast.
- **Persistencia de Toasts:** Guardar el historial de ejecuciones (éxito/error) en una pequeña campana de notificaciones.
- **Streaming de Progreso:** Sustituir el toast de éxito final por una barra de progreso real (conectada a los Transcripts del E6).
