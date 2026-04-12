# Análisis Técnico - Paso 2.3: Implementar componente AgentPersonalityCard.tsx

## 1. Diseño Funcional

### Happy Path
- El usuario accede a la página de detalle de un agente específico (/agents/{id}).
- En la pestaña "Información", se muestra una tarjeta (`AgentPersonalityCard`) que presenta:
  - Nombre público del agente (display_name).
  - Descripción narrativa de la personalidad (soul_narrative), formateada como texto legible.
  - Avatar del agente (avatar_url), o iniciales como fallback.
- El encabezado H1 de la página se actualiza dinámicamente con el nombre público del agente.

### Edge Cases que Afectan al MVP
- Agente sin registro en `agent_metadata`: Mostrar nombre generado basado en el rol del agente (ej. "Agente Bartender"), narrativa genérica ("Este agente está diseñado para..."), y avatar con iniciales.
- Avatar con URL inválida: Fallback automático a iniciales estilizadas.
- Narrativa muy larga: Limitar visualmente a 300 caracteres con opción de "ver más" si excede.

### Manejo de Errores: Qué Ve el Usuario Cuando Algo Falla
- Si falla la carga de datos del agente: Mostrar mensaje "Cargando personalidad..." con skeleton loader.
- Si el endpoint falla: Mantener la página funcional con datos básicos del agente (sin personalidad enriquecida).

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones a Existentes
- **Nuevo componente:** `AgentPersonalityCard.tsx` en `dashboard/components/agents/`.
  - Props: Recibe `agent` (tipo `Agent` extendido con metadata).
  - Renderiza: Card con avatar, nombre y narrativa.
  - Fallbacks internos para datos faltantes.

- **Modificaciones:**
  - `agents/[id]/page.tsx`: Integrar `AgentPersonalityCard` en la pestaña "Información" (tabs).
  - Actualizar el componente de título (H1) para usar `agent.display_name` en lugar de `agent.role`.

### Interfaces (Inputs/Outputs de Cada Componente)
- `AgentPersonalityCard`:
  - Input: `agent: { display_name: string, soul_narrative: string, avatar_url?: string, role: string }`
  - Output: JSX.Element (tarjeta visual)

- `useAgentDetail` hook: Ya consume el contrato enriquecido del backend (`GET /agents/{id}/detail`).

### Modelos de Datos Nuevos o Extensiones
- Extensión del tipo `Agent` en `lib/types.ts`: Ya incluye `display_name`, `soul_narrative`, `avatar_url` (confirmado en estado-fase.md).

- Sin cambios a modelos de backend; usa `agent_metadata` existente.

### Integraciones
- **Backend:** Consume `GET /agents/{id}/detail` que realiza LEFT JOIN con `agent_metadata`.
- **UI Library:** Usar componentes de shadcn/ui (Card, Avatar) para consistencia visual.

**Coherencia con estado-fase.md:** Este diseño respeta el contrato de API definido (enriquecido con metadata) y las decisiones de fallbacks automáticos.

## 3. Decisiones

- **UI Framework:** Usar shadcn/ui Card y Avatar para mantener consistencia con el dashboard existente.
- **Fallbacks de Datos:** Generar display_name basado en role si falta metadata, para evitar roturas visuales.
- **Formato de Narrativa:** Renderizar soul_narrative como texto enriquecido (markdown básico) si contiene formato, o texto plano.
- **Avatar Handling:** Usar componente Avatar de shadcn con src opcional; fallback a iniciales generadas de display_name.
- **Actualización de H1:** En el layout de la página, usar useEffect para actualizar document.title y el H1 basado en agent.display_name.

Cada decisión se basa en la necesidad de enriquecer la identidad del agente sin romper la experiencia existente.

## 4. Criterios de Aceptación
Lista binaria (sí/no) de condiciones que deben cumplirse para considerar el paso COMPLETO:

- El componente AgentPersonalityCard se muestra correctamente en la pestaña "Información" del detalle del agente.
- La tarjeta muestra el display_name del agente como título principal.
- La soul_narrative se presenta como texto legible (no JSON crudo).
- El avatar se carga desde avatar_url, o muestra iniciales si falla.
- El H1 de la página se actualiza dinámicamente con el display_name del agente.
- Funciona correctamente cuando el agente no tiene metadata (fallbacks aplicados).
- No hay errores de consola relacionados con datos faltantes.

## 5. Riesgos

### Riesgos Concretos del Paso
- **Carga de Imagen de Avatar:** URL inválida podría causar errores 404 visibles. **Mitigación:** Implementar onError en img tag para fallback inmediato a iniciales.
- **Texto Largo en Narrativa:** Podría romper el layout si es excesivamente largo. **Mitigación:** Limitar visualmente a 3 líneas con ellipsis, añadir "ver más" expandable.
- **Dependencia de Metadata:** Si el backend no provee los campos, la UI podría quedar vacía. **Mitigación:** Fallbacks robustos en el componente y validación en TypeScript.
- **Consistencia Visual:** El avatar podría no escalar bien en móviles. **Mitigación:** Usar clases responsive de Tailwind.

Cada riesgo tiene estrategia de mitigación implementada en el componente.

## 6. Plan

### Tareas Atómicas Ordenadas
1. **Crear componente base AgentPersonalityCard.tsx** (Media): Implementar la estructura con Card, Avatar y texto. Incluir fallbacks.
2. **Implementar lógica de fallbacks** (Baja): Añadir generación de iniciales y nombre por rol.
3. **Integrar en página de detalle** (Media): Modificar agents/[id]/page.tsx para incluir el componente en tabs "Información".
4. **Actualizar H1 dinámicamente** (Baja): Usar useEffect para setear document.title y el H1 con display_name.
5. **Testing visual y responsive** (Media): Verificar en diferentes tamaños de pantalla y casos de datos faltantes.

### Estimación de Complejidad Relativa
- Baja: Lógica simple, cambios menores.
- Media: Integración con UI existente, manejo de estados.
- Alta: No aplica en este paso.

### Dependencias Explícitas Entre Tareas
- Tarea 2 depende de 1 (fallbacks dentro del componente).
- Tareas 3 y 4 dependen de 1 (componente creado).
- Tarea 5 depende de 3 y 4 (integración completa).

## 🔮 Roadmap (NO implementar ahora)
- **Animaciones de entrada:** Transiciones suaves al cargar la tarjeta para mejorar UX.
- **Edición inline:** Permitir al usuario editar la personalidad directamente desde la UI (requiere backend adicional).
- **Personalización avanzada:** Soporte para múltiples avatares o temas por agente.
- **Analytics de visualización:** Tracking de cuánto tiempo se ve la personalidad para métricas de engagement.

Estas mejoras se consideran para fases posteriores, asegurando que no bloqueen la implementación MVP de identidad narrativa.