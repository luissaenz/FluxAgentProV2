# 🏛️ ANÁLISIS TÉCNICO DEFINITIVO: PASO 2.3 - AGENTPERSONALITYCARD.TSX

## 1. Resumen Ejecutivo
Este paso representa la transición visual del sistema de un motor de ejecución técnica a una plataforma de gestión de agentes con identidad. Se implementará el componente `AgentPersonalityCard.tsx` para presentar el "SOUL" (alma/personalidad) del agente de forma narrativa y atractiva, consumiendo los datos de identidad inyectados por el backend en el paso 2.2.

El componente se integrará en la pestaña "Información" del detalle del agente, priorizando la legibilidad humana sobre la definición técnica JSON, pero manteniendo esta última accesible para debugging.

## 2. Diseño Funcional Consolidado

### 2.1 Happy Path
1. El usuario navega al detalle de un agente.
2. En la pestaña **"Información"**, el usuario visualiza una tarjeta premium (`AgentPersonalityCard`) que contiene:
   - **Identidad Visual:** Avatar circular con la imagen del agente (o fallback inteligente).
   - **Identidad Nominal:** Muestra el `display_name` (ej: "Soporte Nivel 1") con mayor jerarquía que el `role` técnico.
   - **Narrativa (SOUL):** Un texto legible y estructurado que describe la personalidad y misión del agente.
3. El título de la página (H1) se actualiza dinámicamente para mostrar el `display_name` si existe, reforzando la identidad en toda la vista.

### 2.2 Edge Cases (MVP)
- **Metadata Inexistente:** Si `soul_narrative` es null o vacío, la tarjeta muestra un estado vacío elegante: *"Este agente opera bajo directivas técnicas puras. Configuración de personalidad pendiente."*
- **Fallo de Avatar:** Si el `avatar_url` es inválido o falla la carga, el componente realiza un fallback automático en cascada: Imagen → Iniciales del Nombre → Icono `Bot` genérico.
- **Narrativas Extensas:** Se permitirá el crecimiento vertical de la tarjeta (no truncar en detalle) para asegurar que el propósito del agente sea comunicado íntegramente.

### 2.3 Manejo de Errores
- **Carga (Loading):** Uso de `Skeleton` que mimetiza la forma de la tarjeta mientras el hook `useAgentDetail` está en estado `isLoading`.
- **Datos Incompletos:** Desestructuración con valores por defecto para asegurar que el componente nunca "crashee" la página.

## 3. Diseño Técnico Definitivo

### 3.1 Arquitectura de Componentes
- **Ruta:** `dashboard/components/agents/AgentPersonalityCard.tsx`
- **Dependencias:** Shadcn UI (Card, Avatar, Badge, Skeleton), Lucide React, Framer Motion.

### 3.2 Contrato de Interfaz (Props)
```typescript
interface AgentPersonalityCardProps {
  agent: Agent;
  isLoading?: boolean;
}
```

### 3.3 Extensión del Modelo de Datos (`dashboard/lib/types.ts`)
Es imperativo actualizar la interfaz `Agent` para reflejar el enriquecimiento del backend:
```typescript
export interface Agent {
  // ... campos existentes ...
  display_name?: string;    // Inyectado por backend (Paso 2.2)
  soul_narrative?: string;  // Inyectado por backend (Paso 2.2)
  avatar_url?: string;     // Inyectado por backend (Paso 2.2)
}
```

### 3.4 Integración en `agents/[id]/page.tsx`
- **Jerarquía en Tab "Información":**
  1. `AgentPersonalityCard` (Nueva - Foco Identidad).
  2. `Card` de Configuración Técnica (Existente - Foco Parámetros).
  3. `Accordion` de SOUL Definition JSON (Existente - Renombrado a "Definición Técnica (JSON)").
- **Actualización de Header:** El H1 de la página debe priorizar `agent.display_name`.

## 4. Decisiones Tecnológicas

| Decisión | Justificación |
|----------|----------------|
| **Mantener el Accordion JSON** | A diferencia de algunas propuestas de eliminación total, se decide mantenerlo al final de la página. En fase MVP/Desarrollo, el rastro técnico es vital para diagnóstico de prompts. |
| **Directorio `components/agents/`** | Centralizar componentes de dominio para escalabilidad futura (listas, editores de agentes, etc.). |
| **Framer Motion: Entrada Suave** | Implementar un fade-in con un ligero slide-up (0.3s) para dar una sensación de "sistema vivo" al cargar la personalidad. |
| **Fallback en Cascada para Avatar** | Uso de `Avatar` de Radix para manejar `AvatarImage` y `AvatarFallback` (Initials) coordinados. |

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] La tarjeta muestra el `display_name` como título principal de la sección.
- [ ] La `soul_narrative` es legible y respeta párrafos/saltos de línea.
- [ ] El avatar carga la URL proporcionada o muestra las iniciales/icono en su defecto.
- [ ] El título (H1) de la página se actualiza al cargar el detalle del agente.

### Técnicos
- [ ] El componente reside en `dashboard/components/agents/AgentPersonalityCard.tsx`.
- [ ] La interfaz `Agent` en `lib/types.ts` contiene los nuevos campos opcionales.
- [ ] No existen errores de consola por hidratación o tipos de datos nulos.
- [ ] El build de producción (`npm run build`) se completa sin errores.

### Robustez
- [ ] Si el endpoint de detalle falla, la página muestra el estado de error global existente.
- [ ] Si los campos de metadata son nulos (ej: agentes viejos), la UI muestra fallbacks amigables en español.

## 6. Plan de Implementación

1. **[Baja] Refactor de Tipos:** Actualizar `dashboard/lib/types.ts` con los nuevos campos de `Agent`.
2. **[Baja] Estructura:** Crear el directorio `dashboard/components/agents/`.
3. **[Media] Desarrollo:** Implementar `AgentPersonalityCard.tsx` con soporte para Loading Skeletons y animaciones.
4. **[Media] Integración:** Modificar `dashboard/app/(app)/agents/[id]/page.tsx` para inyectar la tarjeta y reordenar el contenido.
5. **[Baja] Clean Up:** Eliminar imports innecesarios y verificar coherencia visual.

## 7. Riesgos y Mitigaciones

- **Riesgo:** Inconsistencia entre el `role` del catálogo y el `agent_role` de la metadata.
  - **Mitigación:** El backend ya realiza el JOIN correcto; el frontend debe confiar en el objeto `agent` devuelto por el detalle enriquecido.
- **Riesgo:** Layout shift al cargar la narrativa después de la página base.
  - **Mitigación:** Asegurar que el Skeleton ocupe el espacio aproximado de la tarjeta final.

## 8. Testing Mínimo Viable
- **Test 1:** Agente con metadata completa → Verificar todos los campos visibles y H1 actualizado.
- **Test 2:** Agente sin metadata (Legacy) → Verificar fallbacks: display_name = Role Formateado, Narrative = Mensaje de "pendiente".
- **Test 3:** Error de Imagen → Poner una URL falsa en `avatar_url` y verificar que el fallback de iniciales/icono aparezca.

## 9. 🔮 Roadmap (NO implementar ahora)
- **Editor In-place:** Permitir editar nombre y narrativa directamente en la card.
- **Mood Indicators:** Cambios visuales en la card según el estado de las últimas tareas (ej: borde rojo si el agente falló sus últimos 3 tickets).
- **Markdown Rendering:** Soporte para formato rico (negritas, links) en la narrativa.
