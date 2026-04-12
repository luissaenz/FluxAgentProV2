# Analisis Tecnico — Paso 2.3: Implementar componente `AgentPersonalityCard.tsx`

## 1. Diseno Funcional

### Happy Path
1. El usuario navega a la pagina de detalle de un agente (`/agents/{id}`).
2. Se renderiza la pagina con los datos basicos del agente obtenidos de `agent_catalog` (query directa a Supabase).
3. Simultaneamente, se dispara `useAgentDetail` que consulta `GET /agents/{id}/detail`, obteniendo el contrato enriquecido con `display_name`, `soul_narrative` y `avatar_url`.
4. Mientras carga, el componente muestra un skeleton con la forma de la tarjeta (avatar, nombre, rol, parrafos de narrativa).
5. Al recibir los datos, `AgentPersonalityCard` se renderiza dentro del tab "Informacion" mostrando:
   - Avatar con imagen personalizada (si `avatar_url` existe y carga correctamente) O fallback estetico con iniciales sobre gradiente violeta/indigo.
   - Badge del rol del agente.
   - Indicador "Identidad Verificada" con icono de usuario.
   - Narrativa de personalidad (`soul_narrative`) entre comillas, con estilo italic y `whitespace-pre-line` para respetar saltos de linea.
   - Si no hay narrativa, se muestra un mensaje default: *"Este agente opera bajo una directiva tecnica estandar sin narrativa de personalidad adicional."*

### Edge Cases Relevantes para MVP
| Escenario | Comportamiento |
|-----------|---------------|
| `avatar_url` es null o vacio | Se muestra fallback de iniciales con gradiente |
| La imagen del avatar falla al cargar (onError) | Se activa `avatarError` state y se muestra fallback |
| `soul_narrative` es null, vacio o solo whitespace | Se muestra el mensaje default en lugar de un bloque vacio |
| `display_name` es vacio o indefinido | Fallback a `agent.role` (ya resuelto en el padre antes de pasar props) |
| Agente sin metadata en `agent_metadata` | El backend ya resuelve esto con fallbacks; el componente recibe datos validos |

### Manejo de Errores (Que ve el usuario)
- **Error de red al cargar detalle:** El hook `useAgentDetail` no tiene manejo de error UI explicito; la pagina sigue mostrando los datos basicos de `agent_catalog`. El usuario ve el agente sin enriquecimiento de personalidad, pero la pagina no se rompe.
- **Error de avatar (imagen rota):** Silencioso — el componente hace fallback automatico al avatar de iniciales sin notificar al usuario.
- **Error general de la pagina:** Si ni siquiera `agent_catalog` carga, se muestra "Agente no encontrado".

### Ambiguedades Detectadas
1. **No hay reintentos automaticos en `useAgentDetail`:** Si la llamada al endpoint enriquecido falla, no se reintenta ni se muestra un estado de error al usuario. Los datos basicos siguen visibles, pero el usuario no sabe que falta informacion.
2. **El skeleton de carga no cubre toda la pagina:** Solo cubre el header y metricas rapidas en el padre; `AgentPersonalityCard` tiene su propio skeleton interno pero el padre ya renderiza un skeleton general antes de llegar aqui. Hay doble capa de skeleton innecesaria potencial.

---

## 2. Diseno Tecnico

### Componentes Involucrados

#### `AgentPersonalityCard` (`dashboard/components/agents/AgentPersonalityCard.tsx`)
- **Responsabilidad:** Presentar la identidad visual del agente (avatar, nombre, rol, narrativa).
- **Props (`AgentPersonalityCardProps`):**
  - `displayName: string` — Nombre publico del agente (puede ser el role como fallback).
  - `role: string` — Rol tecnico del agente (se muestra como badge).
  - `soulNarrative: string | null` — Narrativa de personalidad legible por humanos.
  - `avatarUrl: string | null` — URL de la imagen de avatar.
  - `isLoading: boolean` — Estado de carga del query de detalle enriquecido.
- **Estado interno:**
  - `avatarError: boolean` — Trackea si la imagen del avatar fallo para mostrar fallback.
- **Dependencias UI:** `Card`, `CardContent`, `Badge`, `Skeleton` (shadcn/ui), `Bot`, `User` (lucide-react).

#### Padre: `agents/[id]/page.tsx`
- Obtiene datos basicos via query directa a Supabase (`agent_catalog`).
- Obtiene datos enriquecidos via `useAgentDetail` (llama a `GET /agents/{id}/detail`).
- Resuelve `displayName` con fallback: `detail?.agent.display_name ?? agent.role`.
- Renderiza `AgentPersonalityCard` dentro del `TabsContent value="info"`.
- Tambien renderiza metricas rapidas, tab de tareas recientes, tab de credenciales, y accordion con el SOUL JSON crudo.

