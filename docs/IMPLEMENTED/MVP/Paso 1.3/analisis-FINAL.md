# 🏛️ ANÁLISIS FINAL: PASO 1.3 - Potenciación de `useExecuteTicket` con Notificaciones (Toasts)

## 1. Resumen Ejecutivo
Este paso consiste en elevar la experiencia de usuario (UX) del sistema de tickets mediante la integración de retroalimentación visual inmediata. Actualmente, la ejecución de un ticket ocurre "en silencio" desde la perspectiva del hook, lo que genera incertidumbre en el usuario.

Se potenciará el hook `useExecuteTicket` para que, conservando su lógica interna de invalidación de caché, dispare notificaciones tipo **Toast** (usando la librería `sonner` ya integrada) para informar sobre el inicio, éxito o fracaso de la operación, extrayendo los motivos específicos de error desde el backend (FastAPI).

---

## 2. Diseño Funcional Consolidado

### Happy Path
1. El usuario acciona el botón de ejecución (Play) desde la lista o detalle de un ticket.
2. **Feedback Inmediato:** El botón entra en estado de carga (paso 1.4) y se dispara la petición.
3. **Éxito:** Al recibir respuesta satisfactoria (200 OK):
   - Aparece un Toast de éxito: **"Ticket ejecutado correctamente"**.
   - Se incluye el `task_id` (abreviado) en la descripción: *"Tarea {id...} iniciada"*.
   - La lista de tickets se refresca automáticamente.

### Edge Cases (MVP)
1. **Error de Lógica de Negocio (4xx/5xx):**
   - El backend retorna un error (ej. "Flow not found", "Ticket already in progress").
   - Se muestra un Toast de error de color rojo.
   - **Contenido:** El mensaje exacto retornado por la propiedad `detail.error` del backend.
2. **Error de Conexión / Red:**
   - La petición falla antes de llegar al servidor o por timeout.
   - Se muestra un Toast indicando **"Error de conexión"** con sugerencia de reintento.
3. **Ticket ya bloqueado:**
   - Si la ejecución falla y el backend marca el ticket como `blocked`.
   - El Toast debe informar que el ticket ha sido bloqueado para revisión manual.

### Manejo de Errores Visuales
- Se utilizará la API imperativa de `sonner` (`toast.success`, `toast.error`) para garantizar que el color y el icono coincidan con la semántica de la respuesta.

---

## 3. Diseño Técnico Definitivo

### Ubicación y Componentes
- **Hook:** `dashboard/hooks/useTickets.ts`.
- **Dependencia:** `sonner` (paquete ya configurado en el `Toaster` global de `providers.tsx`).

### Definición Técnica del Cambio
Se modificará el hook `useExecuteTicket` dentro de `useMutation` para incluir los callbacks de ciclo de vida:

1. **`onMutate` (Opcional):** Se descarta el uso de `toast.loading` integrado en favor de simplicidad, permitiendo que el estado `isPending` del botón sea el indicador de carga principal (conforme al paso 1.4).
2. **`onSuccess`:**
   - Invalida queries: `['tickets']`, `['ticket', ticketId]`.
   - Invoca: `toast.success("Ejecución iniciada", { description: "Ticket movido a ejecución correctamente." })`.
3. **`onError`:**
   - Extrae el mensaje: Prioriza `error.response.data.detail.error` -> `error.response.data.detail.message` -> `error.message`.
   - Invoca: `toast.error("Fallo al ejecutar", { description: message })`.

### Contrato de Respuesta (Backend)
Se respetará el esquema definido en el hardening del paso 1.1:
- **Exito:** Retorna `TicketResponse` completo.
- **Error:** Retorna `HTTPException(detail={"message": "...", "error": "...", "task_id": "..."})`.

---

## 4. Decisiones Tecnológicas

1. **Modificación del Hook Base vs Wrapper:**
   - **Decisión:** Modificar `useExecuteTicket` directamente.
   - **Justificación:** Es la forma más eficiente de asegurar que todos los "call sites" existentes (vista de lista y vista de detalle) obtengan la funcionalidad sin refactorizar imports.
2. **Uso de Sonner:**
   - **Decisión:** Se mantiene `sonner` como estándar por su API limpia y peso ligero.
3. **Idioma Castellano:**
   - **Decisión:** Notificaciones íntegramente en español.
   - **Justificación:** Coherencia con la localización actual del dashboard `FluxAgentPro`.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] ¿Se muestra un toast verde de éxito al ejecutar un ticket válido?
- [ ] ¿El toast de éxito aparece inmediatamente después de la respuesta exitosa de la API?
- [ ] ¿Se visualiza un toast rojo de error cuando la ejecución falla por lógica del agente?
- [ ] ¿El mensaje de error del toast contiene información específica (ej. "Flow no encontrado")?

### Técnicos
- [ ] ¿El código se compila sin errores de TypeScript en `dashboard/`?
- [ ] ¿Se importan correctamente las utilidades de `sonner`?
- [ ] ¿El hook invalida las queries de React Query tanto en éxito como en error (si aplica)?

### Robustez
- [ ] ¿Se maneja correctamente el caso donde la respuesta de error no tiene un campo 'detail' (fallback)?
- [ ] ¿El estado de carga (`isPending`) del hook se mantiene funcional para que el componente UI lo use?

---

## 6. Plan de Implementación

| Paso | Tarea | Complejidad | Dependencias |
|------|-------|-------------|--------------|
| 1 | Importar `toast` en `dashboard/hooks/useTickets.ts`. | Baja | Ninguna |
| 2 | Integrar lógica de `toast.success` en el callback `onSuccess`. | Baja | Paso 1 |
| 3 | Implementar lógica de extracción de errores en el callback `onError`. | Media | Paso 1 |
| 4 | Validar la invalidación de caché para asegurar que la UI se actualice tras el toast. | Baja | Pasos 2-3 |
| 5 | Ejecutar prueba manual de "Happy Path" y "Error Path". | Media | Pasos 1-4 |

---

## 7. Riesgos y Mitigaciones

- **Riesgo:** La estructura de error cambiante en Axios. 
  - **Mitigación:** Usar encadenamiento opcional (`error?.response?.data?.detail?.error`) y un string genérico como fallback.
- **Riesgo:** Toasts duplicados si el usuario cambia de página rápido.
  - **Mitigación:** Sonner gestiona la coexistencia de toasts automáticamente por ID o por límite de pantalla.

---

## 8. Testing Mínimo Viable

1. **Prueba de Éxito:** Ejecutar un Ticket con flow válido y verificar:
   - Dashboard refrescado (el ticket cambia de estado).
   - Toast verde visible.
2. **Prueba de Error:** Ejecutar un Ticket sin `flow_type` (forzado) o con error simulado y verificar:
   - Toast rojo visible con el motivo.
3. **Prueba de Red:** Desconectar red y ejecutar, verificar toast de error de conexión.

---

## 9. 🔮 Roadmap (NO implementar ahora)
- **Acciones Directas:** Añadir un botón "Ir a Tarea" dentro del Toast de éxito que navegue a `/tasks/{id}`.
- **Diferenciación de Gravedad:** Toasts de color ambar (warning) para errores 409 (Ya en ejecución).
- **Traducciones (i18n):** Mover los strings de las notificaciones a un sistema de traducción centralizado.
