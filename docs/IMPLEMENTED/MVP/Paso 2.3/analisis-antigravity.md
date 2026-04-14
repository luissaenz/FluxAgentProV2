# 🧠 ANÁLISIS TÉCNICO: PASO 2.3 - AGENT PERSONALITY CARD & EXPERIENCE (SOUL UI)

## 1. Diseño Funcional

Este paso tiene como objetivo transformar la ficha técnica del agente en una experiencia de "identidad digital". No se trata solo de mostrar datos, sino de proyectar la sofisticación y el propósito de cada entidad autónoma del sistema.

- **Happy Path:** Al visualizar el detalle de un agente, la parte superior de la pestaña "Información" presenta la `AgentPersonalityCard`. 
    - El usuario es recibido por un avatar estilizado con bordes suavizados (Squircle/Rounded-2xl).
    - El nombre público (`display_name`) domina la jerarquía visual, proyectando una identidad humana/profesional por encima del rol técnico.
    - La **Narrativa de Alma (`soul_narrative`)** se presenta en una tipografía elegante, posiblemente en itálica o con un estilo de "cita", transmitiendo la filosofía operativa del agente.
- **Estética "Wow" (Premium):** 
    - Uso de gradientes sutiles en el fondo de la tarjeta (`from-card to-muted/30`).
    - Micro-animaciones de entrada: Un suave `fade-in-up` de **Framer Motion** para simular que el agente se "materializa" al cargar.
    - Hover effects: Elevación sutil y cambio de opacidad en el gradiente de borde.
- **Edge Cases MVP:**
    - **Metadata Inexistente:** Si el backend no tiene registro en `agent_metadata`, la tarjeta debe autogenerar un fallback estético usando las iniciales del `role` y un gradiente de color único por agente.
    - **Avatar Roto:** Fallback inmediato al icono de `Bot` (lucide-react) o a las iniciales mencionadas.
- **Manejo de Errores:**
    - Fallback visual ante fallos de carga del detalle (Skeleton state unificado con el resto del dashboard).

---

## 2. Diseño Técnico

### Componentes y Estructura
- **`AgentPersonalityCard.tsx` (Nuevo):**
    - Componente atomizado en `dashboard/components/agents/`.
    - **Tecnologías:** Radix UI `Avatar` (para gestión de fallbacks), Framer Motion (para transiciones premium).
    - **Props:** 
        - `displayName`: string (fallback al role).
        - `role`: string (identificador técnico).
        - `soulNarrative`: string | null.
        - `avatarUrl`: string | null.
        - `isLoading`: boolean.

### Integración en Página
- **`dashboard/app/(app)/agents/[id]/page.tsx`:**
    - Sustitución de la cabecera actual por una composición que combine el `BackButton` con la nueva tarjeta.
    - La cabecera H1 de la página debe sincronizarse con el `displayName` de la tarjeta para mantener coherencia visual.

### Modelos de Datos (Frontend Types)
- Extensión de la interfaz `Agent` en `dashboard/lib/types.ts` (Referenciado en `docs/estado-fase.md` sección 3).
    - Se aseguran los campos `display_name`, `soul_narrative` y `avatar_url` como opcionales para evitar romper implementaciones actuales.

---

## 3. Decisiones

1. **Radix UI Avatar vs <img>:** Se elige Radix UI por su capacidad nativa de manejar el ciclo de vida del avatar (Loading -> Error -> Fallback) de forma declarativa y accesible.
2. **Framer Motion para "Personalidad":** Se decide incluir una animación de entrada `initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}`. Esto aleja el dashboard de una herramienta estática y lo acerca a una plataforma "inteligente" y viva.
3. **Squircle/Rounded-2xl UI:** Se abandona el círculo perfecto para el avatar por una estética más moderna y alineada con interfaces de alto nivel (tipo Apple/Modern SaaS).

---

## 4. Criterios de Aceptación

- [ ] El componente `AgentPersonalityCard` utiliza `framer-motion` para una transición de entrada fluida.
- [ ] El avatar muestra correctamente la imagen de `avatar_url` o, en su defecto, las iniciales del nombre con un fondo gradiente.
- [ ] El `display_name` se visualiza correctamente si existe; de lo contrario, muestra el `role` capitalizado.
- [ ] La narrativa de alma respeta saltos de línea y se muestra con un estilo tipográfico diferenciado (ej. `italic`, `text-muted-foreground`).
- [ ] El componente es totalmente responsivo (pasa de layout horizontal en desktop a vertical en mobile si es necesario).
- [ ] El estado `isLoading: true` renderiza Skeletons que mantienen las dimensiones exactas de la tarjeta final.

---

## 5. Riesgos

| Riesgo | Impacto | Estrategia de Mitigación |
|--------|---------|-------------------------|
| **Inconsistencia de Naming:** El backend podría devolver `display_name` vacío mientras el detail carga. | Medio | Implementar lógica de fallback robusta en el componente: `displayName ?? role`. |
| **Performance de Animaciones:** Exceso de Framer Motion en listas largas. | Bajo | La tarjeta solo vive en el detalle (una por vista), el impacto es despreciable. |
| **Contrato de Tipos:** Desconexión entre el JSON del backend y las interfaces TS. | Alto | Validación estricta en el hook `useAgentDetail` antes de pasar datos al componente. |

---

## 6. Plan

1. **Definición de Tipos (Baja):** Refinar `lib/types.ts` para asegurar que los nuevos campos de SOUL estén presentes y tipados correctamente.
2. **Construcción del Componente (Media):** Implementar `AgentPersonalityCard.tsx` integrando Radix UI Avatar y Framer Motion. Configurar gradientes y estilos tailwind.
3. **Integración en Detail Page (Media):** Inyectar el componente en `agents/[id]/page.tsx`, pasando las props desde el hook `useAgentDetail`.
4. **Validación de Fallbacks (Baja):** Probar con un agente sin metadata para asegurar que la UI "degrada gracilmente" a los valores técnicos básicos.

---

## 🔮 Roadmap (NO implementar ahora)

- **Editor de Identidad:** Modal para que el admin pueda subir un avatar o describir la "personalidad" del agente desde la propia tarjeta.
- **Dynamic Themes:** Cambiar el color del gradiente de la tarjeta basado en las capacidades/herramientas predominantes del agente (ej. azul para análisis, verde para ejecución, naranja para creatividad).
- **Status Indicator Vivo:** Pequeña animación de "pulsación" en el avatar cuando el agente tiene una tarea en ejecución activa.
