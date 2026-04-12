# 🏛️ ANÁLISIS TÉCNICO DEFINITIVO: Paso 3.4 - Integración de Live Transcript en Vista de Tarea

## 1. Resumen Ejecutivo
Este paso representa la culminación de la Fase 3, integrando la visibilidad de ejecución en tiempo real directamente en el flujo de trabajo del usuario. Se transformará la página de detalle de tarea para ofrecer una experiencia dual: una vista de **Información Estática** (auditoría y resultados) y una vista de **Live Transcript** (monitoreo activo).

El sistema utilizará un patrón de pestañas inteligentes que priorizan la visibilidad del proceso de IA cuando la tarea está en ejecución, permitiendo al usuario supervisar pensamientos y herramientas sin fricción.

---

## 2. Diseño Funcional Consolidado

### Happy Path
1. **Acceso:** El usuario abre el detalle de una tarea (`/tasks/{id}`).
2. **Inteligencia de Pestaña:**
   - Si `task.status === 'running'`, la pestaña **"Live Transcript"** se selecciona automáticamente.
   - Si la tarea ha finalizado (`completed`, `failed`), se selecciona por defecto la pestaña **"Información"**.
3. **Monitoreo en Vivo:** En la pestaña "Live Transcript", los eventos fluyen automáticamente con auto-scroll inteligente.
4. **Interacción:** El usuario puede alternar entre "Información" (detalles técnicos, inputs, resultados finales) y el "Transcript" sin perder la conexión en tiempo real.

### Edge Cases (MVP)
- **Re-ejecución:** Si una tarea finalizada se vuelve a ejecutar (p. ej. vía retry), el sistema detecta el cambio de estado y reactiva la suscripción en tiempo real.
- **Paginación Inversa:** El usuario puede cargar eventos antiguos del transcript mediante el botón "Cargar anteriores" (ya soportado por el componente).
- **Desconexión:** Al perder la conexión, se muestra un banner de error no intrusivo que permite reconexión manual mientras los eventos históricos permanecen visibles.

### Manejo de Errores
- **Error de Snapshot:** Si falla la carga inicial del historial, se muestra un estado de error en el contenedor de la pestaña con opción de reintentar.
- **Error de Realtime:** Badge visual cambia a rojo/desconectado y se ofrece botón de reconexión.

---

## 3. Diseño Técnico Definitivo

### Arquitectura de Componentes
Se implementará un sistema de pestañas utilizando el componente `Tabs` de `@/components/ui/tabs`.

**Estructura:**
```tsx
<Tabs defaultValue={initialTab} className="w-full">
  <TabsList>
    <TabsTrigger value="info">Información</TabsTrigger>
    <TabsTrigger value="transcript" className="gap-2">
      Live Transcript
      {task?.status === 'running' && <PulseBadge />}
    </TabsTrigger>
  </TabsList>
  
  <TabsContent value="info">
    <div className="grid lg:grid-cols-2 gap-6">
      <TaskInfoCard task={task} />
      <EventTimeline events={events} /> {/* Legacy Timeline para auditoría de sistema */}
    </div>
  </TabsContent>
  
  <TabsContent value="transcript" forceMount={false}>
    {/* Lazy mounting para evitar suscripciones innecesarias */}
    <TranscriptTimeline taskId={id} orgId={orgId} />
  </TabsContent>
</Tabs>
```

### Contratos e Integraciones
- **Snapshot Inicial:** `GET /transcripts/{task_id}` (vía `useTranscriptTimeline`).
- **Realtime:** Canal Supabase `transcript-timeline:{task_id}` con filtro por `aggregate_id`.
- **Deduplicación:** El frontend mantendrá la lógica de descarte de eventos con `sequence <= last_sequence` para un hand-off limpio del snapshot al stream.

### Modificaciones Requeridas
1. **`dashboard/app/(app)/tasks/[id]/page.tsx`**:
   - Refactorizar para envolver el contenido en `Tabs`.
   - Implementar `initialTab` basado en `task.status`.
   - Mapear correctamente `orgId` desde `useCurrentOrg`.