#### Hook: `useAgentDetail`
- **Query Key:** `['agent-detail', orgId, agentId]`
- **Endpoint:** `GET /agents/${agentId}/detail`
- **Auto-refresh:** Cada 15 segundos (`refetchInterval`).
- **Stale time:** 10 segundos.
- **Retorna:** `AgentDetail` con `{ agent, metrics, credentials }`.

### Modelos de Datos (Extensiones)
- La interfaz `Agent` en `lib/types.ts` ya incluye los campos enriquecidos:
  ```typescript
  display_name?: string
  soul_narrative?: string
  avatar_url?: string
  ```
- Estos son opcionales porque el backend aplica fallbacks cuando no existe registro en `agent_metadata`.

### Integracion con Backend
- El contrato de `GET /agents/{id}/detail` ya esta definido y funcional (Paso 2.2 completado).
- Realiza LEFT JOIN con `agent_metadata` e inyecta los campos enriquecidos en el objeto `agent`.
- No se requieren cambios en el backend para este paso.

### Version Duplicada No Utilizada
- Existe una segunda version de `AgentPersonalityCard` en `dashboard/components/shared/AgentPersonalityCard.tsx`.
- Esta version usa `EmptyState` en lugar de mensaje default, tiene styling mas simple (sin gradientes, sin badge de "Identidad Verificada"), y no esta importada en ningun archivo.
- **Decision:** Mantener solo la version de `components/agents/` que es la usada. La version `shared/` es un artifact de desarrollo que deberia eliminarse para evitar confusion.

---

## 3. Decisiones

| # | Decision | Justificacion |
|---|----------|--------------|
| D1 | **Priorizar datos basicos sobre enriquecidos** | Si `useAgentDetail` falla, la pagina sigue siendo funcional con los datos de `agent_catalog`. El usuario puede ver la configuracion tecnica del agente aunque no vea su personalidad. |
| D2 | **Mensaje default para narrativa vacia** | En lugar de mostrar un bloque vacio o un "EmptyState" generico, se muestra un mensaje explicativo que indica que el agente opera bajo directiva tecnica estandar. Esto da contexto al usuario en lugar de dejar un hueco visual. |
| D3 | **Fallback de avatar con iniciales sobre gradiente** | Solucion visualmente atractida que no requiere asset externo y da una identidad minima reconocible. El gradiente violeta/indigo se alinea con la estetica general del dashboard. |
| D4 | **`whitespace-pre-line` para la narrativa** | Permite que los saltos de linea en la narrativa se respeten sin necesidad de parsear markdown o HTML. Simple y efectivo para MVP. |
| D5 | **Estado `avatarError` silencioso** | No se muestra toast ni notificacion cuando el avatar falla porque no es informacion accionable para el usuario. El fallback visual es suficiente. |

---

## 4. Criterios de Aceptacion

