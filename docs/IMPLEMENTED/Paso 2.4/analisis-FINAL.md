# 🏛️ ANÁLISIS TÉCNICO UNIFICADO: Paso 2.4 - Refactorización de Capacidades (Premium UI)

## 1. Resumen Ejecutivo
Este paso consolida la evolución del Panel de Agente 2.0 (Fase 2) mediante la transformación de la pestaña técnica de "Credenciales" en una interfaz de **Capacidades y Herramientas** de alto nivel. El objetivo es eliminar la fragmentación de información y elevar la calidad visual del MVP, permitiendo al usuario entender qué puede hacer un agente y qué requisitos tiene (aprobaciones, credenciales) de forma intuitiva.

Se resolverá la redundancia detectada entre la pestaña de "Información" (donde ya vive el nuevo `AgentToolsCard`) y la pestaña de "Credenciales en Vault" (cruda y redundante), unificando todo en una vista coherente y premium.

## 2. Diseño Funcional Consolidado

### Happy Path (User Journey)
1. El usuario accede al perfil de un Agente (`/agents/{id}`).
2. Se presenta una vista de **"Detalle"** (anteriormente "Información") que contiene:
   - **AgentPersonalityCard:** Identidad narrativa (SOUL).
   - **AgentToolsCard:** Grid premium con las capacidades del agente.
3. El usuario visualiza cada herramienta con:
   - Nombre legible de negocio (e.g., "Consultar Clima" en lugar de `get_weather`).
   - Descripción narrativa del impacto y función.
   - Badges visuales inteligentes: **Aprobación Requerida** (Amber), **Credencial Configurada** (Blue), **Reloj de Timeout**.
4. Al entrar en el tab, los elementos aparecen con una animación **staggered** (escalonada) que refuerza la sensación de sistema vivo y profesional.

### Edge Cases (MVP)
- **Herramienta no mapeada:** Si la herramienta existe en el backend pero no en el `tool-registry-metadata.ts`, se aplica un fallback automático: `snake_case` -> `Title Case` y descripción genérica "Capacidad operativa estándar".
- **Credencial Faltante:** Si una herramienta requiere credencial pero no está en el `Vault` (según respuesta del backend), se omite el badge de credencial y la descripción asociada, manteniendo la tarjeta limpia.
- **Exceso de Tags:** Si una herramienta tiene más de 3 tags en metadata, se muestran los 3 primeros y un contador `+N`.

### Manejo de Errores
- **Fallos de Carga:** Uso de Skeletons que respetan la estructura de grid (2 columnas) para evitar saltos de layout (CLS).
- **Metadata Corrupta:** El componente `AgentToolsCard` utiliza `try/catch` interno o validación de tipos para asegurar que una entrada malformada no tire toda la página.

## 3. Diseño Técnico Definitivo

### Estructura de Componentes
- **`AgentToolsCard.tsx` (Consolidado)**: 
  - Ubicación: `dashboard/components/agents/`.
  - Lógica: Agrupación por primer tag (`category`) y mapeo contra el registry.
  - Animación: `framer-motion` para la entrada y transición de estados.
- **`AgentDetailPage.tsx` (Refactor)**:
  - Eliminar `<TabsTrigger value="credentials">` y su contenido.
  - Renombrar pestaña "Información" a "Detalle" o "Overview".
  - Asegurar que `AgentToolsCard` recibe las props correctas: `allowedTools={agent.allowed_tools}` y `credentials={credentials}`.

### Contrato de Metadata (`lib/tool-registry-metadata.ts`)
```typescript
export interface ToolMetadata {
  displayName: string;
  description: string;
  category: string; // Derivado del primer tag
  tags?: string[];
  requiresApproval?: boolean;
  timeoutSeconds?: number;
}
```

### Integración con Backend
Se utiliza el contrato existente de `GET /agents/{id}/detail`. No se requieren cambios en la API ni en el esquema de base de datos, ya que el Paso 2.2 ya resolvió el enriquecimiento de los datos necesarios (`allowed_tools` y `credentials`).

