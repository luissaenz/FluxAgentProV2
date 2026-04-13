# 🔬 ANÁLISIS TÉCNICO — Paso 3.1: Habilitar Supabase Realtime para domain_events

## 1. Diseño Funcional

### Happy path detallado
1. Ejecutar comando SQL para agregar tabla `domain_events` a publicación `supabase_realtime`
2. Verificar en Supabase Dashboard que la tabla aparece habilitada para realtime
3. Establecer conexión de prueba desde cliente frontend autenticado
4. Confirmar recepción de eventos INSERT en tiempo real (< 1 segundo de latencia)
5. Validar que RLS filtra correctamente eventos por `org_id` del tenant

### Edge cases que afectan al MVP
- **Cliente sin autenticación válida:** No recibe eventos (filtrado silencioso por RLS)
- **Reconexión durante ejecución activa:** Cliente debe obtener snapshot inicial + subscribe para cubrir gap
- **Alta frecuencia de eventos:** Frontend debe implementar throttling si es necesario

### Manejo de errores: qué ve el usuario cuando algo falla
- **Fallo SQL al agregar tabla:** Error de base de datos durante migración
- **Cliente no recibe eventos:** Verificar autenticación, configuración realtime y permisos RLS
- **Latencia > 1s:** Indica problema de red o configuración realtime

## 2. Diseño Técnico

### Componentes nuevos o modificaciones a existentes
**SQL Script único:**
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
```

### Interfaces (inputs/outputs de cada componente)
- **Input:** Tabla `domain_events` existente con estructura completa
- **Output:** Tabla habilitada para publicación realtime
- **Integración:** Frontend subscribe vía `@supabase/supabase-js`

### Modelos de datos nuevos o extensiones
**NINGUNA.** Estructura actual soporta realtime sin cambios.

**Debe ser coherente con docs/estado-fase.md:** Tabla `domain_events` existe, RLS configurada, índices optimizados.

## 3. Decisiones

| Decisión | Justificación técnica |
|----------|----------------------|
| Usar `ALTER PUBLICATION` directo | Declarativo, versionable, replicable en ambientes |
| Habilitar tabla completa vs columnas específicas | Eventos requieren payload completo para transcripts |
| No modificar RLS existente | Policy `tenant_select_domain_events` aplica automáticamente a realtime |

## 4. Criterios de Aceptación

- [ ] Comando `ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;` ejecuta sin error
- [ ] Tabla aparece habilitada en Supabase Dashboard (Settings > API > Realtime)
- [ ] Cliente autenticado establece conexión streaming exitosamente
- [ ] INSERT en `domain_events` se recibe en cliente en < 1 segundo
- [ ] Eventos filtrados correctamente por `org_id` (RLS aplicado)

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| RLS bloquea realtime silenciosamente | Baja | Alta | Test con cliente autenticado antes de cerrar paso |
| Fallback requerido si realtime falla | Media | Baja | Implementar polling como backup en paso 3.3 |

## 6. Plan

### Tareas atómicas ordenadas

1. **Ejecutar script SQL de habilitación** - Baja complejidad - Sin dependencias
2. **Verificar habilitación en Dashboard** - Baja complejidad - Depende de 1
3. **Test de suscripción con cliente autenticado** - Media complejidad - Depende de 2

### Estimación: Baja (15-30 minutos)

---

## 🔮 Roadmap (NO implementar ahora)

- Habilitar realtime en tablas adicionales (tasks, snapshots) - No requerido hasta Fase 4
- Filtros server-side personalizados - RLS suficiente para MVP
- Políticas de retención de eventos - Usar defaults de Supabase por ahora</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-Kilo.md