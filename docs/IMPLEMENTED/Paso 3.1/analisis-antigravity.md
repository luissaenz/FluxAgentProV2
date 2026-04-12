# 🧠 Análisis Técnico: Paso 3.1 - Supabase Realtime [Antigravity]

## 1. Diseño Funcional
El objetivo es permitir que el Frontend reciba notificaciones instantáneas cada vez que se registra un nuevo hito en la ejecución de una tarea (pensamientos del agente, llamadas a herramientas, cambios de estado).

### Flujo Happy Path
1. El backend (CrewAI/Python) inserta un registro en la tabla `domain_events` con un `correlation_id` específico (ej. `ticket-123`).
2. Supabase detecta la inserción y la publica en el canal de Realtime.
3. El frontend, suscrito al canal con un filtro por `correlation_id`, recibe el payload del evento en milisegundos.
4. El componente `TranscriptTimeline` actualiza la UI sin intervención del usuario.

### Edge Cases (MVP)
- **Desconexión del Socket:** El cliente debe ser capaz de reconectarse. Se asume que el Paso 3.2 (Snapshot inicial) cubrirá los eventos perdidos durante la desconexión.
- **Volumen de Eventos:** Durante ejecuciones intensas, pueden generarse muchos eventos. El habilitar Realtime a nivel de tabla es eficiente, pero el cliente debe filtrar proactivamente.

---

## 2. Diseño Técnico

### Configuración de Base de Datos
Para que una tabla sea "escuchable" por el cliente de Supabase, debe pertenecer a la publicación `supabase_realtime`.

**Acciones SQL:**
```sql
-- Incluir la tabla en la publicación de Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;

-- Opcional: Asegurar que se envíen todos los datos en actualizaciones (aunque usamos principalmente INSERT)
ALTER TABLE domain_events REPLICA IDENTITY FULL;
```

### Seguridad y Aislamiento (Multi-tenant)
Supabase Realtime (v2+) respeta las políticas de **Row Level Security (RLS)**. 
- Dado que `domain_events` ya tiene RLS habilitado (en `001_set_config_rpc.sql` y corregido en `002_governance.sql`), un usuario autenticado solo recibirá eventos cuyo `org_id` coincida con su sesión.
- **Verificación Crítica:** La suscripción desde el frontend debe usar el JWT del usuario para que Supabase aplique el RLS correctamente.

### Payload del Evento
El streaming enviará el objeto completo de `domain_events`. Campos clave para el transcript:
- `event_type`: (ej. `agent_thought`, `tool_call`, `status_change`).
- `payload`: El contenido JSON con el texto o resultado.
- `correlation_id`: Para filtrar los eventos pertenecientes a una tarea específica.

---

## 3. Decisiones
1. **Uso de Publicación Existente:** Se utilizará la publicación estándar `supabase_realtime` en lugar de crear una nueva, para seguir las convenciones de Supabase y simplificar la configuración del cliente.
2. **Replica Identity FULL:** Se establece por defecto para evitar problemas futuros si se decide actualizar eventos (ej. corregir un error en un log previo), asegurando que el cliente reciba siempre el "antes" y "después" completo si fuera necesario.

---

## 4. Criterios de Aceptación
- [ ] La tabla `domain_events` está presente en `SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';`.
- [ ] Un cliente (JS/Python) puede suscribirse exitosamente al canal `realtime:public:domain_events`.
- [ ] Al insertar un registro manualmente en `domain_events`, el suscriptor recibe el payload completo en < 500ms.
- [ ] **Seguridad:** Un suscriptor con un JWT de la Org A **no** recibe eventos insertados para la Org B.

---

## 5. Riesgos
- **Riesgo:** Fuga de eventos si el JWT no se gestiona correctamente en el subscripción. 
  - *Mitigación:* Forzar el uso de `supabase-auth-helpers` en el frontend y validar RLS en los tests de este paso.
- **Riesgo:** Sobrecarga del navegador si el stream de eventos es demasiado denso.
  - *Mitigación:* El backend solo debe emitir eventos de "dominio" significativos, no logs de debug de bajo nivel.

---

## 6. Plan

| Tarea | Complejidad | Dependencias |
|-------|-------------|--------------|
| 1. Crear migración SQL `supabase/migrations/022_enable_realtime_events.sql` | Baja | Ninguna |
| 2. Ejecutar migración en el entorno de desarrollo | Baja | Tarea 1 |
| 3. Crear script de validación `LAST/test_3_1_realtime.py` (simular suscriptor y emisor) | Media | Tarea 2 |
| 4. Documentar el contrato de eventos para el Paso 3.2 | Baja | Tarea 3 |

---

## 🔮 Roadmap (No para el MVP)
- **Compresión de Eventos:** Si el payload es muy grande, explorar el envío de hashes o referencias.
- **Broadcasting:** Uso de canales de Supabase sin persistencia para logs de depuración extrema que no necesiten guardarse en DB.

---
*Análisis generado por Antigravity siguiendo el protocolo ANALISTA.*
