# Análisis Técnico - Paso 2.3: Implementar componente AgentPersonalityCard.tsx

## 1. Diseño Funcional

### Happy Path
El usuario accede a la página de detalle de un agente y en la pestaña "Información" ve una tarjeta visual atractiva que muestra:
- Avatar del agente (imagen circular)
- Nombre de display amigable (ej: "Asistente de Ventas" en lugar de "sales_assistant")
- Descripción narrativa de la personalidad del agente en texto legible, no JSON crudo

El flujo completo: Usuario → Página de agentes → Seleccionar agente → Ver pestaña "Información" → Tarjeta de personalidad visible inmediatamente, sin necesidad de expandir accordions.

### Edge Cases Relevantes para MVP
- **Agente sin metadata:** Mostrar fallback con el role del agente como nombre y descripción genérica ("Agente especializado en [role]")
- **Avatar faltante:** Mostrar icono de bot por defecto
- **Navegación móvil:** La tarjeta mantiene legibilidad en pantallas pequeñas (320px+)
- **Texto largo en narrativa:** Truncar a 200 caracteres con opción de "ver más"

### Manejo de Errores
- **Carga fallida del detalle:** Mostrar spinner durante carga, mensaje de error si falla completamente
- **Imagen de avatar rota:** Fallback automático a icono de bot sin romper el layout
- **Usuario sin permisos:** No aplica (ya manejado en rutas protegidas)

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **AgentPersonalityCard.tsx:** Componente principal que recibe `agent` (con campos enriquecidos) y renderiza la tarjeta visual
- **Modificación de AgentDetailPage:** Reemplazar el accordion "SOUL Definition" por el nuevo componente AgentPersonalityCard
- **Actualización de tipos:** Extender interfaz `Agent` para incluir `display_name`, `soul_narrative`, `avatar_url` (string | null)

### Interfaces (Inputs/Outputs)
**AgentPersonalityCard props:**
- `agent: Agent` (con campos enriquecidos)
- `isLoading?: boolean`

**AgentPersonalityCard output:**
- JSX.Element renderizado con Card de shadcn/ui
- Estructura: Avatar + Nombre + Narrativa + Badge de estado

### Modelos de Datos Nuevos o Extensiones
Extensión de interfaz `Agent` en `lib/types.ts`:
```typescript
export interface Agent {
  // ... campos existentes
  display_name?: string | null
  soul_narrative?: string | null
  avatar_url?: string | null
}
```

Coherente con contrato backend: `GET /agents/{id}/detail` retorna `{ agent: { ..., display_name, soul_narrative, avatar_url }, ... }`

### APIs/Endpoints
Sin cambios requeridos - usa endpoint existente `GET /agents/{id}/detail` ya enriquecido en paso 2.2.

## 3. Decisiones

Sin decisiones nuevas - implementación directa del contrato técnico establecido en estado-fase.md.

## 4. Criterios de Aceptación

- La tarjeta AgentPersonalityCard se muestra en la pestaña "Información" del detalle de agente
- Se visualiza avatar (o fallback), display_name y soul_narrative en formato legible
- El accordion "SOUL Definition (Prompt)" ya no es visible por defecto
- Al hacer hover sobre la narrativa se muestra tooltip con texto completo si está truncado
- En agentes sin metadata se muestra fallback amigable sin errores
- El componente responde correctamente en viewport móvil (sm: 640px, xs: 320px)
- No se muestran datos sensibles ni JSON crudo en la vista principal

## 5. Riesgos

### Riesgos Concretos del Paso
- **Riesgo de ruptura visual:** Avatar URL podría ser inválida causando layout shift - *Mitigación:* Validar URL y fallback inmediato a icono
- **Riesgo de performance:** Carga de imagen de avatar bloquea render - *Mitigación:* Lazy loading con Suspense y skeleton
- **Riesgo de truncado excesivo:** Narrativa muy corta no comunica personalidad - *Mitigación:* Definir límite mínimo de caracteres en validación
- **Riesgo de inconsistencia:** Backend podría no tener todos los agentes con metadata - *Mitigación:* Fallbacks robustos en componente

### Estrategias de Mitigación
- Implementar logging de errores de carga de avatar para monitoreo
- Añadir tests visuales con Storybook para diferentes estados
- Validar contrato en desarrollo con MSW mocks

## 6. Plan

### Tareas Atómicas Ordenadas
1. **Actualizar tipos (Baja):** Extender interfaz `Agent` con campos `display_name`, `soul_narrative`, `avatar_url`
2. **Crear componente base (Media):** Implementar `AgentPersonalityCard.tsx` con layout básico y fallbacks
3. **Añadir interactividad (Baja):** Implementar truncado de narrativa con "ver más" y tooltip
4. **Responsive design (Baja):** Asegurar legibilidad en móvil y tablet
5. **Integrar en AgentDetailPage (Media):** Reemplazar accordion por nuevo componente
6. **Testing visual (Baja):** Verificar renders en diferentes estados (con/sin metadata)

### Dependencias Explícitas
- Tarea 1 debe completarse antes de tarea 2
- Tarea 2 debe completarse antes de tarea 5
- Tareas 3 y 4 pueden paralelizarse con tarea 5

## 🔮 Roadmap (NO implementar ahora)

### Optimizaciones Futuras
- **Personalización visual:** Temas de color por tipo de agente (ventas = verde, soporte = azul)
- **Animaciones:** Transiciones suaves al cargar metadata
- **Cache de avatares:** Service worker para offline de imágenes
- **Narrativas dinámicas:** Actualización en tiempo real si metadata cambia

### Mejoras de UX
- **Editar personalidad:** Modal para actualizar display_name y narrativa desde frontend
- **Galería de avatares:** Selector predefinido de imágenes para agentes
- **Preview de cambios:** Vista previa antes de guardar modificaciones

### Decisiones de Diseño que No Bloquean
- Mantener JSON crudo accesible vía developer mode (localStorage flag)
- Soporte para múltiples idiomas en narrativas (i18n ready)
- Integración con sistema de themes para avatares adaptativos

---

**Análisis completado por agente kilo - Paso 2.3 Fase 2**