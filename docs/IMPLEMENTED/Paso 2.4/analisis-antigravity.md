# 🧠 ANÁLISIS TÉCNICO: Paso 2.4 - Refactor Tab de Herramientas (Premium UI)

Este análisis se centra en la transformación de la pestaña de "Credenciales" en una vista de "Capacidades y Herramientas" de alto nivel, utilizando metadata descriptiva y animaciones premium para mejorar la experiencia del usuario (Fase 2 MVP).

## 1. Diseño Funcional

### Happy Path
1. El usuario accede al perfil de un Agente y hace clic en la pestaña **"Herramientas"** (anteriormente "Credenciales").
2. La UI realiza una transición suave donde las herramientas aparecen secuencialmente (animación staggered).
3. Cada herramienta se muestra como una tarjeta dedicada que traduce el lenguaje técnico a lenguaje de negocio:
   - Ejemplo: `reservar_stock_evento` → **"Reservar Stock para Evento"**.
   - Se muestra una descripción clara del impacto (e.g., "Reserva el stock físico necesario...").
4. El usuario puede identificar rápidamente qué herramientas requieren aprobación humana o credenciales externas mediante badges visuales.

### Edge Cases (MVP)
- **Herramienta no registrada:** Si una herramienta existe en `allowed_tools` pero no en `tool-registry-metadata.ts`, el sistema formatea el nombre técnico (snake_case a Title Case) y muestra un estado de "Descripción pendiente".
- **Falta de credenciales:** Si una herramienta marcada como "Requiere Credencial" no tiene una credencial configurada en el Vault, se muestra un indicador de advertencia (Warning).

### Manejo de Errores
- Si falla la carga de detalles del agente, el componente `AgentToolsCard` muestra skeletons coherentes con la estructura de grid planeada.
- Si la metadata del registro está corrupta, se usa un objeto de fallback seguro para evitar crash de la UI.

---

## 2. Diseño Técnico

### Modificaciones a Componentes
- **`AgentDetailPage.tsx`**: 
  - Renombrar pestaña "Credenciales" a "Herramientas".
  - Mover `AgentToolsCard` de la pestaña "Información" a la pestaña "Herramientas".
- **`AgentToolsCard.tsx`**:
  - Implementación de **Framer Motion** para animaciones de entrada.
  - Mejora de la lógica de agrupación (por categorías derivadas de tags).
  - Integración de `AnimatePresence` para cambios de estado (si aplica).

### Interfaces y Modelos
```typescript
// En lib/tool-registry-metadata.ts
export interface ToolMetadata {
  displayName: string;
  description: string;
  tags?: string[];
  requiresApproval?: boolean;
  timeoutSeconds?: number;
  icon?: string; // Nombre del icono de Lucide (Roadmap)
}
```

### Integración de Datos
El componente consumirá las `credentials` del endpoint `get_agent_detail` para vincularlas directamente con las tarjetas de herramientas en la UI, eliminando la necesidad de una lista de credenciales separada y cruda.

---

## 3. Decisiones

1. **Unificación de Vistas (Herramientas + Credenciales)**: Se decide consolidar ambos conceptos en una sola interfaz. 
   - *Justificación*: Para el usuario, una credencial no es más que un requisito para usar una herramienta. Verlas juntas reduce la carga cognitiva.
2. **Interacciones con Framer Motion**: Uso de `initial={{ opacity: 0, y: 10 }}` y `animate={{ opacity: 1, y: 0 }}` con `staggerChildren: 0.05`.
   - *Justificación*: Eleva la percepción de calidad del "Panel de Agente 2.0" cumpliendo con el estándar premium definido en `estado-fase.md`.
3. **Hover States Dinámicos**: Bordes que cambian de color sutilmente según la categoría de la herramienta.
   - *Justificación*: Facilita la distinción visual entre herramientas de inventario, clima o utilidades.

---

## 4. Criterios de Aceptación (Definición de Hecho)

- [ ] La pestaña "Herramientas" es la fuente única de verdad para capacidades y requisitos del agente en la UI.
- [ ] Las tarjetas de herramientas aparecen con animación escalonada al montar el componente.
- [ ] Los nombres técnicos (snake_case) no son visibles para el usuario a menos que el mapping falle.
- [ ] El componente utiliza `Badge` de Shadcn con variantes de color (amber para aprobación, blue para credenciales).
- [ ] Se incluye un estado de "Empty State" elegante con un icono de `Wrench` si el agente no tiene herramientas.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Inconsistencia de nombres | Medio | El helper `formatToolName` garantiza que incluso sin metadata, el nombre sea legible. |
| Performance en listas largas | Bajo | El grid responsivo y las animaciones ligeras de Framer Motion mantienen la fluidez. |
| Duplicidad de componentes | Bajo | Se ha verificado que solo existe un `AgentToolsCard` en la ruta estándar. |

---

## 6. Plan de Implementación

1. **Tarea 1 (Limpieza)**: Refactorizar `AgentDetailPage.tsx` para mover y renombrar la sección de herramientas. [Dificultad: Baja]
2. **Tarea 2 (Animaciones)**: Integrar `framer-motion` en `AgentToolsCard` y sus sub-componentes. [Dificultad: Media]
3. **Tarea 3 (UX Refinement)**: Mejorar el layout de las tarjetas para que la información de credenciales se sienta integrada y no un "parche" (use of muted colors/icons). [Dificultad: Media]
4. **Tarea 4 (Validación)**: Pruebas con agentes con/sin herramientas y con/sin credenciales para asegurar robustez. [Dificultad: Baja]

---

## 🔮 Roadmap (No implementar ahora)

- **Acciones Rápidas**: Botón para "Probar Herramienta" directamente desde la tarjeta (Sandbox).
- **Iconos Personalizados**: Mapping de iconos específicos para cada herramienta del dominio.
- **Tooltips Detallados**: Información técnica adicional (schemas de input/output) visible al hacer hover prolongado o clic.
- **Filtros**: Buscador y filtros por categoría si el número de herramientas crece sustancialmente.
