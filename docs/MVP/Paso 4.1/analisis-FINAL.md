# 🏛️ ANALISIS-FINAL: Paso 4.1 - Metadata de Escalamiento en el Registry

## 1. Resumen Ejecutivo
Este paso tiene como objetivo dotar al framework de flows de la capacidad de modelar **jerarquías de procesos de negocio** mediante metadatos de clasificación (`category`) y dependencia (`depends_on`). Actualmente, el sistema opera con flows aislados sin conocimiento de su relación lógica (ej. un flow de "Facturación" que depende de una "Venta" previa).

Ubicado al inicio de la Fase 4, este paso establece los cimientos para la supervisión analítica y la visualización jerárquica (Paso 4.2). Se implementará una solución de **Code-as-Schema**, donde la metadata reside en los decoradores de código, complementada con motores de validación de integridad para detectar referencias huérfanas o dependencias circulares antes de la ejecución.

## 2. Diseño Funcional Consolidado

### Happy Path
1.  **Registro con Contexto:** Un desarrollador registra un flow utilizando el decorador `@register_flow`, especificando su categoría funcional (ej. `ventas`, `rrhh`) y sus flows predecesores en `depends_on`.
2.  **Validación Post-Startup:** Una vez que el servidor carga todos los módulos, el `FlowRegistry` ejecuta una validación automática del grafo de dependencias.
3.  **Consumo de Jerarquía:** El frontend consulta el endpoint `GET /flows/hierarchy` y recibe un mapa estructurado de procesos agrupados por categoría, incluyendo estados de validación (si hay ciclos o nodos rotos).
4.  **Flujos Dinámicos:** Los flows creados dinámicamente desde la BD heredan metadatos definidos en sus plantillas de workflow.

### Edge Cases para MVP
-   **Dependencia a Flow Inexistente:** El sistema detecta el error pero NO impide el arranque del servidor; en su lugar, marca el nodo como `invalid_dependency` en la API para alertar al operador.
-   **Ciclos de Dependencia (A -> B -> A):** Se detectan mediante un algoritmo DFS y se reportan en el endpoint de jerarquía para evitar bloqueos en futuras orquestaciones automáticas.
-   **Categorías Huérfanas:** Flows sin categoría explícita se agrupan automáticamente bajo `"sin_categoria"`.

### Manejo de Errores
-   **Startup:** Logs detallados (Warnings) si se detectan inconsistencias en el grafo de dependencias durante el registro.
-   **API:** El response de jerarquía incluirá un objeto `validation` que detalla los problemas encontrados, permitiendo al frontend mostrar alertas visuales sobre la integridad del sistema.

## 3. Diseño Técnico Definitivo

### Arquitectura de Componentes
-   **`src/flows/registry.py` (Core):** Singleton `FlowRegistry` centraliza el almacenamiento de `_metadata`. Se añadirán los métodos `validate_dependencies()` y `detect_cycles()`.
-   **`src/flows/dynamic_flow.py`:** Modificar `DynamicWorkflow.register()` para capturar metadatos del diccionario de definición proveniente de la base de datos.
-   **`src/api/routes/flows.py` (API):** Extender los endpoints `/hierarchy` y `/available` para exponer los resultados de validación y la metadata enriquecida.

### Contratos de API (Propuesta Unificada)

**`GET /flows/hierarchy`**
```json
{
  "hierarchy": {
    "cotizacion_flow": {
      "name": "Cotización de Venta",
      "category": "ventas",
      "depends_on": []
    },
    "facturacion_flow": {
      "name": "Facturación Electrónica",
      "category": "finanzas",
      "depends_on": ["cotizacion_flow"]
    }
  },
  "categories": {
    "ventas": ["cotizacion_flow"],
    "finanzas": ["facturacion_flow"]
  },
  "validation": {
    "invalid_dependencies": {},
    "cycles": []
  }
}
```

### Modelo de Datos
La metadata se mantiene **en memoria** (volátil) asociada al ciclo de vida del proceso de Python. La fuente de verdad para flows estáticos es el decorador `@register_flow`, y para dinámicos es la tabla `workflow_templates`.

## 4. Decisiones Tecnológicas

