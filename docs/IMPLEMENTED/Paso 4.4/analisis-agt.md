# 🧠 ANÁLISIS TÉCNICO: Paso 4.4 - AnalyticalAssistantChat.tsx

## Perfil del Análisis
- **Agente:** Antigravity
- **Paso:** 4.4 [Frontend] - Implementación del Chat de Asistente Analítico.
- **Estado de Fase Relacionado:** Fase 4 - Capa de Inteligencia Visual y Analítica.
- **Contrato Backend:** `POST /analytical/ask` (Definido en `estado-fase.md`).

---

## 1. Diseño Funcional

### Happy Path
1. El usuario accede al dashboard y activa el chat analítico desde la barra lateral o un botón flotante en la sección de Analítica.
2. El usuario ingresa una consulta (ej: "¿Cuál es el flow con más errores en las últimas 24h?").
3. El componente muestra un estado de "pensando" (Skeleton o Typing Indicator animado con Framer Motion).
4. El backend procesa la consulta vía `AnalyticalCrew`.
5. Se recibe la respuesta y se renderiza:
    - **Summary:** Narrativa en Markdown con insights.
    - **Data Visualizer:** Una tabla compacta o lista si hay datos estructurados.
    - **Metadata:** Badge discreto indicando tokens y filas procesadas.

### Edge Cases (MVP)
- **Consultas Vacías o sin Sentido:** El sistema debe manejar el "I don't know" del LLM sin romperse, mostrando el summary coherente que retorne el backend.
- **Grandes Volúmenes de Datos:** Si `row_count` es alto (ej: >50), el componente debe truncar la vista previa de la tabla y ofrecer un scroll interno.
- **Fallos de Conectividad (Offline):** Mostrar estado deshabilitado del input si no hay conexión.

### Manejo de Errores
- **Error 500/Timeout:** Mensaje "The analytical crew is currently unavailable. Please try again in a few seconds."
- **Rate Limit (429):** Feedback explícito: "Too many questions. Our AI needs a short break."

---

## 2. Diseño Técnico

### Estructura de Componentes
- **`AnalyticalAssistantChat` (Contenedor Principal):** Maneja el estado de la conversación y el layout del sidebar.
- **`ChatBubble`:** Diferenciación visual clara entre `user` y `assistant`.
- **`DataPreviewTable`:** Componente ligero para renderizar la lista `data` del response de forma compacta.
- **`AnalyticalInput`:** Campo de texto con auto-resize y validación básica.

### Interface de Datos (Frontend State)
```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string; // Summary en el caso del asistente
  data?: any[];    // Datos crudos para visualización
  metadata?: {
    tokens_used: number;
    row_count: number;
  };
  status: 'sending' | 'success' | 'error';
}
```

### Integración con API
- Endpoint: `POST /analytical/ask`
- Payload: `{ "question": string }`
- Headers: Incluir `Authorization` y asegurar que el `org_id` sea manejado por el middleware del backend (según contrato de Fase 4).

---

## 3. Decisiones

1. **Persistencia Local (Session-based):** Para el MVP, el historial del chat se mantendrá en el estado de React (o `localStorage` opcionalmente) para evitar añadir carga de base de datos extra (tablas de `chat_history`).
2. **Uso de React Markdown:** Necesario para que el `AnalyticalCrew` pueda resaltar KPIs (ej: **85%**) y estructurar su narrativa con listas o negritas.
3. **Framer Motion para el Sidebar:** Se usará para un efecto de "deslizado" suave desde la derecha, manteniendo la estética premium definida para LUMIS.

---

## 4. Criterios de Aceptación (NUEVO)

- [✅] El chat se abre y cierra correctamente sin afectar el layout principal del dashboard.
- [✅] Al presionar Enter (sin Shift), la pregunta se envía al backend.
- [✅] Se muestra un indicador de carga visible mientras se espera la respuesta de la API.
- [✅] El summary se renderiza correctamente interpretando el formato Markdown.
- [✅] Si la respuesta incluye `data`, se visualiza al menos una vista previa de los primeros 5 registros.
- [✅] El botón de envío se deshabilita mientras hay una consulta en curso.

---

## 5. Riesgos

- **Riesgo:** Alta latencia en las respuestas del LLM (Step 4.3).
  - **Mitigación:** Asegurar que el frontend tenga un timeout generoso (30s) y un estado de carga "humano" (mensajes rotativos de carga).
- **Riesgo:** Inconsistencia de tipos en el campo `data`.
  - **Mitigación:** El componente `DataPreviewTable` debe realizar un mapeo dinámico de llaves buscando las columnas más relevantes.

---

## 6. Plan

1. **Tarea 1 [Media]:** Crear el Layout del Sidebar Chat con soporte responsive y animaciones de entrada.
2. **Tarea 2 [Baja]:** Implementar el servicio de API/Hook para conectar con `/analytical/ask`.
3. **Tarea 3 [Media]:** Desarrollar los componentes de burbujas de chat y renderizado de Markdown.
4. **Tarea 4 [Baja]:** Implementar visualización compacta de datos (Table View) para el campo `data`.
5. **Tarea 5 [Baja]:** Pulido estético (Scroll automático, micro-interacciones en el input).

---

### 🔮 Roadmap (NO implementar ahora)
- Exportación de resultados analíticos a CSV/PDF.
- Gráficos dinámicos (Charts) basados en el campo `data` (ej. BarChart si detecta series temporales).
- Persistencia de hilos de conversación en base de datos.
