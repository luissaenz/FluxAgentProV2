# 🧠 Análisis Técnico: Paso 4.1 - Metadata de Escalamiento

## 1. Diseño Funcional

### Objetivo
Habilitar la capacidad de modelar jerarquías de procesos de negocio dentro del framework de flows. Esto permite que el sistema "entienda" que un proceso (ej. `facturacion_flow`) es la continuación natural o depende de otro (ej. `cotizacion_flow`), y organizarlos en categorías lógicas.

### Flujo de Usuario (Happy Path)
1.  Un desarrollador crea un nuevo Flow.
2.  Al usar el decorador `@register_flow`, especifica metadatos descriptivos:
    -   `category`: El dominio al que pertenece (Ventas, RRHH, etc.).
    -   `depends_on`: Una lista de nombres de flows que preceden rítmicamente a este.
3.  El sistema de registro indexa esta información.
4.  La futura vista de jerarquía (Paso 4.2) consulta estos metadatos para renderizar un grafo de procesos.

### Edge Cases / Consideraciones MVP
-   **Dependencias Inexistentes:** El registro debe permitir dependencias a flows que aún no han sido importados (late binding), pero la consulta de jerarquía debe ser capaz de señalar "nodos huérfanos".
-   **Ciclos de Dependencia:** Para el MVP, el registro no validará ciclos (A -> B -> A), pero se recomienda que la lógica de visualización maneje esto de forma elegante (DAG vs Grafo general).

---

## 2. Diseño Técnico

### Componentes Afectados
-   **`src/flows/registry.py`**: El corazón del cambio. Requiere extender la clase `FlowRegistry` y el decorador `register_flow`.

### Interfaces y Contratos
-   **`register_flow(name, *, depends_on, category)`**:
    -   `depends_on`: `Optional[List[str]]`. Default: `[]`.
    -   `category`: `Optional[str]`. Default: `None`.
-   **`FlowRegistry.get_hierarchy()`**:
    -   Retorno: `Dict[str, Dict[str, Any]]` donde la clave es el `flow_name` y el valor contiene la metadata.

### Modelo de Datos
La información se mantendrá de forma volátil en el singleton `flow_registry`. No se requiere persistencia en base de datos para este paso, ya que la definición de los procesos reside en el código (Code-as-Schema).

---

## 3. Decisiones

1.  **Metadata en Decorador:** Se decide incluir la metadata en el momento de registro para minimizar el "boilerplate". El código fuente es la única fuente de verdad (Single Source of Truth).
2.  **Normalización de Nombres:** Se utilizará `snake_case` para el almacenamiento de nombres de flows en el registro de metadata, garantizando coherencia con el lookup de clases.
3.  **Defaulting:** Los flows sin categoría se agruparán bajo `"sin_categoria"` para asegurar que siempre aparezcan en las consultas analíticas.

---

## 4. Criterios de Aceptación (NUEVO)

-   [ ] El decorador `@register_flow` acepta los parámetros `depends_on` y `category` sin errores de firma.
-   [ ] La clase `FlowRegistry` almacena internamente esta información de forma aislada para cada flow.
-   [ ] Existe un método `get_metadata(name)` que devuelve la metadata normalizada.
-   [ ] Existe un método `get_hierarchy()` que devuelve el mapa completo para su uso en APIs.
-   [ ] Los tests unitarios confirman que registrar un flow con dependencias no afecta la capacidad de instanciarlo (retrocompatibilidad).

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| **Ambigüedad de Nombres** | Medio | Forzar normalización vía `_normalize_flow_name` en todas las entradas. |
| **Carga de Memoria** | Bajo | La metadata es ligera (strings), no representa riesgo para el singleton. |
| **Dependencias Rotas** | Bajo | El sistema no forzará la existencia de la dependencia en tiempo de registro, facilitando importaciones dinámicas. |

---

## 6. Plan de Implementación

1.  **Extensión del Registry (Alta)**: Modificar `src/flows/registry.py` para añadir el soporte de almacenamiento de metadatos. (Complejidad: Baja)
2.  **Métodos de Acceso (Media)**: Implementar `get_hierarchy` y `get_flows_by_category`. (Complejidad: Baja)
3.  **Documentación de Contratos (Baja)**: Actualizar el docstring del registro para reflejar el uso de Phase 4. (Complejidad: Muy Baja)

---

## 🔮 Roadmap (NO implementar ahora)
-   **Validación de Ciclos:** Detector de dependencias circulares en tiempo de registro.
-   **Metadatos de Performance:** Añadir `expected_duration` para comparar ejecución real vs estimada.
-   **Límite de Escalamiento:** Configuración de profundidad máxima de jerarquía.