1.  **Validación Post-Carga (Lazy Validation):** No se validarán dependencias en el decorador (import time) para evitar errores por orden de importación. Se ejecutará una vez tras el startup del app.
2.  **Detección de Ciclos vía DFS:** Se implementará un algoritmo de búsqueda en profundidad (Depth First Search) para detectar ciclos de forma eficiente (O(V+E)).
3.  **Soporte Transparente para Dynamic Flows:** La integración en `DynamicWorkflow.register()` garantiza que los procesos definidos por usuario tengan el mismo nivel de visibilidad analítica que los core flows.
4.  **No Enforcement en Runtime (MVP):** Este paso **NO bloquea** la ejecución de un flow si sus dependencias no están listas; solo modela la relación visual. El bloqueo se delega a fases post-MVP.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El usuario puede ver la jerarquía completa de procesos en el endpoint `/hierarchy`.
- [ ] Los flows existentes (`coctel`, `bartenders`) aparecen con sus categorías correctas asignadas.
- [ ] Si un flow se registra sin categoría, aparece bajo `"sin_categoria"`.

### Técnicos
- [ ] El decorador `@register_flow` acepta `depends_on` (lista de strings) y `category` (string).
- [ ] `FlowRegistry.validate_dependencies()` identifica correctamente flows que apuntan a nombres inexistentes.
- [ ] `FlowRegistry.detect_cycles()` identifica y reporta ciclos directos (A-B-A) e indirectos (A-B-C-A).
- [ ] Los flows dinámicos registrados vía `DynamicWorkflow` incluyen su metadata en el registro global.
- [ ] El endpoint `/available` incluye los nuevos campos de metadata en cada objeto de la lista.

### Robustez
- [ ] El servidor arranca correctamente incluso si hay dependencias circulares o rotas (los errores se reportan vía API/Logs).
- [ ] No hay regresión en los tests unitarios existentes del `FlowRegistry`.

## 6. Plan de Implementación

| # | Tarea | Complejidad |
|---|---|---|
| **1** | **Infraestructura de Validación:** Implementar `validate_dependencies` y `detect_cycles` en `registry.py`. | Media |
| **2** | **Soporte Dinámico:** Actualizar `DynamicWorkflow.register()` en `dynamic_flow.py`. | Baja |
| **3** | **Enriquecimiento de Endpoints:** Modificar `flows.py` para incluir validación en el response JSON. | Baja |
| **4** | **Auditoría de Datos:** Actualizar todos los decoradores en `src/flows/coctl_flows.py` y flows de bartenders con su jerarquía real. | Media |
| **5** | **Batería de Tests:** Crear tests unitarios para los nuevos algoritmos de validación del grafo. | Media |

## 7. Riesgos y Mitigaciones
-   **Falsos Positivos en Ciclos:** Un flow que se usa como paso interno de muchos flows (ej. `log_event`) podría parecer un ciclo si no se gestiona bien el grafo. *Mitigación:* Diferenciar claramente entre jerarquía de negocio (Step 4.1) y ejecución de pasos técnicos de bajo nivel.
-   **Desactualización de Metadata:** Al ser Code-as-Schema, un cambio de nombre en un archivo puede romper una dependencia string. *Mitigación:* Usar el método `validate_dependencies` en the startup para alertar de inmediato.

## 8. Testing Mínimo Viable
1.  **Test de Integridad:** Registrar intencionalmente un Flow C que depende de un Flow D (inexistente). Verificar que la API lo reporta en `invalid_dependencies`.
2.  **Test de Ciclos:** Registrar un ciclo A-B-A. Verificar que la API reporta el ciclo en el campo `cycles`.
3.  **Test de Disponibilidad:** Verificar que `GET /flows/available` muestra la categoría asignada al `cotizacion_flow`.

## 9. 🔮 Roadmap (NO implementar ahora)
-   **Enforcement Automático:** Bloqueo de ejecución de una Task si sus dependencias de negocio no están en estado `done`.
-   **Visualización en Frontend:** Implementación del componente React `FlowHierarchyView.tsx` (Paso 4.2).
-   **Migración a DB:** Mover la metadata a una tabla SQL para permitir filtros complejos sin cargar todos los módulos en memoria.
