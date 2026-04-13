# 🧠 ANÁLISIS TÉCNICO: PASO 1.5 - PRUEBA E2E CICLO DE VIDA (TICKETS)

## 1. Diseño Funcional
- **Objetivo**: Validar que la infraestructura de Tickets y Trazabilidad (Fase 1) funciona como un sistema cohesionado de extremo a extremo.
- **Flujo de Prueba (Happy Path)**:
    1. **Creación**: El usuario crea un ticket con un `flow_type` específico (ej. `generic_flow`).
    2. **Ejecución**: Se dispara la ejecución desde la UI. Se debe observar el spinner y el pulso de la fila.
    3. **Procesamiento**: El backend debe instanciar el Flow, propagar el `correlation_id` y generar eventos.
    4. **Finalización**: El ticket debe transicionar a `done` automáticamente.
    5. **Verificación**: El usuario debe poder hacer clic en el `task_id` vinculado y ver el registro de la tarea.
- **Escenario de Error (Hardening Path)**:
    1. Se ejecuta un ticket cuyo Flow está configurado deliberadamente para fallar.
    2. El ticket debe transicionar a `blocked`.
    3. El campo `notes` del ticket debe contener el timestamp del error, el tipo de excepción y el `correlation_id` para debugging.

## 2. Diseño Técnico
- **Alcance de la Validación**:
    - **Capa UI**: Re-renderizado reactivo y Toasts de éxito/error.
    - **Capa API**: Persistencia del vínculo `ticket_id <-> task_id`.
    - **Capa Motor (Core)**: Propagación del `correlation_id` en `BaseFlow` y `EventStore`.
- **Puntos de Verificación en Base de Datos**:
    - Query: `SELECT correlation_id FROM tasks WHERE id = '{task_id}'` → Debe ser `ticket-{ticket_id}`.
    - Query: `SELECT count(*) FROM domain_events WHERE correlation_id = 'ticket-{ticket_id}'` → Debe ser > 0.
- **Interfaces a Probar**:
    - `POST /tickets/{id}/execute`
    - `GET /tickets/{id}` (verificación de notas y status)

## 3. Decisiones
- **Evidencia Técnica**: No basta con la confirmación visual en UI. Para este paso, se considera obligatorio verificar la trazabilidad en el `EventStore` mediante logs o query directa a Supabase.
- **Criterio de "Done"**: Un ticket solo se considera exitoso si tiene un `task_id` no nulo en DB y un estado final consistente.

## 4. Criterios de Aceptación
1. **Vinculación**: ¿El `task_id` generado por el Flow se guarda correctamente en la columna `task_id` del ticket? [ ]
2. **Ciclo de Vida**: ¿El ticket cambia de `backlog` -> `in_progress` -> `done` (o `blocked`) sin intervención manual? [ ]
3. **Trazabilidad DB**: ¿El `correlation_id` en la tabla `tasks` coincide con el formato `ticket-{id}`? [ ]
4. **Persistencia de Errores**: En caso de fallo, ¿se preservan las notas previas y se añade la nueva traza de error? [ ]
5. **Navegación**: ¿El link al `task_id` en el Dashboard redirige a la vista de tarea correcta? [ ]

## 5. Riesgos
- **Latencia de Flow**: Flows muy largos pueden hacer que el usuario cierre la pestaña.
    - *Mitigación*: Se verifica que el proceso continúa en background y se refleja al volver a entrar (invalidación de caché).
- **Falsos Positivos**: Un ticket que marca `done` en UI pero no vinculó la tarea en DB.
    - *Mitigación*: Validación estricta de la respuesta del endpoint `/execute`.

## 6. Plan
1. **Tarea 1**: Configurar un Flow de prueba simple en el `flow_registry`. (Complejidad: Baja)
2. **Tarea 2**: Ejecución manual documentada del ciclo completo (Pantallazos/Logs). (Complejidad: Baja)
3. **Tarea 3**: Inspección de la tabla `domain_events` para asegurar que el `correlation_id` fluyó correctamente. (Complejidad: Baja)
4. **Tarea 4**: Generación del reporte de validación final de la Fase 1. (Complejidad: Baja)

### 🔮 Roadmap (NO implementar ahora)
- **Automated Smoke Test**: Crear un script de Playwright que realice este ciclo automáticamente en cada despliegue.
- **History Logs**: Una pestaña de "Historial de Ejecuciones" dentro del detalle del ticket para ver ejecuciones pasadas (actualmente solo se guarda la última exitosa en el campo `task_id`).