2. **`dashboard/components/transcripts/TranscriptTimeline.tsx`**:
   - **CRÍTICO:** Eliminar la definición duplicada de la función `ConnectionStatusBadge` al final del archivo.
   - Ajustar altura del `ScrollArea` para aprovechar el layout de pestaña.

---

## 4. Decisiones Tecnológicas
1. **Lazy Rendering de Transcript:** El componente de transcript solo se activará (y por tanto, conectará a Supabase) cuando la pestaña esté activa. Esto optimiza el uso de conexiones WebSocket.
2. **Coexistencia de Timelines:** Se mantienen ambos timelines. `EventTimeline` (existente) para eventos de ciclo de vida del flujo y `TranscriptTimeline` (nuevo) para el proceso detallado del agente.
3. **Sincronización de URL (Roadmap):** Se decide NO persistir la pestaña en la URL para el MVP para evitar complejidad innecesaria en el manejo de historial de navegación, pero se deja preparado el diseño para ello.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El usuario ve dos pestañas claramente diferenciadas en el detalle de la tarea.
- [ ] Al cargar una tarea en estado `running`, la pestaña "Live Transcript" es la activa por defecto.
- [ ] Al cargar una tarea finalizada, la pestaña "Información" es la activa por defecto.
- [ ] El cambio de pestañas es instantáneo y no provoca recargas de toda la página.
- [ ] El badge "LIVE" (pulsante) es visible en el trigger de la pestaña solo durante la ejecución.

### Técnicos
- [ ] Se eliminó el código duplicado en `TranscriptTimeline.tsx`.
- [ ] La suscripción a Supabase se cierra correctamente al navegar fuera de la página o cambiar a una pestaña que no renderiza el componente (verificar hook cleanup).
- [ ] No hay errores de consola relacionados con `framer-motion` o layouts rotos por el uso de `Tabs`.
- [ ] El componente `TranscriptTimeline` recibe el `orgId` correcto para el aislamiento multi-tenant.

### Robustez
- [ ] Si el socket de Supabase falla, el usuario puede seguir viendo el transcript cargado mediante el snapshot REST.
- [ ] El auto-scroll se detiene si el usuario sube manualmente en el historial de eventos.

---

## 6. Plan de Implementación

| Tarea | Descripción | Complejidad |
|-------|-------------|-------------|
| **1. Fix Técnico** | Eliminar duplicación en `TranscriptTimeline.tsx`. | Baja |
| **2. Estructura UI** | Implementar `Tabs` en `tasks/[id]/page.tsx`. | Media |
| **3. Lógica Condicional** | Implementar autoselección de pestaña y PulseBadge. | Baja |
| **4. Integración** | Conectar `TranscriptTimeline` con props dinámicas. | Baja |
| **5. Validación** | Test de ciclo de vida completo (Snapshot -> Realtime -> Finish). | Media |

---

## 7. Riesgos y Mitigaciones
- **Riesgo:** Alta carga de CPU si hay miles de eventos en el DOM.
- **Mitigación:** Se limita el snapshot inicial y se confía en el paginado del backend. La virtualización queda para el Roadmap.
- **Riesgo:** Confusión del usuario entre los dos timelines.
- **Mitigación:** Etiquetas claras: "Auditoría de Sistema" (Información) vs "Pensamiento del Agente" (Transcript).

---

## 8. Testing Mínimo Viable
1. Abrir tarea `running` -> Verificar que abre en pestaña "Transcript" con badge LIVE.
2. Abrir tarea `completed` -> Verificar que abre en pestaña "Información" con el legacy timeline visible.
3. Cambiar de pestaña -> Verificar que el contenido se actualiza correctamente.
4. Desconectar internet mientras se ve un transcript `running` -> Verificar banner de error.

---

## 🔮 Roadmap (NO implementar ahora)
- **Filtros de Eventos:** Segmentar el transcript por Agente / Herramienta.
- **Persistencia de URL:** `?tab=transcript` para compartir enlaces directos a la ejecución.
- **Exportación:** Botón "Generar Reporte" basado en el transcript acumulado.
