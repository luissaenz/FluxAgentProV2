# 🏛️ ANÁLISIS TÉCNICO FINAL — Paso 4.4: Implementar AnalyticalAssistantChat.tsx

## 1. Resumen Ejecutivo
El paso 4.4 representa la culminación de la Capa de Inteligencia Analítica en el frontend. El objetivo es integrar un **Asistente Analítico Conversacional** accesible globalmente desde el Dashboard, permitiendo a los usuarios interactuar con los datos de su organización mediante lenguaje natural.

Este componente actúa como la interfaz del `AnalyticalCrew` (implementado en el paso 4.3), transformando preguntas complejas ("¿Cuál es el agente con más éxito?") en respuestas narrativas enriquecidas con tablas de datos en tiempo real. La implementación se basa en un panel lateral (Sheet) activado por un botón flotante (FAB) que garantiza acceso instantáneo sin perder el contexto de trabajo actual.

## 2. Diseño Funcional Consolidado

### 2.1 Flujo Principal (Happy Path)
1. **Acceso:** El usuario ve un botón flotante (FAB) con el icono de un cerebro (`Brain`) en la esquina inferior derecha.
2. **Apertura:** Al hacer clic, se despliega un panel lateral (`Sheet`) desde la derecha.
3. **Estado Inicial:** Si no hay mensajes, se muestra un mensaje de bienvenida y una lista de "Consultas Rápidas" (ej. "Tasa de éxito de agentes") obtenidas dinámicamente desde el backend.
4. **Interacción:** El usuario escribe una consulta libre o selecciona una rápida.
5. **Procesamiento:** Se muestra un indicador animado ("Analizando datos...") mientras el `AnalyticalCrew` procesa la respuesta.
6. **Resultados:** El asistente responde con:
   - **Badge de Intención:** Indica qué tipo de análisis se realizó (ej. `agent_performance`).
   - **Narrativa:** Un resumen sintetizado en Markdown con insights clave.
   - **Data Preview:** Una tabla compacta con los registros reales encontrados (limitada a los primeros 5 con indicador de excedente).
7. **Persistencia:** El historial de la conversación se mantiene durante la sesión activa del usuario.

### 2.2 Casos de Borde y Manejo de Errores (MVP)
- **Rate Limiting (429):** El usuario recibe un mensaje amigable: "Demasiadas consultas analíticas. Esperá un momento."
- **Consulta No Clasificada (400):** El asistente informa que no puede responder a esa pregunta específica y sugiere usar las consultas rápidas disponibles.
- **Timeout/Error de Red:** Burbuja de chat roja con icono de alerta y mensaje explicativo claro.
- **Respuesta sin Datos:** Si la consulta es válida pero no hay registros (ej. un periodo sin actividad), se muestra solo el resumen narrativo informando la situación.

## 3. Diseño Técnico Definitivo

### 3.1 Estructura de Componentes
El componente se ubica en `dashboard/components/analytical/AnalyticalAssistantChat.tsx` (ya pre-implementado) y se integra globalmente.

- **`AnalyticalAssistantChat`:** Contenedor principal con lógica de `useMutation` (TanStack Query) y estado de visibilidad.
- **`EmptyState`:** Renderiza la bienvenida y las `Quick Queries`.
- **`ChatMessageBubble`:** Manejo diferencial de estilos para `user`, `assistant` y `error`. Soporta renderizado de badges y `DataPreview`.
- **`DataPreview`:** Tabla dinámica que mapea las llaves de los objetos devueltos en `data`.

### 3.2 Integración y Contratos
- **Ubicación:** Se debe instanciar en `dashboard/app/(app)/layout.tsx` para persistencia visual en todo el dashboard.
- **Endpoints:**
  - `GET /analytical/queries`: Para poblar el estado inicial.
  - `POST /analytical/ask`: `{ "question": string }`.
- **Seguridad:** Aislamiento multi-tenant garantizado por el `org_id` inyectado automáticamente en los headers por el cliente de API existente.

