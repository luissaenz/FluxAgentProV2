# 🧠 ANÁLISIS TÉCNICO: PASO 2.3 - IMPLEMENTAR AGENTPERSONALITYCARD.TSX

## 1. Diseño Funcional

Este paso transforma la visualización técnica del agente en una experiencia de "identidad". El objetivo es que el usuario perciba al agente no como un script, sino como una entidad con propósito y personalidad (SOUL).

- **Happy Path:** Al navegar al detalle de un agente, la sección principal de información muestra la `AgentPersonalityCard`. Esta tarjeta incluye:
    - **Avatar:** Imagen circular con bordes suavizados (glassmorphism). Fallback automático a icono de `Bot` si no hay URL.
    - **Nombre Público (`display_name`):** Título prominente que reemplaza el `role` técnico (ej: "Soporte Estratégico" en lugar de `agent-support`).
    - **Narrativa de Alma (`soul_narrative`):** Párrafo descriptivo que explica el comportamiento y la "filosofía" de ejecución del agente.
- **Micro-interacciones:** Hover effects que iluminan sutilmente el borde de la tarjeta y una animación de entrada (fade-in + slide-up) para enfatizar la carga de la "personalidad".
- **Edge Cases MVP:**
    - **Metadata Ausente:** Si el backend devuelve `null` en narrativa, se mostrará un texto elegante: *"Este agente opera bajo directivas técnicas puras. Definición narrativa pendiente."*
    - **Error de Imagen:** Uso de `AvatarFallback` de Radix para evitar espacios en blanco o iconos de "imagen rota".
- **Manejo de Errores:** Si `useAgentDetail` falla, la tarjeta muestra su propio estado de esqueleto (Skeleton) independiente de las métricas.

## 2. Diseño Técnico

### Componentes y Estructura
- **Nuevo Componente:** `AgentPersonalityCard.tsx`
    - **Ubicación:** `dashboard/components/agents/` (crear directorio).
    - **Props:** `agent: Agent`.
- **Modificación de Página:** `dashboard/app/(app)/agents/[id]/page.tsx`
    - Reemplazar el `Accordion` de "SOUL Definition" por la nueva tarjeta.
    - Mover el `CodeBlock` de `soul_json` a una sección secundaria de "Especificaciones Técnicas" o bajo un nuevo Tab de "Configuración Avanzada".

### Tipos de Datos (Refactor Obligatorio)
Se debe actualizar `dashboard/lib/types.ts`:
```typescript
export interface Agent {
  // ... campos existentes ...
  display_name?: string;    // Inyectado por backend
  soul_narrative?: string;  // Inyectado por backend
  avatar_url?: string;     // Inyectado por backend
}
```

### Estética Premium
- **Fondo:** `bg-card/50` con `backdrop-blur-md` (si el tema lo permite).
- **Borde:** Gradiente sutil `from-primary/20 to-secondary/20`.
- **Tipografía:** Título en `font-semibold`, narrativa con `leading-relaxed` y color `text-muted-foreground`.

## 3. Decisiones

1. **Uso de Radix UI Avatar:** Se elige sobre la etiqueta `<img>` nativa por su manejo avanzado de estados de carga y fallbacks integrados, crucial para una UI profesional.
2. **Framer Motion para el "Despertar":** Aplicar una animación de opacidad lenta al componente para reforzar la narrativa de que el agente es una entidad inteligente que se "carga" en el sistema.
3. **Preservar el SOUL JSON:** Aunque se oculte de la vista principal, el JSON original es vital para debugging. Se mantendrá accesible pero en un segundo plano visual.

## 4. Criterios de Aceptación (NUEVO)

- [ ] Las interfaces en `lib/types.ts` incluyen `display_name`, `soul_narrative` y `avatar_url` como opcionales.
- [ ] El componente `AgentPersonalityCard` renderiza el `display_name` como encabezado de la tarjeta.
- [ ] Si `avatar_url` es válido, la imagen se visualiza sin distorsión (object-cover).
- [ ] La narrativa utiliza un componente de texto que respeta el espaciado (whitespace-pre-wrap si es necesario).
- [ ] El dashboard no presenta errores de lint/typescript tras la integración.
- [ ] La página de detalle del agente carga correctamente incluso si el registro de metadata no existe (fallback al role técnico).

## 5. Riesgos

| Riesgo | Impacto | Estrategia de Mitigación |
|--------|---------|-------------------------|
| **Carga Lenta de Imágenes:** Avatares externos pueden ralentizar la percepción de velocidad. | Medio | Usar Skeleton local dentro de la tarjeta y pesos de imagen optimizados. |
| **Pérdida de Contexto Técnico:** Usuarios avanzados podrían extrañar ver el prompt crudo rápidamente. | Bajo | Mantener el `Accordion` técnico al pie del tab de información. |
| **Mismatch de Tipos:** El frontend podría fallar si el backend no envía los campos inyectados. | Alto | Definir valores por defecto en la desestructuración de props del componente. |

## 6. Plan de Implementación

1. **Infraestructura (Baja):** Crear el directorio `dashboard/components/agents` y actualizar `lib/types.ts`.
2. **Componente Soul (Media):** Implementar `AgentPersonalityCard.tsx` con Shadcn UI (Card, Avatar) y Framer Motion.
3. **Integración UI (Media):** Modificar `app/(app)/agents/[id]/page.tsx` para inyectar la tarjeta y reordenar la información técnica.
4. **Pulido (Baja):** Ajustar Skeletons y validación de fallbacks.

---

## 🔮 Roadmap (NO implementar ahora)

- **Editor de Personalidad:** Formulario in-place para que el usuario pueda editar el `display_name` y la `narrative` directamente desde el panel.
- **Generación de Avatares:** Integrar con una API de generación de imágenes (o el `generate_image` tool) para crear avatares únicos basados en el rol del agente.
- **Voces:** Extender la metadata para incluir IDs de voces de ElevenLabs/OpenAI para futura síntesis de voz en el chat.
