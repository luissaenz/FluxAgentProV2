# 📋 ANÁLISIS TÉCNICO — Paso 4.3: AnalyticalCrew

**Agente:** OC  
**Fecha:** 2026-04-12  
**Paso:** 4.3 [Backend] — Implementar `AnalyticalCrew`

---

## 1. Diseño Funcional

### 1.1 Propósito
El `AnalyticalCrew` es un agente especializado que procesa consultas analíticas complejas sobre datos históricos de la organización. No ejecuta tareas genéricas de CrewAI; su función es purely analytical.

### 1.2 Happy Path
1. El sistema recibe una solicitud de análisis (query_type + params opcionales)
2. El crew valida que el query_type esté en el allowlist de consultas predefinidas
3. Ejecuta la consulta SQL segura contra la base de datos del tenant
4. Devuelve los resultados enriquecidos con metadata (timestamps, row_count, query_template)
5. Opcionalmente puede consultar el EventStore para análisis temporal

### 1.3 Queries Soportadas (MVP)
- `agent_success_rate`: Tasa de éxito por agente en últimos 7 días
- `tickets_by_status`: Distribución de tickets por estado
- `flow_token_consumption`: Consumo de tokens por flow type
- `recent_events_summary`: Eventos últimos 24h por tipo
- `tasks_by_flow_type`: Tareas agrupadas por flow y estado

### 1.4 Edge Cases MVP
- **Org sin datos:** Retorna arrays vacíos sin error (comportamiento esperado)
- **tokens_used null:** Se filtra en `_query_flow_tokens` (línea 259-260)
- **Division by zero:** Mitigada con `NULLIF` en SQL y cálculos defensivos en Python (línea 223)
- **Query unknown:** Lanza `ValueError` con lista de queries disponibles (línea 139-143)

### 1.5 Manejo de Errores
- Error de query inválida → `ValueError` con mensaje claro
- Error de DB → Propaga excepción (no silenciar errores de infraestructura)
- EventStore no disponible → Silently falls back a query de BD (líneas 366-371)

---

## 2. Diseño Técnico

### 2.1 Componentes Existentes a Utilizar
- `BaseCrew`: Clase base de la cual hereda (línea 93)
- `EventStore`: Acceso al store de eventos para análisis temporal (líneas 116-120)
- `get_tenant_client`: Función del session manager para acceso seguro a BD (línea 177)

### 2.2 Interfaz Pública
```python
class AnalyticalCrew(BaseCrew):
    def __init__(self, org_id: str, user_id: Optional[str] = None) -> None: ...
    
    async def analyze(
        self,
        query_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...
    
    async def query_events(
        self,
        event_type: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]: ...
```

### 2.3 Modelos de Datos
No se requieren nuevos modelos. El crew consume datos existentes:
- `tasks`: flow_type, status, assigned_agent_role, tokens_used, created_at
- `tickets`: status
- `domain_events`: event_type, aggregate_type, aggregate_id, payload, sequence, created_at
- `agent_catalog`: role (via JOIN implícito)

### 2.4 Consideraciones de Seguridad
- **Allowlist de queries:** Solo consultas predefinidas pueden ejecutarse (línea 29-90)
- **Parameterized org_id:** Inyección mitigada por construcción de queries con f-strings controlados (línea 41)
- **RLS activo:** El tenant client aplica Row Level Security automáticamente
- **Sin SQL raw:** Evita exposición a ataques de inyección

### 2.5 Coherencia con estado-fase.md
- ✅ Usa el patrón de registry existente
- ✅ Respeta la arquitectura de tenants via `get_tenant_client`
- ✅ No contradice ninguna decisión previa

---

## 3. Decisiones

| Decisión | Justificación |
|----------|----------------|
| Allowlist de queries en lugar de SQL libre | Seguridad MVP: previene inyección y queries destructivas. Simplifica validación. |
| Agregación en Python en lugar de SQL raw | Supabase no soporta SQL raw. RPC functions quedan para versión post-MVP. |
| Lazy-init de EventStore | Evita overhead si no se usa la funcionalidad de eventos. |
| Fallback silencioso en EventStore | El análisis principal es SQL; eventos son complemento opcional. |
| Timeout por defecto del tenant client | Heredado de la configuración global de Supabase. |

### Decisiones No Tomadas (para Roadmap)
- **RPC functions en Supabase:** Postergado para post-MVP cuando volumen de datos crezca
- **Caching de resultados:** Postergado; el MVP acepta queries live
- **Consultas ad-hoc sin allowlist:** Excluido por seguridad

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| 1 | `AnalyticalCrew` instancia correctamente con org_id y user_id | ✅ Unit test |
| 2 | `analyze("agent_success_rate")` retorna array con campos role, total_tasks, completed_tasks, success_rate | ✅ Integration test |
| 3 | `analyze("unknown_query")` lanza ValueError | ✅ Unit test |
| 4 | `analyze()` aplica filtro de 7 días para agent_success_rate | ✅ Integration test |
| 5 | `query_events()` retorna eventos filtrados por tipo y límite | ✅ Integration test |
| 6 | Todas las queries respetan RLS (mismo org_id) | ✅ Integration test |
| 7 | El crew hereda de BaseCrew correctamente | ✅ Code review |
| 8 | Fallback de EventStore no rompe si store no está disponible | ✅ Unit test |

---

## 5. Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| **Rendimiento con grandes datasets** | Media | Queries tienen LIMIT. Para MVP aceptable. Post-MVP: paginación. |
| **Inyección vía params** | Baja | Params no se usan en strings SQL actualmente. Si se agregan, sanitizar. |
| **Desincronización allowlist vs código** | Baja | Allowlist definido como constante en mismo archivo. |
| **Supabase client timeout** | Media | Heredado del sistema. Monitorear en producción. |

---

## 6. Plan de Implementación

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Verificar que `analytical_crew.py` compila sin errores | Baja | Ninguna |
| 2 | Crear tests unitarios para método `analyze()` | Media | #1 |
| 3 | Crear tests de integración para queries específicas | Media | #1, #2 |
| 4 | Validar que RLS se aplica correctamente | Alta | Necesita fixture de test con multi-tenant |
| 5 | Documentar uso en README del proyecto | Baja | #3 |

### Estado Actual
El archivo `src/crews/analytical_crew.py` **ya existe y contiene una implementación completa** del AnalyticalCrew con las 5 queries predefinidas. El paso 4.3 está **funcionalmente implementado**.

### Acciones Pendientes
- Tests unitarios no existentes actualmente
- Validación de integración end-to-end con el chat analítico (Paso 4.4)

---

## 🔮 Roadmap (Post-MVP)

1. **RPC Functions en Supabase:** Reemplazar agregaciones Python con SQL puro para mejor rendimiento
2. **Caching:** Redis o memoria para queries frecuentes
3. **Consultas ad-hoc:** Extensión de allowlist con validación de schemas
4. **Gráficos predefinidos:** Integración con charting library para dashboard analítico
5. **Exportación:** CSV/Excel de resultados
6. **Alertas thresholds:** Notificaciones automáticas cuando métricas cruzan umbrales
