# Análisis Técnico - Paso 4.5: Test de Precisión Analítica

## 1. Diseño Funcional

### Happy Path
1. Usuario pregunta al chat analítico: "¿Cuál es el agente con mayor tasa de éxito en la última semana?"
2. El sistema clasifica la intención como `agent_success_rate`
3. Ejecuta la consulta SQL pre-validada contra la base de datos
4. Retorna el agente con mayor `success_rate` (completadas/totales * 100) en los últimos 7 días
5. La respuesta incluye métricas verificables: nombre del agente, tasa de éxito, tareas totales/completadas

### Edge Cases para MVP
- **Sin datos históricos:** Si no hay tareas en los últimos 7 días, la respuesta indica "No hay datos suficientes para calcular tasas de éxito"
- **Empate en tasa:** Si múltiples agentes tienen la misma tasa máxima, retorna el primero por orden alfabético de `role`
- **Agente sin tareas completadas:** Agentes con `success_rate = 0.00` se incluyen pero no son candidatos al "mayor"
- **Un solo agente:** Funciona correctamente retornando ese agente como el de mayor tasa

### Manejo de Errores
- **Fallo de clasificación:** Si el LLM no identifica la intención, fallback a keywords retorna `agent_success_rate`
- **Timeout de DB:** Respuesta con mensaje de "Servicio temporalmente no disponible, intenta nuevamente"
- **Rate limit excedido:** Frontend muestra mensaje específico de límite de organización (10 req/min)
- **Usuario ve:** Spinner durante procesamiento, luego respuesta narrativa o mensaje de error claro

## 2. Diseño Técnico

### Componentes Involucrados
- **Frontend:** `AnalyticalAssistantChat.tsx` (FAB global) - interfaz de usuario para preguntas en lenguaje natural
- **Backend:** `AnalyticalCrew` en `src/crews/analytical_crew.py` - orquestador con clasificación LLM + fallback keywords
- **Herramienta:** `SQLAnalyticalTool` en `src/tools/analytical.py` - ejecutor seguro de consultas allowlisted
- **Base de Datos:** Consulta `agent_success_rate` de `analytical_queries.py` con filtro `org_id` y ventana temporal de 7 días

### Interfaces
- **Input del Chat:** `{ question: "¿Cuál es el agente con mayor tasa de éxito en la última semana?" }`
- **API Response:** 
  ```json
  {
    "question": "¿Cuál es el agente con mayor tasa de éxito en la última semana?",
    "query_type": "agent_success_rate",
    "data": [
      {
        "role": "architect_flow",
        "total_tasks": 25,
        "completed_tasks": 23,
        "success_rate": 92.00
      }
    ],
    "summary": "El agente con mayor tasa de éxito es 'architect_flow' con 92.00% (23 de 25 tareas completadas).",
    "metadata": {
      "tokens_used": 150,
      "row_count": 1
    }
  }
  ```
- **Modelo de Datos:** Basado en tablas `tasks` y `agent_catalog` con JOIN por `assigned_agent_role` y `org_id`

### Modificaciones a Componentes Existentes
- Ninguna modificación requerida - utiliza contratos existentes de Fase 4
- Verificación: La consulta `agent_success_rate` ya está implementada y probada en tests previos

## 3. Decisiones

No se requieren decisiones técnicas nuevas. El paso reutiliza la arquitectura analítica completa implementada en los pasos 4.3 y 4.4, incluyendo:
- Clasificación de intención vía LLM con fallback keywords
- Ejecución segura mediante allowlist SQL
- Aislamiento multi-tenant por `org_id`
- Rate limiting por organización

## 4. Criterios de Aceptación

- [ ] El chat analítico responde a la pregunta "¿Cuál es el agente con mayor tasa de éxito en la última semana?" sin errores
- [ ] La respuesta incluye el nombre correcto del agente según la consulta SQL `agent_success_rate`
- [ ] La tasa de éxito reportada coincide exactamente con el cálculo: `(completed_tasks / total_tasks) * 100` redondeado a 2 decimales
- [ ] Los números de tareas totales y completadas coinciden con la base de datos para el período de 7 días
- [ ] La respuesta se genera en menos de 5 segundos desde la pregunta
- [ ] El `query_type` en la respuesta es exactamente `"agent_success_rate"`
- [ ] Si no hay datos, la respuesta indica claramente "No hay datos suficientes" en lugar de fallar

