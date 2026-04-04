# FluxAgent Pro (FAP) — Fase 7: Capa de Presentación

**Documento de Definición Exhaustiva**
Versión 1.0 · Abril 2026

| Campo | Valor |
|-------|-------|
| Fase | 7 de 7 |
| Estado | En Definición |
| Tipo | UX / Plataforma |

---

## Tabla de Contenidos

1. [Contexto y Motivación](#1-contexto-y-motivación)
2. [Premisas Innegociables](#2-premisas-innegociables)
3. [Objetivo de la Fase](#3-objetivo-de-la-fase)
4. [Concepto Central: presentation_config](#4-concepto-central-presentation_config)
5. [Las Tres Vistas Estandarizadas](#5-las-tres-vistas-estandarizadas)
6. [Fallback Genérico para Agentes sin Presentación](#6-fallback-genérico-para-agentes-sin-presentación)
7. [Flujo Completo de la Capa de Presentación](#7-flujo-completo-de-la-capa-de-presentación)
8. [Cambios en agent_catalog](#8-cambios-en-agent_catalog)
9. [Migración de Agentes Existentes](#9-migración-de-agentes-existentes)
10. [Preguntas Abiertas y Deuda Técnica Consciente](#10-preguntas-abiertas-y-deuda-técnica-consciente)
11. [Plan de Implementación por Iteraciones](#11-plan-de-implementación-por-iteraciones)
12. [Criterios de Aceptación de la Fase](#12-criterios-de-aceptación-de-la-fase)

---

## 1. Contexto y Motivación

### 1.1 El problema: un sistema para desarrolladores, no para personas

FAP v1 a v6 construyeron una plataforma técnicamente sólida: event sourcing, flows robustos, aprobaciones human-in-the-loop, multi-tenancy. Sin embargo, la experiencia del supervisor —la persona que debe tomar decisiones operativas reales— quedó sin resolver.

La interfaz actual presenta al supervisor:

- Tarjetas en el Kanban que solo muestran un ID de tarea y un estado crudo
- Un detalle que al hacer clic despliega el JSON sin procesar del resultado del agente
- Datos como `{"opcion_recomendada": 5376757}` sin contexto, etiquetas ni jerarquía visual

> ⚠️ **Diagnóstico central**
>
> FAP v2 es técnicamente brillante pero operativamente frío. Un supervisor no puede tomar decisiones informadas con un JSON crudo. El sistema hoy es usable solo por el equipo que lo construyó.

### 1.2 La brecha entre el agente y el humano

Existe una brecha estructural en el flujo de información:

```
Agente ejecuta
    ↓
Produce JSON en tasks.result
    ↓
El Dashboard muestra... ese mismo JSON

Lo que el supervisor necesita ver:
⚠️ Cotización Boda 150pax — $5.376.757 → [APROBAR]
```

La Fase 7 cierra esa brecha con una capa de presentación declarativa, definida por agente, sin modificar el motor de CrewAI ni los datos almacenados en Supabase.

---

## 2. Premisas Innegociables

Toda decisión de diseño e implementación de esta fase debe respetar las siguientes premisas, que provienen de la arquitectura central de FAP y no son negociables:

| # | Premisa | Descripción | Implicancia en Fase 7 |
|---|---------|-------------|----------------------|
| **A** | Solo datos procesados por agentes en Supabase | En la base de datos solo existe información generada o procesada por los agentes. Ningún dato operativo propio de la organización (stock, precios base, nómina) reside en Supabase. | La presentación es **metadata del agente**, no dato operativo. Vive junto al agente en `agent_catalog`. |
| **B** | Cero modificaciones a CrewAI | Bajo ningún punto de vista se modificarán los archivos del proyecto CrewAI. El motor de ejecución es inmutable desde la perspectiva de FAP. | Los agentes siguen produciendo JSON puro. La presentación se aplica **client-side** en el Dashboard, nunca en el agente. |

> ✅ **Lo que NO cambia**
>
> - Los agentes siguen produciendo JSON en `tasks.result`
> - `tasks.result` sigue siendo JSONB sin restricciones de esquema
> - CrewAI no se toca bajo ninguna circunstancia
> - Los datos operativos (stock, precios) no existen en Supabase
> - Los botones de aprobación (Aprobar / Rechazar) permanecen **fuera** del detalle, en el contenedor del Dashboard

---

## 3. Objetivo de la Fase

Dotar a FAP de una capa de presentación estándar que permita a cualquier agente definir cómo se muestra su output al supervisor, transformando la experiencia de un panel de depuración para desarrolladores en una interfaz operativa para personas.

### 3.1 Objetivos específicos

1. Definir un estándar declarativo de presentación (`presentation_config`) que cualquier agente pueda adoptar de forma optativa.
2. Implementar tres vistas estandarizadas: **Card**, **Compacta** y **Detalle**.
3. Implementar un fallback genérico inteligente para agentes sin presentación definida.
4. Integrar `presentation_config` como columna de `agent_catalog` en Supabase, sin alterar la estructura de `tasks`.
5. Migrar los agentes existentes de CoctelPro (4 agentes) y Bartenders NOA (11 agentes) con sus presentaciones correspondientes.

### 3.2 Fuera del alcance de esta fase

- Presentación dinámica por tipo de resultado (un mismo agente, múltiples esquemas de output)
- Agente ReAct como presentador universal (opción futura, Fase 8+)
- Edición de `presentation_config` por supervisores desde el Dashboard
- Presentación diferenciada por estado del flow
- Versionado de configuraciones de presentación

---

## 4. Concepto Central: `presentation_config`

### 4.1 Definición

`presentation_config` es un campo JSONB que se agrega a la tabla `agent_catalog`. Define de forma declarativa cómo el Dashboard debe transformar el JSON producido por el agente (`tasks.result`) en una interfaz visual legible para el supervisor.

Es **metadata del agente**, no dato de negocio. Tiene el mismo estatus conceptual que `soul_json` (personalidad), `allowed_tools` (herramientas) o `max_iter` (límite de iteraciones): forma parte de la definición del agente, no de su ejecución.

### 4.2 Dónde vive

| Campo existente | Propósito | Quién lo usa |
|-----------------|-----------|--------------|
| `soul_json` | Personalidad y reglas rígidas del agente | CrewAI al inicializar el agente |
| `allowed_tools` | Herramientas permitidas | FAP Tool Proxy |
| `model` | LLM backend | Runtime de ejecución |
| `max_iter` | Límite de iteraciones | CrewAI |
| `presentation_config` ← **NUEVO** | Cómo mostrar el output al supervisor | Dashboard (client-side únicamente) |

> 💡 **Principio de separación de responsabilidades**
>
> El agente **produce** datos. El Dashboard **presenta** datos.
> `presentation_config` es el contrato entre ambos.
> CrewAI nunca ve este campo. Solo lo usa el Dashboard.

### 4.3 Opcionalidad y fallback

La capa de presentación es **optativa** para todos los agentes. Esta decisión responde a que ciertos agentes son "invisibles" operativamente: son nodos intermedios de un pipeline, agentes ReAct autónomos, o agentes cuyo output nunca necesita revisión humana directa.

| Tipo de agente | Tiene `presentation_config` | Justificación |
|----------------|----------------------------|---------------|
| Agente Ventas (CoctelPro) | ✅ Sí | Su output requiere aprobación del supervisor |
| Agente Logística (CoctelPro) | ✅ Sí | Genera compras que requieren autorización |
| Agente ReAct de parsing interno | ❌ No (recomendado) | Output intermedio, nunca visto por supervisor |
| Agente de monitoreo autónomo | ❌ No (opcional) | Actúa sin intervención humana |

---

## 5. Las Tres Vistas Estandarizadas

### 5.1 Tabla comparativa

| Vista | Dónde se usa | Tamaño | Propósito principal |
|-------|-------------|--------|---------------------|
| **Card** | Tablero Kanban (columnas) | 1 línea, máx. 60 caracteres | Decisión rápida: ¿necesito mirar esto? |
| **Compacta** | Historial de tareas / Listados | 1 línea con más campos | Escaneo rápido de múltiples tareas pasadas |
| **Detalle** | Pantalla dedicada al hacer clic | Completa, con secciones y estructura | Acción informada: entender, aprobar, rechazar |

---

### 5.2 Vista Card

#### Propósito

La Card es lo que el supervisor ve en el tablero Kanban junto a otras 15-20 tareas. Debe responder en menos de 2 segundos la pregunta: ¿necesito atender esto ahora?

#### Estructura

```
Formato:  {icono_estado} {titulo} — ${monto_principal}
Ejemplo:  ⚠️ Cotización Boda 150pax — $5.376.757
Límite:   60 caracteres incluyendo icono
```

#### Definición en `presentation_config`

```yaml
card:
  icon:
    from: "$.status"
    map:
      pending_approval: "⚠️"
      completed:        "✅"
      failed:           "❌"
      running:          "🔄"
  title:
    from: "$.evento_nombre"
  amount:
    from: "$.precio_recomendado"
    format: "currency_ars"
```

> 🔍 **Nota sobre la resolución de campos**
>
> Los campos usan **JSONPath** (`$.campo` o `$.objeto.campo`) sobre `tasks.result`.
> Esto es más explícito y predecible que un sistema de template strings con aliases.
> Si el campo no existe en el resultado, se aplica el fallback de la vista Card.

---

### 5.3 Vista Compacta

#### Propósito

Se usa en la sección de Historial o en listados de tareas completadas. El supervisor necesita escanear múltiples entradas y entender de un vistazo qué ocurrió, cuándo y con qué resultado.

#### Estructura

```
Formato:  {fecha} │ {tipo_flow} │ {titulo} │ ${monto} │ {estado} │ {actor}
Ejemplo:  15/01/2026 14:30 │ Cotización │ Boda 150pax │ $5.376.757 │ Aprobada │ Juan
```

#### Definición en `presentation_config`

```yaml
compact:
  fields:
    - from: "$.created_at"          format: "datetime_short"
    - from: "$.flow_type"           label: "Tipo"
    - from: "$.evento_nombre"
    - from: "$.precio_recomendado"  format: "currency_ars"
    - from: "$.approval_status"
    - from: "$.approved_by_name"
```

Si `compact` no está definido pero `card` sí existe, el Dashboard construye la vista compacta a partir de la card con campos adicionales del contexto de la tarea (fecha, estado, actor de aprobación). Si ninguna está definida, se aplica el fallback genérico.

---

### 5.4 Vista Detalle

#### Propósito

Es la pantalla completa que el supervisor ve al hacer clic en una Card. Aquí se toma la decisión de aprobar, rechazar o escalar. Debe proveer toda la información necesaria, bien organizada, sin requerir que el supervisor interprete JSON.

#### Anatomía de la vista Detalle

```
┌─────────────────────────────────────────────────────────────┐
│ [Breadcrumb: Kanban > Cotizaciones > Boda Juan y María]     │
├─────────────────────────────────────────────────────────────┤
│  SECCIÓN 1 (type: fields)    ← Datos del evento             │
│  SECCIÓN 2 (type: table)     ← Tabla de opciones            │
│  SECCIÓN 3 (type: accordion) ← Escandallo (colapsado)       │
│  SECCIÓN 4 (type: key_value_list) ← Ajustes aplicados       │
├─────────────────────────────────────────────────────────────┤
│  [BOTONES: Aprobar] [Rechazar] [Modificar]  ← FUERA         │
│  Los botones los renderiza el contenedor del Dashboard       │
└─────────────────────────────────────────────────────────────┘
```

#### Tipos de sección disponibles

| Tipo | Descripción | Caso de uso típico |
|------|-------------|-------------------|
| `fields` | Lista de pares etiqueta-valor en formato ficha | Datos del evento, resumen de cliente |
| `table` | Tabla con columnas y filas configurables, con resaltado de fila recomendada | Comparación de opciones de precio/margen |
| `accordion` | Sección colapsada por defecto con expand bajo demanda | Desglose técnico, escandallo de costos |
| `key_value_list` | Lista de items con nombre y valor sin cabecera | Ajustes aplicados, factores de corrección |

#### Ejemplo de definición completa — Agente Ventas (CoctelPro)

```yaml
detail:
  sections:
    - type: fields
      title: "📋 Evento"
      fields:
        - label: "Evento"     from: "$.evento_nombre"
        - label: "Fecha"      from: "$.fecha"         format: "date"
        - label: "Pax"        from: "$.pax"
        - label: "Provincia"  from: "$.provincia"
        - label: "Menú"       from: "$.menu_tipo"

    - type: table
      title: "💰 Cotización"
      from: "$.opciones"
      highlight_where: "$.recommended == true"
      columns:
        - label: "Opción"   from: "$.nombre"
        - label: "Margen"   from: "$.margen"   format: "pct"
        - label: "Precio"   from: "$.precio"   format: "currency_ars"

    - type: accordion
      title: "📊 Escandallo (base)"
      default: collapsed
      from: "$.escandallo"
      render_as: key_value_list

    - type: key_value_list
      title: "🔍 Ajustes aplicados"
      from: "$.ajustes"
```

---

## 6. Fallback Genérico para Agentes sin Presentación

### 6.1 Filosofía del fallback

El fallback **no debe ser** un blob de JSON con syntax highlighting. Eso es útil para un desarrollador en modo debug, pero inutilizable para un supervisor operativo. El fallback debe ser la representación más legible posible del resultado sin requerir ninguna configuración.

### 6.2 Comportamiento por vista

| Vista | Fallback si NO hay `presentation_config` |
|-------|------------------------------------------|
| **Card** | `{flow_type}: {status}`   Ej: `cotizacion_flow: pending_approval` |
| **Compacta** | `{created_at} │ {flow_type} │ {status}` |
| **Detalle** | Ficha automática key/value de todos los campos del JSON (ver 6.3) |

### 6.3 Detalle del fallback para la vista Detalle

En lugar de mostrar JSON crudo, el Dashboard construye automáticamente una ficha legible:

```
┌────────────────────────────────────────────────────┐
│ 📄 RESULTADO DEL AGENTE                            │
├──────────────────────┬─────────────────────────────┤
│ evento_nombre        │ Boda de Juan y María        │
│ precio_recomendado   │ 5376757                     │
│ pax                  │ 150                         │
│ provincia            │ Tucumán                     │
│ menu_tipo            │ Premium                     │
└──────────────────────┴─────────────────────────────┘

Sin JSON crudo. Sin syntax highlighting de código.
Tabla de dos columnas: campo | valor.
```

> 🎯 **Por qué esto importa**
>
> El fallback inteligente tiene costo de implementación casi cero. Sin embargo, transforma inmediatamente la experiencia para **todos** los agentes, incluso aquellos que aún no tienen `presentation_config` definido. Es la primera victoria rápida de la fase.

---

## 7. Flujo Completo de la Capa de Presentación

### 7.1 Diagrama de flujo

```
 1. Agente ejecuta via CrewAI
      ↓
 2. Produce JSON en tasks.result (JSONB en Supabase)
      ↓
 3. Dashboard recibe notificación (Supabase Realtime)
      ↓
 4. Dashboard consulta:
      a) tasks.result              → el output del agente
      b) agent_catalog.presentation_config → las plantillas
      ↓
 5. ¿Tiene presentation_config?
      SÍ → aplica plantilla Card / Compact / Detail
      NO → aplica fallback genérico inteligente
      ↓
 6. Supervisor ve información entendible en el Kanban
      ↓
 7. Supervisor hace clic → ve vista Detalle
      ↓
 8. Supervisor toma acción (botones fuera del detalle)
      ↓
 9. Dashboard llama POST /approvals/{task_id}
      ↓
10. Flow reanuda. El agente NUNCA supo cómo se mostró.
```

### 7.2 Lo que el agente nunca conoce

El agente es completamente agnóstico a la presentación. Esto es una propiedad de diseño intencional:

- El agente produce JSON. Siempre. Sin cambios.
- No sabe en qué vista se mostrará su output (Card, Detalle, fallback).
- No sabe si hay un supervisor mirando o si la tarea es parte de un pipeline automatizado.
- `presentation_config` es leída únicamente por el Dashboard en el momento de renderización.

---

## 8. Cambios en `agent_catalog`

### 8.1 Nueva columna

```sql
ALTER TABLE agent_catalog
  ADD COLUMN presentation_config JSONB DEFAULT NULL;

-- NULL  = sin presentación definida → usar fallback
-- {}    = presentación vacía (equivalente a NULL)
```

### 8.2 Esquema JSON de `presentation_config`

El campo acepta cualquier combinación de las tres vistas. Todas son opcionales:

```json
{
  "card": {
    "icon": {
      "from": "$.status",
      "map": {
        "pending_approval": "⚠️",
        "completed": "✅",
        "failed": "❌",
        "running": "🔄"
      }
    },
    "title":  { "from": "$.evento_nombre" },
    "amount": { "from": "$.precio_recomendado", "format": "currency_ars" }
  },

  "compact": {
    "fields": [
      { "from": "$.created_at",          "format": "datetime_short" },
      { "from": "$.evento_nombre" },
      { "from": "$.precio_recomendado",  "format": "currency_ars" }
    ]
  },

  "detail": {
    "sections": [
      // ... ver sección 5.4
    ]
  }
}
```

### 8.3 Formatos de valor disponibles

| Formato | Descripción | Ejemplo de output |
|---------|-------------|-------------------|
| `currency_ars` | Moneda Argentina con separadores de miles | `$5.376.757` |
| `currency_usd` | Moneda USD | `USD 3.720` |
| `pct` | Porcentaje | `45%` |
| `date` | Fecha local (dd/mm/yyyy) | `15/01/2026` |
| `datetime_short` | Fecha y hora corta | `15/01 14:30` |
| `boolean_yn` | Booleano como Sí/No | `Sí` |
| *(sin format)* | Valor crudo como string | `Tucumán` |

---

## 9. Migración de Agentes Existentes

### 9.1 Agentes en scope

| Sistema | Agentes | Tiene output visible por supervisor |
|---------|---------|-------------------------------------|
| CoctelPro Events | 4 agentes | Sí (cotizaciones, compras, eventos) |
| Bartenders NOA | 11 agentes | Parcial (algunos son pipelines internos) |

### 9.2 Criterio de priorización

| Prioridad | Criterio | Acción |
|-----------|----------|--------|
| **P0 — Crítico** | El agente produce output que requiere aprobación humana directa | Definir `card` + `detail` completo |
| **P1 — Importante** | El agente produce output consultado frecuentemente en historial | Definir `card` + `compact` |
| **P2 — Opcional** | Agente de pipeline interno, output técnico o intermedio | Dejar en fallback genérico |

### 9.3 Agentes CoctelPro — presentación propuesta

#### Agente Ventas
- **Prioridad:** P0
- **Output típico:** cotización con 3 opciones de precio y margen
- **Vistas:** `card` + `compact` + `detail` completo con tabla de opciones y acordeón de escandallo

#### Agente Logística
- **Prioridad:** P0
- **Output típico:** lista de compras con cantidades, precios y proveedores sugeridos
- **Vistas:** `card` + `compact` + `detail` con tabla de ítems

#### Agente Finanzas
- **Prioridad:** P1
- **Output típico:** resumen financiero del evento (ingresos, costos, margen real)
- **Vistas:** `card` + `compact` + `detail` con secciones de ingresos y egresos

#### Agente Coordinación
- **Prioridad:** P2
- **Output típico:** log de coordinación entre agentes
- **Vistas:** fallback genérico es suficiente

---

## 10. Preguntas Abiertas y Deuda Técnica Consciente

### 10.1 Preguntas abiertas a resolver antes de implementar

| # | Pregunta | Impacto si no se responde | Propuesta provisional |
|---|----------|--------------------------|----------------------|
| 1 | ¿Quién puede editar `presentation_config` en producción? | Cuello de botella si solo el developer puede | Solo rol `admin_org` o `developer`; no supervisores en v1 |
| 2 | ¿Hay versionado de `presentation_config`? | Un cambio en el output del agente puede romper una presentación existente | Sin versionado en Fase 7; se agrega como mejora en Fase 8 |
| 3 | ¿Cómo genera `presentation_config` el ArchitectFlow? | El agente que crea agentes no sabrá cómo completar este campo | El ArchitectFlow deja `presentation_config` en `NULL` por defecto; el developer lo completa manualmente post-creación |
| 4 | ¿Cómo se valida que los JSONPath referencian campos que existen en el output real? | Pantallas rotas en producción difíciles de diagnosticar | Validación client-side con advertencia visible; no bloquea el guardado |

### 10.2 Deuda técnica consciente (fuera de Fase 7)

| Item | Descripción | Fase sugerida |
|------|-------------|---------------|
| Presentación por tipo de resultado | Un mismo agente con múltiples esquemas de output según contexto | Fase 8 |
| Agente ReAct presentador universal | Un agente autónomo que genera presentaciones sobre la marcha para cualquier JSON | Fase 8+ |
| Versionado de `presentation_config` | Registro histórico de cambios en la presentación con rollback | Fase 8 |
| Editor visual de presentaciones | Interfaz para que el admin construya presentaciones sin editar JSON | Fase 9 |
| Edición por supervisores | Permitir que supervisores ajusten etiquetas y orden sin acceso técnico | Fase 9 |

---

## 11. Plan de Implementación por Iteraciones

Se propone una secuencia en 4 iteraciones para evitar el riesgo de diseñar un estándar perfecto sin validación real.

---

### Iteración 1 — Fallback inteligente *(quick win)*

**Costo:** bajo. **Ganancia:** inmediata para todos los agentes.

- Implementar la ficha key/value automática en la vista Detalle para cualquier `tasks.result`
- Reemplazar el JSON con syntax highlighting por la tabla de dos columnas etiqueta/valor
- Actualizar la Card en Kanban para mostrar `flow_type` + `status` de forma legible en lugar del ID crudo

> 🎯 **Criterio de éxito:** Un supervisor sin formación técnica puede entender qué hizo cualquier agente sin asistencia.

---

### Iteración 2 — Card configurable

**Costo:** medio. **Ganancia:** mejora visible en el Kanban diario.

- Agregar columna `presentation_config` a `agent_catalog`
- Implementar parser de la sección `card` en el Dashboard
- Definir y cargar la `card` del Agente Ventas (CoctelPro) como caso piloto
- Validar que se muestra correctamente en el Kanban

> 🎯 **Criterio de éxito:** La Card del Agente Ventas muestra: `⚠️ Cotización [Nombre Evento] — $[Monto]`

---

### Iteración 3 — Detalle configurable *(piloto único)*

**Costo:** alto. Se implementa solo para el Agente Ventas de CoctelPro antes de generalizar.

- Implementar el renderer de secciones (`fields`, `table`, `accordion`, `key_value_list`)
- Definir la presentación completa del Agente Ventas en `presentation_config`
- Validar con un usuario real (supervisor de CoctelPro) que la vista es operativamente útil
- Iterar sobre el diseño según feedback **antes** de generalizar

> 🎯 **Criterio de éxito:** El supervisor de CoctelPro puede aprobar o rechazar una cotización sin abrir un JSON. Al menos 1 usuario no técnico valida que la vista es clara y suficiente.

---

### Iteración 4 — Migración general

**Costo:** medio (es trabajo de definición, no de código). Con el renderer ya implementado:

- Definir `presentation_config` para los 4 agentes de CoctelPro
- Definir `presentation_config` para los agentes P0 y P1 de Bartenders NOA
- Dejar agentes P2 con fallback genérico
- Documentar el estándar para futuros agentes

> 🎯 **Criterio de éxito:** Todos los agentes con interacción humana tienen Card y Detalle configurados.

---

## 12. Criterios de Aceptación de la Fase

| # | Criterio | Verificación |
|---|----------|-------------|
| 1 | Un supervisor sin formación técnica puede entender el output de cualquier agente en menos de 10 segundos | Test con usuario real |
| 2 | La Card del Kanban muestra información de negocio, no IDs ni JSON | Inspección visual |
| 3 | El Detalle de un agente con `presentation_config` completo no contiene ningún JSON visible para el supervisor | Inspección visual |
| 4 | El fallback genérico muestra una ficha key/value, no JSON con syntax highlighting | Inspección visual |
| 5 | Los botones de acción (Aprobar / Rechazar) **NO** son parte de `presentation_config` | Revisión de código |
| 6 | CrewAI no fue modificado en ningún archivo | Revisión de código |
| 7 | `tasks.result` sigue siendo JSONB sin restricciones de esquema | Revisión de schema |
| 8 | `presentation_config` es `NULL` por defecto y el sistema funciona correctamente sin ella | Test automatizado |

---

> 📌 **Resumen ejecutivo**
>
> La Fase 7 agrega una capa de presentación declarativa a FAP. Cada agente **puede** definir (optativamente) cómo se muestra su output en 3 vistas. La presentación vive en `agent_catalog` como metadata, invisible para CrewAI. Los datos en Supabase no cambian. `tasks.result` sigue siendo JSON puro. El Dashboard aplica la presentación client-side al momento de renderizar. Un fallback inteligente garantiza legibilidad para todos los agentes desde el día 1. Los botones de acción son responsabilidad del contenedor del Dashboard, no de la presentación.

---

*— Fin del documento —*
