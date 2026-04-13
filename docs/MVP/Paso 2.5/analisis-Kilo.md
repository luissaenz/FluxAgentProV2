# Análisis Técnico - Paso 2.5: Test de aislamiento multi-tenant para SOUL

## 1. Diseño Funcional

### Happy Path
- Se ejecuta una validación que simula consultas desde dos organizaciones diferentes (Org1 y Org2) al endpoint `GET /agents/{id}/detail` para un agente con el mismo identificador lógico en ambas organizaciones.
- La respuesta desde Org1 incluye únicamente la metadata SOUL correspondiente a Org1, sin acceso a la de Org2.
- La respuesta desde Org2 incluye únicamente la metadata SOUL correspondiente a Org2, sin acceso a la de Org1.
- El test confirma que el aislamiento multi-tenant se mantiene a nivel de API y base de datos.

### Edge Cases Relevantes para MVP
- Agente existente en una organización pero no en la otra: La consulta desde la organización sin el agente debe retornar un error 404 o respuesta vacía, sin exponer existencia en otras organizaciones.
- Agente con `org_id` nulo o inválido: El sistema debe denegar el acceso o aplicar políticas de seguridad predeterminadas sin violar aislamiento.
- RLS temporalmente deshabilitado: El test debe detectar si las políticas de Row Level Security no se aplican correctamente, simulando un fallo de configuración.

### Manejo de Errores
- Si el aislamiento falla, el usuario del test (desarrollador) recibe un reporte detallado indicando cuál consulta violó el aislamiento, incluyendo los datos devueltos incorrectamente.
- No hay manejo de errores orientado al usuario final, ya que este es un test de validación técnica.

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Script de Validación:** Un script de prueba (ej. Python con requests para API o psycopg2 para DB directa) que ejecuta consultas simuladas desde diferentes contextos de tenant.
- **Configuración de Test Data:** Preparación de datos en base de datos de prueba con agentes duplicados en orgs distintas, respetando el esquema `agent_metadata`.

### Interfaces (Inputs/Outputs)
- **Input del Test:** 
  - `org_id_1`: Identificador de organización 1
  - `org_id_2`: Identificador de organización 2
  - `agent_id`: Identificador común del agente en ambas orgs
- **Output del Test:** 
  - Booleano: `true` si aislamiento se mantiene, `false` si se viola
  - Detalles: Lista de violaciones encontradas (ej. "Org1 accedió a metadata de Org2")

### Modelos de Datos
- No se requieren nuevos modelos; se utiliza la tabla `agent_metadata` existente con RLS aplicado.
- El contrato del endpoint `GET /agents/{id}/detail` se respeta: `{ agent: { ..., soul_narrative }, ... }`, pero filtrado por `org_id` del contexto de autenticación.
- Coherente con `estado-fase.md`: El LEFT JOIN ya incluye metadata, y RLS asegura que solo se devuelva data de la org autenticada.

## 3. Decisiones
- **Enfoque de Validación:** Se opta por un test de integración manual/ejecutable en lugar de unitario, ya que el aislamiento depende de configuración de DB (RLS) y contexto de API, no solo lógica de código.
- **Simulación de Multi-Tenancy:** Usar headers de autenticación o sesiones simuladas para cambiar el contexto de `org_id`, sin requerir entornos físicos separados para MVP.

## 4. Criterios de Aceptación
- La consulta `GET /agents/{id}/detail` desde contexto Org1 devuelve `soul_narrative` únicamente de Org1.
- La consulta `GET /agents/{id}/detail` desde contexto Org2 devuelve `soul_narrative` únicamente de Org2.
- Si el agente no existe en la org consultante, se retorna HTTP 404 sin información de otras organizaciones.
- El test ejecuta sin errores de conexión o configuración, y reporta resultados claros.
- La validación se completa en menos de 5 minutos en entorno de desarrollo.

## 5. Riesgos
- **Fallo en RLS:** Si las políticas de Row Level Security en `agent_metadata` no se aplican correctamente, el test podría pasar falsamente o fallar sin detectar la violación real. **Mitigación:** Verificar configuración de RLS antes del test con query directa a DB.
- **Propagación Incorrecta de org_id:** Si el backend no inyecta correctamente el `org_id` en las queries del endpoint, el aislamiento se rompe. **Mitigación:** Revisar código de `agents.py` para asegurar que el contexto de autenticación se usa en el JOIN.
- **Datos de Test Inconsistentes:** Si los agentes de prueba no se crean correctamente con orgs separadas, el test no valida aislamiento real. **Mitigación:** Usar scripts de seed específicos para test, con validación previa de datos.

## 6. Plan
1. **Preparar Entorno de Test (Baja):** Configurar base de datos de prueba con dos organizaciones y un agente compartido por ID lógico, insertando metadata SOUL diferente en cada org.
2. **Implementar Script de Validación (Media):** Crear script que simule llamadas API desde contextos Org1 y Org2, capturando respuestas y verificando aislamiento.
3. **Ejecutar Test Manual (Baja):** Correr el script y registrar resultados, incluyendo capturas de queries y respuestas.
4. **Documentar y Reportar (Baja):** Generar reporte de validación con evidencia de cumplimiento o fallos detectados.
   - **Dependencias:** Requiere acceso a entorno de test con multi-tenancy configurado; depende de que RLS esté activo en DB.

## 🔮 Roadmap (NO implementar ahora)
- Automatización del test en CI/CD para ejecuciones continuas post-despliegue.
- Expansión a validación de aislamiento en otros endpoints relacionados con agentes (ej. listados, métricas).
- Implementación de monitoring en producción para alertas de violaciones de aislamiento, integrando con el sistema de eventos.
- Optimización de performance del test para entornos de alto volumen, reduciendo tiempo de ejecución.
- Consideraciones de escalabilidad: Diseñar el test para validar aislamiento con cientos de organizaciones sin impacto en performance.</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-Kilo.md