| # | Criterio | Verificable |
|---|----------|-------------|
| C1 | El componente `AgentPersonalityCard` se renderiza dentro del tab "Informacion" de la pagina de detalle del agente | ✅ Si/No |
| C2 | Cuando `isLoading` es true, se muestra skeleton con forma de avatar, nombre y parrafos | ✅ Si/No |
| C3 | Si `avatar_url` es valido, se muestra la imagen del avatar; si es null, vacio o falla la carga, se muestra fallback con inicial del agente sobre gradiente | ✅ Si/No |
| C4 | Si `soul_narrative` tiene contenido, se muestra entre comillas con estilo italic y `whitespace-pre-line` | ✅ Si/No |
| C5 | Si `soul_narrative` es null/vacia, se muestra el mensaje default sobre directiva tecnica estandar | ✅ Si/No |
| C6 | El `displayName` muestra el valor enriquecido del backend o hace fallback al `role` del agente | ✅ Si/No |
| C7 | El badge del rol del agente se muestra con estilo secundario/primary visible | ✅ Si/No |
| C8 | El indicador "Identidad Verificada" se muestra junto al rol | ✅ Si/No |
| C9 | El componente no rompe la pagina si los datos enriquecidos fallan (los datos basicos siguen visibles) | ✅ Si/No |
| C10 | La pagina H1 se actualiza con el `displayName` del agente | ✅ Si/No |

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigacion |
|---|--------|---------|------------|
| R1 | **Duplicidad de componentes:** Existen dos versiones de `AgentPersonalityCard` (`agents/` y `shared/`). Un desarrollador podria importar la version incorrecta. | Medio — confusion en el equipo, inconsistencia visual. | Eliminar `dashboard/components/shared/AgentPersonalityCard.tsx` o consolidar en una sola version exportada desde un unico lugar. |
| R2 | **Sin reintento automatico en `useAgentDetail`:** Si la llamada falla por un timeout transitorio, el usuario nunca ve la narrativa hasta que hace refresh manual. | Bajo — los datos basicos siguen disponibles, pero la experiencia es incompleta. | Agregar `retry: 1` o `retry: 2` al query de TanStack Query para reintentos automaticos. |
| R3 | **El auto-refetch cada 15s es innecesario para datos de personalidad:** La narrativa y avatar de un agente no cambian frecuentemente. Esto genera llamadas innecesarias al backend. | Bajo — carga innecesaria en el servidor y consumo de datos del usuario. | Separar la query de metadata personal del agent-detail o aumentar `staleTime`/`refetchInterval` para este dato especifico. Actualmente `useAgentDetail` trae todo junto (agent, metrics, credentials). |
| R4 | **`whitespace-pre-line` puede causar desbordamiento visual** si la narrativa tiene lineas muy largas sin espacios. | Bajo — en practica la narrativa es texto natural con espacios. | Agregar `overflow-wrap: break-word` o `max-w-full` al parrafo como precaucion. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias | Notas |
|---|-------|-------------|--------------|-------|
| T1 | Verificar que `AgentPersonalityCard` se integra correctamente en el tab "Informacion" con datos del backend enriquecido | Baja | Paso 2.2 completado | Ya implementado y funcional. Validar visualmente. |
| T2 | Eliminar la version duplicada en `dashboard/components/shared/AgentPersonalityCard.tsx` | Baja | Ninguna | Limpieza de codigo muerto para evitar confusion. |
| T3 | Agregar `retry: 1` al query de `useAgentDetail` para tolerancia a fallos transitorios | Baja | Ninguna | Mejora de resiliencia sin cambios de contrato. |
| T4 | Agregar `overflow-wrap: break-word` al parrafo de narrativa para prevenir desbordamiento | Baja | Ninguna | Precaucion defensiva de CSS. |
| T5 | Verificar aislamiento multi-org: Agente A en Org 1 no ve metadata de Agente A en Org 2 | Media | Paso 2.5 | Esto depende de las politicas RLS en `agent_metadata` y del filtro por `org_id` en el backend. Validar con prueba directa. |
| T6 | Documentar en `estado-fase.md` que este paso esta completo y archivar el analisis | Baja | T1-T5 completados | Actualizar registro de fase. |

**Orden recomendado:** T1 → T2 → T3 → T4 → T5 → T6

**Estado actual del paso:** El componente ya esta implementado y funcional (T1). El trabajo restante es pulido y limpieza (T2-T6).

---

## 🔮 Roadmap (NO implementar ahora)

### Mejoras Post-MVP
1. **EmptyState visual para agentes sin personalidad:** En lugar del mensaje textual, usar un componente `EmptyState` con icono ilustrativo y un CTA para "Configurar personalidad del agente" cuando el sistema lo permita.
2. **Editor de narrativa inline:** Permitir que usuarios con permisos editen el `soul_narrative` directamente desde la UI, con preview en tiempo real.
3. **Avatar upload:** Integrar con Supabase Storage para permitir subir imagenes de avatar en lugar de solo URLs externas.
4. **Soporte de markdown en narrativa:** Si la narrativa necesita formato rico (negritas, listas, enlaces), integrar un renderizador de markdown ligero (ej. `react-markdown`).
5. **Separacion de queries:** Dividir `useAgentDetail` en `useAgentPersonality` (datos estaticos, sin refetch) y `useAgentMetrics` (datos dinamicos, con refetch) para optimizar llamadas al servidor.
6. **Skeleton unificado:** Eliminar el skeleton interno del componente y manejar toda la carga a nivel de pagina para evitar parpadeos entre skeletons padre e hijo.

### Decisiones de Diseño que No Bloquean el Futuro
- **Props interface extensible:** `AgentPersonalityCardProps` puede crecer con campos como `onEdit`, `permissions`, o `theme` sin requerir reescritura.
- **Separacion de concerns:** El componente es puramente presentacional; toda la logica de datos vive en el padre y los hooks. Esto facilita probar el componente en aislamiento y reutilizarlo en otros contextos.
- **Version `shared/` como seed para reutilizacion:** Si en el futuro se necesita mostrar personalidad de agentes en otras partes del dashboard (ej. selector de agentes, lista de agentes), la version `shared/` puede refinarse y usarse como componente base comun.