## 4. Decisiones Tecnológicas

- **Unificación de Vistas (Architectural Choice):** Se elimina el tab "Credenciales en Vault" por ser redundante. La información de credenciales es un atributo de la herramienta para el usuario, no una entidad separada.
- **Framer Motion for Staggered Animation:** Uso obligatorio para cumplir con el estándar "Premium UI" definido en la Fase 2.
- **Static Registry (Frontend):** Se mantiene el mapa de metadata en el frontend para este paso. 
  - *Justificación:* El dominio actual (Bartenders) es conocido y estático. Moverlo al backend añadiría complejidad innecesaria al MVP sin valor inmediato.
- **Radix UI + Shadcn:** Base para badges y cards, asegurando consistencia con el resto del sistema.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] La pestaña "Credenciales en Vault" ya **no es visible** en la UI.
- [ ] La pestaña principal de detalle muestra tanto la personalidad (SOUL) como las herramientas.
- [ ] Las herramientas muestran nombres en lenguaje natural (mapeados) y no nombres técnicos (snake_case).
- [ ] El badge de "Credencial" solo aparece si la herramienta está en el array de credenciales devuelto por el backend.
- [ ] El usuario visualiza la descripción de la credencial inline si está disponible.

### Técnicos
- [ ] El código de la pestaña eliminada en `agents/[id]/page.tsx` ha sido removido completamente (sin dejar dead code).
- [ ] Se integra `framer-motion` en `AgentToolsCard` con animaciones de entrada.
- [ ] `lib/tool-registry-metadata.ts` contiene al menos las 8 herramientas del dominio Bartenders.
- [ ] La persistencia de `notes` de tickets se mantiene funcional tras el refactor.

### Robustez
- [ ] Si se añade una herramienta nueva al backend sin actualizar el frontend, la UI muestra un fallback legible y no rompe el renderizado.
- [ ] Los Skeletons de carga coinciden visualmente con la estructura final del grid (1 col mobile, 2 cols desktop).

## 6. Plan de Implementación

| Tarea | Descripción | Complejidad |
|---|---|---|
| **T1: Cleanup** | Eliminar Tab de Credenciales y dead code en `agents/[id]/page.tsx`. | Baja |
| **T2: Integration UI** | Refinar `AgentToolsCard` para asegurar que consume correctamente el array de `credentials` para los badges. | Baja |
| **T3: Animations** | Aplicar efectos de entrada (stagger) con Framer Motion. | Media |
| **T4: Quality Check** | Verificar alineación de los 8 mapeos de herramientas Bartenders. | Baja |

## 7. Riesgos y Mitigaciones
- **Desincronización de Metadata:** El frontend puede no conocer una herramienta nueva. 
  - *Mitigación:* El helper de fallback garantiza legibilidad mínima siempre.
- **Confusión de Usuario por eliminación de Tab:** 
  - *Mitigación:* Los badges azules de "Credencial" en las herramientas son suficientemente explícitos para indicar que el requisito está cumplido.

## 8. Testing Mínimo Viable
1. **Test Visual:** Abrir agente con 5 herramientas y verificar que aparecen una tras otra.
2. **Test de Credenciales:** Verificar que una herramienta que requiere credencial muestra el badge solo si el agente la tiene en el Vault.
3. **Test de Fallback:** "Ocultar" temporalmente una herramienta del registry y verificar que se formatea correctamente en la UI.

## 9. 🔮 Roadmap (Post-MVP)
- **Metadata Dinámica:** Mover el `tool-registry` al backend para actualizaciones sin deploy.
- **Sandbox Mode:** Botón para disparar una ejecución de prueba directamente desde la tarjeta de herramienta.
- **Analytics de Herramientas:** Mostrar cuántas veces ha sido usada cada herramienta por ese agente.