## 5. Riesgos

### Riesgo 1: Datos insuficientes en entorno de test
**Probabilidad:** Media  
**Impacto:** Alto  
**Mitigación:** Ejecutar previamente scripts de seed para crear tareas de test con estados variados (completed, failed, blocked) en los últimos 7 días

### Riesgo 2: Desincronización entre clasificación y allowlist
**Probabilidad:** Baja  
**Impacto:** Alto  
**Mitigación:** Verificar que tanto el LLM como el fallback keywords mapean la pregunta a `agent_success_rate`

### Riesgo 3: Errores de redondeo en cálculo de tasa
**Probabilidad:** Baja  
**Impacto:** Medio  
**Mitigación:** Verificar que la fórmula SQL `ROUND(100.0 * completed / NULLIF(total, 0), 2)` coincide con el cálculo manual

### Riesgo 4: Problemas de concurrencia en DB
**Probabilidad:** Baja  
**Impacto:** Medio  
**Mitigación:** Ejecutar la verificación en ventana de mantenimiento o con locks de lectura

## 6. Plan

1. **Preparar datos de test** (Baja complejidad, 15 min)
   - Ejecutar seed de tareas con diferentes estados para al menos 3 agentes
   - Asegurar distribución: 70% completed, 20% failed, 10% blocked en última semana

2. **Ejecutar test automático existente** (Baja complejidad, 5 min)
   - Correr `src/scripts/test_analytical_precision.py`
   - Verificar que `test_ask_method_structure` pasa con la pregunta objetivo

3. **Realizar consulta manual al chat** (Media complejidad, 10 min)
   - Acceder al dashboard y usar el FAB de chat analítico
   - Preguntar: "¿Cuál es el agente con mayor tasa de éxito en la última semana?"
   - Capturar respuesta completa (JSON de backend + renderizado frontend)

4. **Verificar contra base de datos** (Media complejidad, 15 min)
   - Ejecutar directamente la consulta SQL `agent_success_rate` con `org_id` de test
   - Comparar resultados: agente top, success_rate, total_tasks, completed_tasks
   - Documentar cualquier discrepancia con evidencia

5. **Validar criterios de aceptación** (Baja complejidad, 10 min)
   - Marcar cada criterio binario según resultados
   - Si falla algún criterio, documentar root cause y steps para fix

6. **Limpiar datos de test** (Baja complejidad, 5 min)
   - Remover registros creados para testing
   - Verificar que no afecta producción

## 7. 🔮 Roadmap

### Optimizaciones de Precisión
- **Cache de resultados:** Implementar cache Redis para consultas analíticas frecuentes con TTL de 5 minutos
- **Validación cruzada:** Agregar comparación automática entre respuesta del LLM y cálculo SQL en entorno de desarrollo
- **Auditoría de respuestas:** Log detallado de cada respuesta analítica para análisis de precisión histórica

### Mejoras de Testing
- **Suite de precisión expandida:** Tests automatizados para todas las consultas allowlisted con datasets conocidos
- **Golden dataset:** Crear conjunto de datos de referencia para validar respuestas analíticas
- **CI/CD integration:** Ejecutar tests de precisión en cada deployment con comparación contra baseline

### Features Futuras (Post-MVP)
- **Preguntas compuestas:** Soporte para "agente más eficiente Y con más tareas" combinando múltiples métricas
- **Filtros temporales dinámicos:** Permitir "últimos 30 días" o "este mes" en lugar de ventana fija de 7 días
- **Explicaciones detalladas:** Incluir breakdown de por qué un agente tiene mejor tasa (tipos de flows, etc.)

---

**Estimación Total:** 1 hora  
**Complejidad General:** Baja (reutiliza infraestructura existente)  
**Dependencias:** Pasos 4.3 y 4.4 completados y funcionales