### 3.3 Optimizaciones de UI/UX
- **Auto-scroll:** El chat baja automáticamente al recibir nuevos mensajes.
- **Z-Index:** Configurado en `z-50` para evitar ser solapado por la barra lateral o headers.
- **Framer Motion:** Uso de animaciones de entrada para el panel y micro-interacciones en los botones.

## 4. Decisiones Tecnológicas

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| **Patrón de Acceso** | FAB + Sheet | Máxima accesibilidad sin interrumpir el flujo de trabajo actual en el Kanban o listas de tareas. |
| **Renderizado Narrativo** | `whitespace-pre-wrap` | Suficiente para el MVP para mostrar saltos de línea y negritas básicas sin añadir dependencias externas pesadas. |
| **Manejo de Estado** | React Query | Consistencia con el resto del proyecto para el manejo de caché de queries y estados de mutación. |
| **Aislamiento de Datos** | Tabla Compacta (max 5) | Evita la saturación visual en el chat lateral. Los datos completos están en el Event Store si se requiere detalle profundo. |

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El botón flotante (FAB) es visible en todas las páginas bajo la ruta `/dashboard`.
- [ ] El panel lateral se abre correctamente al hacer clic en el FAB y se cierra al hacer clic fuera o en el botón de cerrar.
- [ ] Las consultas rápidas (Quick Queries) se ejecutan automáticamente al hacer clic en ellas.
- [ ] El chat permite enviar preguntas libres mediante la tecla `Enter`.
- [ ] Las respuestas del asistente muestran correctamente la narrativa (summary) y la tabla de datos (si aplica).

### Técnicos
- [ ] El componente está integrado en `dashboard/app/(app)/layout.tsx`.
- [ ] Se realizan llamadas correctas a `/analytical/queries` y `/analytical/ask`.
- [ ] El campo de input se deshabilita durante el estado `loading`.
- [ ] No existen errores de consola de React al abrir/cerrar el chat.
- [ ] El auto-scroll funciona al recibir una respuesta larga.

### Robustez
- [ ] El sistema muestra una burbuja roja ante errores de red o errores 500 del servidor.
- [ ] Se maneja el error 429 (Rate Limit) con el mensaje específico definido.
- [ ] Si `data` es un array vacío, la tabla no se renderiza pero el summary sí.

## 6. Plan de Implementación

| Fase | Tarea | Complejidad |
|------|-------|-------------|
| 1. Integración | Registrar el componente en el layout global para habilitar el FAB. | Baja |
| 2. Refinamiento | Ajustar z-index y márgenes para asegurar compatibilidad con sidebar colapsada. | Baja |
| 3. Validación | Pruebas de flujo completo: Consultas rápidas -> Respuesta -> Tabla. | Media |
| 4. Pulido | Añadir timeout de 30s a la mutación para evitar cuelgues. | Baja |

## 7. Riesgos y Mitigaciones
- **Riesgo:** Conflicto de superposición con otros elementos flotantes.
- **Mitigación:** Verificar el FAB en dispositivos móviles y con diferentes estados de la sidebar.
- **Riesgo:** Alta latencia en el procesamiento de IA (Step 4.3).
- **Mitigación:** Asegurar que el indicador "Analizando datos..." sea visible y no bloquee la UI.

## 8. Testing Mínimo Viable
1. **Test Visual:** Abrir el dashboard y verificar que el botón flotante está en la posición correcta.
2. **Test Funcional:** Ejecutar la consulta rápida "Tasa de éxito de agentes" y verificar la aparición de la tabla.
3. **Test de Error:** Enviar una pregunta vacía o sin sentido y verificar el manejo de error/respuesta del asistente.

## 9. 🔮 Roadmap (Post-MVP)
- **Persistencia:** Guardar historial de chat en `localStorage`.
- **Visualizaciones:** Generar mini-gráficos dinámicos (Charts) si los datos lo permiten.
- **Exportación:** Botón para descargar los resultados de la tabla en formato CSV.
- **Markdown Completo:** Integración de `react-markdown` para estilos premium enriquecidos.
