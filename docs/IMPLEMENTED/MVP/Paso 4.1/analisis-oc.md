# 📋 ANÁLISIS TÉCNICO — Paso 4.1: Metadata de Escalamiento en el Registry

**Agente:** oc  
**Fecha:** 2026-04-12  
**Ubicación:** `src/flows/registry.py`

---

## 1. Diseño Funcional

### 1.1 Objetivo del Paso
Añadir campos `depends_on` y `category` a los flows para modelar la **jerarquía de procesos de negocio** (ej: "Venta" → "Facturación").

### 1.2 Estado Actual
El mecanismo de metadata **ya está implementado** en el código:

- **Decorator `@register_flow`** (línea 162-168 en `registry.py`): Acepta parámetros `depends_on: List[str]` y `category: str`.
- **Almacenamiento** (línea 75-78): Se guarda en `_metadata` dict en memoria.
- **APIs existentes** (líneas 157-180 en `flows.py`):
  - `GET /flows/hierarchy`: Retorna `FlowHierarchyResponse` con estructura `{hierarchy, categories}`.
  - `GET /flows/`: Incluye metadata en `list_flows`.
- **Uso en flows existentes** (`coctl_flows.py:21`): `@register_flow("cotizacion_flow", category="ventas")`.

### 1.3 Happy Path
1. Un flow se registra con: `@register_flow("facturacion_flow", depends_on=["cotizacion_flow"], category="ventas")`
2. El registry almacena la metadata en memoria.
3. API `GET /flows/hierarchy` retorna el árbol de dependencias.
4. Frontend consume el endpoint para renderizar `FlowHierarchyView`.

### 1.4 Edge Cases
- **Ciclo en dependencias** (`A depends_on B, B depends_on A`): No hay validación. Risk: deadlock en orquestación.
- **Categoría vacía**: Se muestra como `"sin_categoria"` (línea 116).
- **Flow sin metadata**: Retorna defaults: `depends_on: []`, `category: None`.

---

## 2. Diseño Técnico

### 2.1 Componentes Existentes
| Componente | Ubicación | Propósito |
|------------|-----------|-----------|
| `FlowRegistry.register()` | `registry.py:47` | Decorador con metadata |
| `FlowRegistry.get_hierarchy()` | `registry.py:101` | Retorna árbol completo |
| `FlowRegistry.get_flows_by_category()` | `registry.py:112` |-Agrupa por categoría |
| `GET /flows/hierarchy` | `flows.py:157` | Endpoint API |

### 2.2 Interfaces
```python
# Decorador
@register_flow("facturacion_flow", depends_on=["cotizacion_flow"], category="ventas")
class FacturacionFlow(BaseFlow): ...

# API Response (ya existe en flows.py)
class FlowHierarchyNode(BaseModel):
    flow_type: str
    name: str
    category: Optional[str]
    depends_on: List[str]
```

### 2.3 Modelo de Datos
La metadata vive **en memoria** (dict `_metadata`), no hay persistencia en BD.

---

## 3. Decisiones

### 3.1 Decisión: Metadata en Memoria vs BD
| Opción | Pros | Contras |
|--------|------|---------|
| **En memoria (actual)** | Simple, cero migraciones | Se pierde al reiniciar servicio |
| **En BD** | Persistencia, queryable | Requiere migración, más complejidad |

**Justificación:** Para MVP, metadata en memoria es suficiente. El endpoint `/flows/hierarchy` sirve la jerarquía en runtime. Si se necesitaqueryable offline, migrar a tabla `flow_metadata` post-MVP.

### 3.2 Decisión: Validación de Ciclos
**Estado:** No implementada.  
**Impacto:** Medio. Orquestador debe validar antes de ejecutar.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| 1 | El decorador `@register_flow` acepta `depends_on` y `category` | ✅ Código `registry.py:47` |
| 2 | `GET /flows/hierarchy` retorna estructura con `depends_on` y `category` | ✅ Llamar endpoint |
| 3 | Flow existente `cotizacion_flow` tiene `category="ventas"` | ✅ Revisar `coctl_flows.py:21` |
| 4 | Categorías sin valor muestran `"sin_categoria"` | ✅ Código `registry.py:116` |
| 5 | API agrupa flows por categoría correctamente | ✅ `get_flows_by_category()` |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Ciclo de dependencias no detectado | Baja | Alto | Validar en `_run_crew()` del orquestador antes de ejecutar |
| Metadata se pierde en restart | Baja | Medio | Documentar como limitación MVP; migrar a BD si se requiere persistence |
| Falta de documentación de categorías | Media | Bajo | Crear CONSTANTS en código o docs |

---

## 6. Plan

### Tareas Atómicas
| # | Tarea | Complejidad | Dependencia |
|----|------|------------|-------------|
| 1 | Verificar que registry actual acepta `depends_on` y `category` | Baja | — |
| 2 | Verificar endpoint `/flows/hierarchy` retorna metadata | Baja | 1 |
| 3 | Documentar cómo usar el decorador | Baja | 1 |
| 4 | Registrar todos los flows existentes con su metadata | Media | 1, 2 |

### Estado: El paso 4.1 ya está **IMPLEMENTADO** en código.
Los componentes necesarios existen y funcionan. Solo falta auditoría completa de flows existentes.

---

## 🔮 Roadmap (Post-MVP)

1. **Validación de ciclos**: Agregar check en `FlowRegistry.register()` queLance error si `depends_on` crea ciclo.
2. **Migración a BD**: Crear tabla `flow_metadata` con RLS por `org_id` si se requiere query offline.
3. **Constantes de categoría**: Definir lista válida de categorías (`ventas`, `facturacion`, `logistica`, etc.) como constants o enum.
4. **API de actualización**: Endpoints `PATCH /flows/{flow_type}/metadata` paramodificar sin código.

---

*Documento generado por el protocolo de Análisis de OC.*