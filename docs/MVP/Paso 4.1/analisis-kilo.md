# ANÁLISIS TÉCNICO - PASO 4.1: METADATA DE ESCALAMIENTO EN REGISTRY.PY

## 1. Diseño Funcional

### Happy Path
- Los flows se registran con metadata de jerarquía mediante `@register_flow(name, depends_on=[...], category="...")`
- El endpoint `/flows/hierarchy` retorna estructura completa con dependencias y categorías
- El endpoint `/flows/available` incluye metadata en cada flow para UI de selección
- La jerarquía respeta dependencias secuenciales: ventas → logística → compras → finanzas

### Edge Cases
- Flows sin dependencias (raíz de jerarquía) tienen `depends_on=[]`
- Flows sin categoría asignada aparecen en grupo "sin_categoria" 
- Dependencias circulares son prevenidas por validación en registro
- Flows inexistentes referenciados en `depends_on` generan error en startup

### Manejo de Errores
- Registro de flow con dependencia inexistente: `ValueError` en import time
- API retorna metadata por defecto (vacío) si flow no tiene metadata configurada
- Cliente recibe estructura consistente aunque algunos flows carezcan de metadata

## 2. Diseño Técnico

### Componentes Nuevos/Modificaciones
- **registry.py**: Framework ya implementado, requiere actualización de decoradores `@register_flow`
- **routes/flows.py**: Endpoints `/hierarchy` y `/available` ya exponen metadata
- **Pydantic Models**: `FlowInfo` y `FlowHierarchyNode` ya incluyen campos `depends_on` y `category`

### Interfaces (Inputs/Outputs)
- **Registro**: `@register_flow(name, depends_on: List[str] = None, category: str = None)`
- **API /flows/hierarchy**: `{"hierarchy": {flow: {"depends_on": [...], "category": "..."}}, "categories": {"ventas": ["cotizacion_flow"]}}`
- **API /flows/available**: Array de `FlowInfo` con campos `depends_on` y `category`

### Modelos de Datos
- **Metadata Structure**: `{"depends_on": List[str], "category": Optional[str]}`
- **Jerarquía Coctel**: `cotizacion_flow` → `logistica_flow` → `compras_flow` → `finanzas_flow`
- **Jerarquía Bartenders**: `bartenders_preventa` → `bartenders_reserva` → `bartenders_alerta`|`bartenders_cierre`

### Integraciones
- **Registro Global**: `flow_registry` singleton mantiene metadata consistente
- **API Gateway**: Endpoints integran metadata sin cambios en lógica de ejecución
- **Frontend**: Próximo paso 4.2 consumirá `/flows/hierarchy` para `FlowHierarchyView.tsx`

## 3. Decisiones

- **Categorización por Dominio**: Flows agrupados por "ventas", "logistica", "compras", "finanzas", "eventos"
- **Dependencias Explícitas**: Solo dependencias directas (no transitivas) para mantener simplicidad
- **Validación en Import**: Errores de dependencias detectados en startup, no runtime
- **Backward Compatibility**: Flows existentes sin metadata aparecen con valores por defecto

## 4. Criterios de Aceptación
- Endpoint `/flows/hierarchy` retorna estructura con dependencias correctas para todos los flows
- Endpoint `/flows/available` incluye campos `depends_on` y `category` en cada `FlowInfo`
- Flows coctel siguen jerarquía ventas→logística→compras→finanzas
- Flows bartenders siguen jerarquía preventa→reserva→cierre
- No hay dependencias circulares ni referencias a flows inexistentes
- Categorías agrupan flows por dominio de negocio correctamente

## 5. Riesgos
- **Dependencias Circulares**: Validación insuficiente permite loops infinitos en jerarquía
  - *Mitigación*: Implementar validación topológica en `FlowRegistry.register()`
- **Cambios en Categorías**: Renombrar categorías rompe contratos con frontend futuro
  - *Mitigación*: Definir categorías como constantes en módulo separado
- **Performance API**: Endpoint hierarchy sin caché impacta latencia en listados grandes
  - *Mitigación*: Implementar cache Redis para metadata de jerarquía

## 6. Plan
1. **Actualizar coctel_flows.py**: Añadir `depends_on` y `category` a decoradores `@register_flow`
2. **Actualizar bartenders flows**: Aplicar metadata de jerarquía eventos en flows bartenders
3. **Validar dependencias**: Ejecutar import de módulos para detectar errores de referencias
4. **Test API endpoints**: Verificar `/flows/hierarchy` y `/flows/available` retornan metadata correcta
5. **Verificar jerarquía**: Confirmar estructura de dependencias respeta lógica de negocio

## 🔮 Roadmap
- **Validación Automática**: Script de CI que verifica integridad de jerarquía (no dependencias circulares)
- **Cache de Metadata**: Redis para endpoints de jerarquía con invalidación en cambios
- **UI de Dependencias**: Indicadores visuales en `/flows/available` mostrando prerrequisitos
- **Orquestación Automática**: Sistema que ejecuta flows en orden basado en dependencias
- **Análisis de Impacto**: Métricas de uso de categorías para optimizar agrupaciones</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md