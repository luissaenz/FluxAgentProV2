# 🧠 ANÁLISIS TÉCNICO: Paso 3.4 - Integración en Vista de Tarea (Live Transcript)

## 1. Diseño Funcional
El objetivo de este paso es integrar la capacidad de monitoreo en tiempo real (implementada en el Paso 3.3) dentro de la interfaz de usuario principal del dashboard, específicamente en la página de detalle de tarea.

### Happy Path
1. El usuario accede a una tarea desde la lista de tareas o mediante un enlace directo.
2. Si la tarea está en estado `running`, la página carga automáticamente la pestaña **"Live Transcript"**.
3. El usuario ve los pensamientos del agente y las salidas de las herramientas fluyendo en tiempo real sin recargar.
4. Si la tarea está en un estado terminal (`completed`, `failed`), la página carga por defecto la pestaña **"Información"**, pero el usuario puede navegar a "Transcript" para ver el historial completo.

### Edge Cases (MVP)
- **Tarea Completa:** El streaming no se activa si `is_running` es falso, pero se muestra el snapshot completo.
- **Desconexión:** Si el canal de Supabase falla, se muestra un banner de error (ya gestionado por `TranscriptTimeline`) y un botón para ver el transcript estático.
- **Cambio de Estado:** Cuando una tarea termina mientras el usuario está viendo el "Live Transcript", el badge de "En vivo" desaparece suavemente.

### Manejo de Errores
- Si falla la carga inicial del snapshot, se muestra un mensaje de error y opción de reintentar.
- Si el usuario no tiene permisos (RLS), el timeline aparecerá vacío o con un mensaje de acceso denegado.

---

## 2. Diseño Técnico

### Componentes y Estructura
Se transformará la página `dashboard/app/(app)/tasks/[id]/page.tsx` para utilizar un sistema de pestañas (`Tabs` de shadcn/ui).

**Estructura Propuesta:**
```tsx
<Tabs defaultValue={task.status === 'running' ? 'transcript' : 'info'}>
  <TabsList>
    <TabsTrigger value="info">Información</TabsTrigger>
    <TabsTrigger value="transcript">Live Transcript</TabsTrigger>
  </TabsList>
  
  <TabsContent value="info">
    {/* Contenido actual: Info Cards + Legacy EventTimeline */}
  </TabsContent>
  
  <TabsContent value="transcript">
    <TranscriptTimeline taskId={id} orgId={orgId} />
  </TabsContent>
</Tabs>
```

### Modificaciones en Archivos Existentes
- **`tasks/[id]/page.tsx`**:
  - Importar `Tabs, TabsContent, TabsList, TabsTrigger`.
  - Importar `TranscriptTimeline`.
  - Implementar lógica de `defaultValue` dinámica.
  - El enlace anterior de "Ver Transcript" (líneas 61-67) puede eliminarse o actualizarse para forzar la selección de la pestaña.

- **`dashboard/components/transcripts/TranscriptTimeline.tsx`**:
  - **Corrección Crítica:** Eliminar la duplicación de `ConnectionStatusBadge` (definido accidentalmente dos veces en el Paso 3.3).

### Modelos de Datos
No se requieren cambios en los modelos de datos. Se consumirán los contratos existentes:
- API: `GET /transcripts/{task_id}`
- Realtime: Canal `transcript-timeline:{task_id}`

---

## 3. Decisiones
1. **Tabs vs Grid:** Se prefiere el uso de pestañas sobre un layout de rejilla (grid) para maximizar el espacio vertical del Timeline, que es denso en información.
2. **Autoselección de Pestaña:** Se prioriza la transparencia operativa (`running` -> `transcript`) para cumplir con el objetivo de la Fase 3 de dar visibilidad inmediata al proceso de la IA.
3. **Mantenimiento de Legacy Timeline:** Se mantiene el `EventTimeline` original en la pestaña de Información ya que muestra eventos de sistema (`flow.created`, etc.) que no son parte del transcript de ejecución del agente.

---

## 4. Criterios de Aceptación
- [ ] La página `tasks/[id]/page.tsx` tiene dos pestañas: "Información" y "Live Transcript".
- [ ] Si la tarea tiene estado `running`, la pestaña activa al cargar es "Live Transcript".
- [ ] El componente `TranscriptTimeline` se renderiza correctamente dentro de su pestaña.
- [ ] El `TranscriptTimeline` recibe y muestra eventos en tiempo real (validado visualmente o vía hooks logs).
- [ ] Se eliminó la definición duplicada de `ConnectionStatusBadge` en `TranscriptTimeline.tsx`.
- [ ] Las animaciones de `framer-motion` del timeline funcionan sin errores de prop-types o layout.

---

## 5. Riesgos
- **Memoria por Suscripciones:** Si el usuario abre muchas pestañas de tareas `running`, la conexión con Supabase podría saturarse (límite de 200 concurrentes en free tier). *Mitigación:* Recomendado cerrar suscripciones si la página pierde foco (Roadmap).
- **Consistencia de Sequence:** Si el backend re-numera secuencias (poco probable), el frontend podría mostrar duplicados. *Mitigación:* La lógica de deduplicación por ID en `useTranscriptTimeline` protege contra esto.

---

## 6. Plan de Implementación
1. **Limpieza (Complejidad Baja):** Corregir la duplicación de componentes en `TranscriptTimeline.tsx`.
2. **Setup Shadcn (Complejidad Baja):** Asegurar que `tabs.tsx` está disponible (ya verificado).
3. **Refactor de Página (Complejidad Media):** Implementar el sistema de pestañas en `page.tsx` y conectar las props necesarias.
4. **Pulido Visual (Complejidad Baja):** Ajustar espaciados y asegurar que el `Live Badge` sea prominente.

---

## 🔮 Roadmap (NO implementar ahora)
- **Persistencia de Pestaña:** Guardar la pestaña seleccionada en el estado de la URL (`?tab=transcript`).
- **Exportación:** Botón para descargar el transcript completo en formato Markdown o PDF.
- **Sincronización de Audio:** Si se implementa TTS en el futuro, sincronizar la lectura con el scroll del timeline.
