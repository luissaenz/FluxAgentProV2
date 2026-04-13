# Análisis Técnico: Paso 4.4 - Implementar AnalyticalAssistantChat.tsx

## 1. Diseño Funcional

### Happy Path
1. Usuario accede al dashboard de FluxAgentPro
2. Ve un botón flotante con ícono de cerebro en la esquina inferior derecha
3. Click en el botón abre un panel lateral (Sheet) con el chat analítico
4. Usuario puede hacer preguntas en lenguaje natural sobre datos históricos
5. Sistema clasifica la intención usando LLM y ejecuta consultas SQL pre-validadas
6. Respuesta se muestra en formato narrativo con tabla de datos opcional
7. Usuario puede usar consultas rápidas predefinidas o preguntas libres

### Edge Cases
- **Rate limiting alcanzado**: Usuario ve mensaje de error con tiempo de espera
- **Consulta no reconocida**: Sistema informa que no puede responder y sugiere consultas disponibles
- **Error de conectividad con LLM**: Sistema usa fallback por keywords
- **Datos vacíos**: Se muestra mensaje apropiado sin tabla
- **Pregunta demasiado compleja**: LLM sintetiza respuesta narrativa clara

### Manejo de Errores
- **Rate limit excedido**: HTTP 429 con mensaje "Demasiadas consultas analíticas. Esperá un momento."
- **Query type inválido**: HTTP 400 con lista de queries disponibles
- **Error interno**: HTTP 500 con mensaje genérico de error
- **UI**: Mensajes de error se muestran en burbujas rojas con ícono de alerta

## 2. Diseño Técnico

### Componentes Nuevos
- `AnalyticalAssistantChat`: Componente principal con estado de chat, manejo de mensajes y UI
- `EmptyState`: Subcomponente para estado inicial con consultas rápidas
- `ChatMessageBubble`: Subcomponente para renderizar mensajes (usuario/asistente/error)
- `DataPreview`: Subcomponente para mostrar datos tabulares en respuestas

### Interfaces
```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
  data?: Record<string, unknown>[]
  queryType?: string
  timestamp: Date
}

interface AnalyticalQuery {
  key: string
  description: string
}
```

### Integración con APIs Existentes
- `GET /analytical/queries`: Obtiene lista de consultas predefinidas para botones rápidos
- `POST /analytical/ask`: Envía pregunta y recibe respuesta estructurada
- Rate limiting: 10 requests/min por organización
- Aislamiento multi-tenant vía `org_id` automático

### Estado y Persistencia
- Estado local en componente (no persistido en servidor)
- Mensajes se pierden al recargar página (comportamiento esperado para MVP)
- Auto-scroll automático al nuevo mensaje

## 3. Decisiones

- **Ubicación del componente**: Botón flotante global disponible en todo el dashboard, no limitado a página específica de analítica
- **Tecnología de UI**: Sheet de shadcn/ui para panel lateral responsivo
- **Manejo de estado**: React Query para cache de consultas disponibles, estado local para mensajes
- **Formato de respuestas**: Markdown para síntesis narrativa + tabla HTML para datos
- **Rate limiting**: Implementación client-side con feedback visual inmediato

## 4. Criterios de Aceptación

- El botón flotante con ícono de cerebro se muestra en la esquina inferior derecha de todas las páginas del dashboard
- Al hacer click, se abre un panel lateral de ancho 480px (540px en desktop)
- El panel muestra estado vacío con lista de consultas rápidas al abrirse por primera vez
- Las consultas rápidas ejecutan automáticamente al hacer click
- Las preguntas libres se envían con Enter o botón de enviar
- Las respuestas del asistente incluyen badge con tipo de consulta y tabla de datos cuando aplica
- Los errores se muestran en burbujas rojas con ícono de alerta
- El chat maneja rate limiting mostrando mensaje apropiado
- El componente es responsivo y funciona en móvil
- Auto-scroll funciona correctamente con nuevos mensajes

## 5. Riesgos

- **Dependencia de APIs backend**: Si endpoints `/analytical/*` no están disponibles, el componente falla silenciosamente
  - **Mitigación**: Verificar disponibilidad de APIs en desarrollo y agregar manejo de errores robusto

- **Rate limiting agresivo**: 10 req/min podría ser insuficiente para usuarios avanzados
  - **Mitigación**: Configurar límite basado en feedback de usuarios beta

- **Complejidad de respuestas LLM**: Las respuestas narrativas podrían ser confusas o demasiado técnicas
  - **Mitigación**: Incluir ejemplos de preguntas en empty state y refinar prompts del crew analítico

## 6. Plan

1. **Baja**: Verificar que `AnalyticalAssistantChat.tsx` esté correctamente implementado y funcional
2. **Baja**: Agregar componente al layout principal `app/(app)/layout.tsx` para disponibilidad global
3. **Baja**: Probar integración con APIs backend existentes
4. **Media**: Verificar responsividad en diferentes tamaños de pantalla
5. **Baja**: Probar casos de error (rate limit, consultas inválidas)
6. **Baja**: Ejecutar pruebas E2E de interacción completa del chat

### Dependencias
- Requiere que paso 4.3 (AnalyticalCrew backend) esté completado y funcional
- Depende de existencia de endpoints `/analytical/ask` y `/analytical/queries`

## 🔮 Roadmap

- **Persistencia de conversaciones**: Guardar historial de chat en localStorage o base de datos
- **Exportación de datos**: Permitir descargar resultados en CSV/Excel desde la tabla preview
- **Consultas personalizadas**: Permitir que usuarios creen sus propias consultas SQL validadas
- **Integración con gráficos**: Mostrar resultados como gráficos además de tablas
- **Multi-idioma**: Soporte para respuestas en diferentes idiomas
- **Analytics del chat**: Métricas de uso del asistente analítico
- **Context awareness**: El chat podría recordar contexto de página actual (ej: métricas específicas)</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md