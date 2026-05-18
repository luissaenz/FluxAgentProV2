# 🏛️ ANÁLISIS TÉCNICO UNIFICADO — Paso 12: Protocolo de Validación y Dogfooding E2E

**Fase:** `guiAgentGenerator`  
**Paso:** 12 — Protocolo de Validación y Dogfooding E2E  
**Estado:** 🏛️ UNIFICADO Y FINAL (Fuente de verdad para la implementación)  
**Fecha:** 2026-05-18  

---

### 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

#### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **dsp** | ✅ (36 items) | 5 (D1, D2, D3, D4, D5) | ✅ `fap validate-dogfood` | ✅ Sí (Múltiples archivos y líneas exactas) | **4.9** |
| **step** | ✅ (30 items) | 3 (SSR, loop, dry-run) | ✅ `fap dogfood check` | ✅ Sí (Session, config, RLS policies) | **4.5** |
| **qwen3.6** | ✅ (22 items) | 5 (API bypass, DB verify, SSR, seed) | ✅ `fap dogfood run` + `dogfood_validator.py` | ✅ Sí (Detalle de contratos y schemas Pydantic) | **4.4** |
| **ds4f** | ✅ (21 items) | 3 (Tools, templates, regex bug) | ✅ `fap validate api-contracts` | ✅ Sí (Líneas de CLI y scripts detectados) | **4.2** |
| **lgn** | ✅ (25 items) | 2 (Loop, SSR mismatch) | ✅ `fap dogfood check` | ✅ Sí (Estructuras de comandos y migraciones) | **4.0** |

*Nota del Arquitecto:* El agente **dsp** proveyó el análisis más exhaustivo y técnicamente brillante de la suite, detectando el fallo estructural en el script de navegación donde la variable `uses_navmain` se calculaba pero jamás se utilizaba en la lógica de decisión final. El agente **ds4f** fue el único que identificó la causa exacta del bug de regex (doble-escape de caracteres).

#### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **Bug de decisión en `validate_builder_nav.py`** | **dsp** | ✅ `scripts/validate_builder_nav.py:65-70` | La variable `uses_navmain` se define pero no se usa en el check. Se reescribe la decisión para que requiera `uses_navmain == True`. |
| 2 | **Regex roto en `validate_builder_nav.py`** | **ds4f**, **dsp** | ✅ `scripts/validate_builder_nav.py:65` | `"items={\\s*defaultNavItems}"` hace match literal inútil. Se cambia por `re.search(r'items\s*=\s*\{\s*defaultNavItems\s*\}', content)`. |
| 3 | **Falso negativo SSR en `validate_builder_nav.py`** | **lgn**, **step** | ✅ `scripts/validate_builder_nav.py:160-176` | Busca `BuilderCanvas` pero el componente real en `BuilderLayout.tsx` es `CrewCanvas`. Se corrige para buscar `CrewCanvas` y `{ ssr: false }`. |
| 4 | **Bypass HTTP en herramientas de Dogfooding** | **ds4f**, **dsp**, **qwen3.6** | ✅ `src/cli/commands/tools_list.py`, `templates_seed.py` | 5 de 7 comandos CLI consultan DB directamente en vez de pasar por los endpoints HTTP REST. Se resuelve integrando validación cruzada en la herramienta DX orquestadora para forzar el dogfooding HTTP. |
| 5 | **Async Event Loop warning en CLI** | **dsp**, **lgn**, **step** | ⚠️ `src/cli/commands/tools_list.py:141` | `asyncio.new_event_loop()` es un antipatrón en entornos asíncronos. Se documenta como riesgo para mitigarse en Paso 13, no bloquea Paso 12. |

---

### 1️⃣ Resumen Ejecutivo

- **Objetivo del paso:** Validar rigurosamente la suite completa de creación y exportación visual de agentes (`guiAgentGenerator`) utilizando las herramientas CLI y scripts estáticos del sistema. Asegura la total consistencia de contratos entre Base de Datos, Endpoints HTTP, interfaces CLI y la UI del Dashboard.
- **Correcciones críticas al plan original:** 
  1. Se corrigen de inmediato tres fallos críticos en el script estático de validación `scripts/validate_builder_nav.py` (cálculo de variable inútil, regex roto y nombre de componente SSR incorrecto).
  2. Se expone la desincronización de contratos HTTP: la mayoría de los comandos CLI puentean la API y van directo a Base de Datos.
- **Decisión sobre herramienta DX seleccionada:** Se fusionan todas las propuestas en un único orquestador robusto llamado **`fap dogfood check`**. Este comando ejecutará de manera secuencial los 8 flujos de validación (incluyendo comparación de contratos HTTP vs CLI local, verificación RLS, polling de tareas y validación de UI), reportando un estado verde consolidado y generando un informe Rich detallado.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path
Secuencia completa de validación end-to-end:
1. **Verificación DX Diagnóstica:** Se ejecuta `fap doctor builder` para confirmar que los 6 fixes de arquitectura están estables.
2. **Sembrado Idempotente:** Se ejecuta `fap templates seed` para poblar el catálogo de templates del sistema.
3. **Validación de Catálogos:** Se listan las herramientas disponibles (`fap tools list`) y se valida que el endpoint `/api/tools/available` retorne idéntico contenido.
4. **Mapeo de Plantillas:** Se realiza el dry-run del uso de templates (`fap templates use --dry-run`) para los 8 templates del sistema, verificando la generación correcta de payloads.
5. **Creación de Agente:** Se crea un agente a través del CLI (`fap agent create`) y se verifica su persistencia en `agent_catalog` mediante verificación de API.
6. **Ejecución en Tiempo Real (Playground):** Se ejecuta el agente creado (`fap agent run`) y se realiza polling síncrono al backend hasta recibir el estado terminal.
7. **Exportación y Esquema:** Se valida el payload de exportación completo (`fap bundle validate-payload`) asegurando la integridad estructural.
8. **Validación UI:** Se ejecuta el script `validate_builder_nav.py` para asegurar que el frontend Next.js tiene correctamente cableados sus skeletons, breadcrumbs y boundaries.

#### Edge Cases MVP
- **Conflicto de Rol Existente:** Si se intenta crear un agente cuyo rol ya existe para esa organización, el endpoint `/agents` debe resolverlo mediante un `upsert` transparente en lugar de lanzar una excepción de base de datos.
- **Idempotencia de Templates:** Correr `fap templates seed` de manera concurrente debe ignorar duplicados de IDs mediante UUID v5 determinista.
- **Degradación Grácil de MCP:** Si un servidor MCP no está disponible o falla, `fap tools list` y el endpoint `/api/tools/available` deben registrar advertencias en logs y continuar devolviendo las herramientas locales en lugar de arrojar un error 500.
- **Validación de Cadenas en Exportación:** El endpoint de exportación (`POST /api/bundles/export`) debe retornar 422 si el campo `goal` o `backstory` de cualquier agente tiene una longitud inferior a 10 caracteres.

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

##### 1. Modificación de `scripts/validate_builder_nav.py`
- **Ruta real:** `scripts/validate_builder_nav.py`
- **Tipo de cambio:** Modificación / Bugfix
- **Descripción:** Corrección de la lógica de decisión de `check_sidebar_ssot` y de la detección de SSR.
- **Modificación exacta en `check_sidebar_ssot`:**
```python
# Reemplazar la búsqueda por substring inútil:
# uses_navmain = "items={\\s*defaultNavItems}" in content
# Por búsqueda regex correcta:
uses_navmain = bool(re.search(r'items\s*=\s*\{\s*defaultNavItems\s*\}', content))

# Usar la variable en la decisión:
if not uses_navmain:
    print_check_result("B", "NavMain en app-sidebar.tsx recibe items={defaultNavItems}", False, "Falta prop items={defaultNavItems} en NavMain")
    errors += 1
else:
    print_check_result("B", "NavMain en app-sidebar.tsx recibe items={defaultNavItems}", True)
```
- **Modificación exacta en `check_ssr_false`:**
```python
# Cambiar la búsqueda de BuilderCanvas a CrewCanvas que es el componente real:
if "CrewCanvas" not in content or "ssr: false" not in content:
    print_check_result("E", "Componente CrewCanvas cargado dinámicamente con ssr: false", False, "Falta CrewCanvas o ssr: false en dynamic import")
    errors += 1
else:
    print_check_result("E", "Componente CrewCanvas cargado dinámicamente con ssr: false", True)
```

##### 2. Creación del comando de validación `fap dogfood check`
- **Ruta real:** `src/cli/commands/dogfood_check.py` (registrado en `src/cli/main.py`)
- **Tipo de cambio:** Creación (DX Tool)
- **Descripción:** Comando unificado que automatiza toda la secuencia de validaciones cruzadas.
- **Firmas clave:**
```python
@dogfood_app.command("check")
def dogfood_check(
    org_id: str = typer.Option(..., "--org-id", "-o", help="Org ID para validaciones"),
    json_output: bool = typer.Option(False, "--json", help="Generar reporte en formato JSON para CI/CD"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo previsualizar pasos")
) -> None
```

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap dogfood check
- **Qué automatiza:** Orquesta y ejecuta en orden: fap doctor builder + fap templates seed + fap tools list (comparado con HTTP REST) + fap templates use (dry-run) + fap agent create (dry-run & real) + fap bundle validate-payload + validate_builder_nav.py.
- **Tipo:** Comando CLI (Typer)
- **Ubicación:** src/cli/commands/dogfood_check.py
- **Cómo se usa:** uv run fap dogfood check --org-id <org-uuid>
- **Impacto para el usuario final:** Reduce el tiempo de verificación de 15 minutos de comandos manuales y comparación de consola visual a solo 10 segundos con un reporte Rich interactivo y código de salida compatible con CI/CD.
- **El implementador DEBE usarla** para completar la validación integrada final de todo el paso.
```

---

### 4️⃣ Decisiones Tecnológicas

1. **Unificación en `fap dogfood check`:** Se descarta la creación de scripts independientes y dispersos (como `dogfood_validator.py`). Unificar las pruebas de contrato HTTP, diagnósticos del doctor y tests estáticos en un solo comando CLI optimiza drásticamente el DX y centraliza el mantenimiento.
2. **Validación Cruzada HTTP vs CLI:** Para resolver el bypass de la API de los comandos locales, `fap dogfood check` consumirá directamente los endpoints `GET /api/tools/available` y `GET /api/templates` usando un `httpx.Client` y comparará estructuralmente los resultados con las respuestas de las funciones del core local.
3. **No-mocking en Dogfooding:** A diferencia de la suite de tests E2E que usa mocks globales de LLM, el protocolo dogfooding requiere conectividad real con Supabase y el API REST activo para verificar la persistencia de producción.

---

### 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Tabla `agent_templates` poblada con 8 templates de sistema mediante semilla idempotente.
✅ [DATA] Tabla `agent_catalog` persiste de manera segura los registros creados sin lanzar excepciones por duplicación.
✅ [CODE] CLI `fap tools list` y `fap templates seed/use` se ejecutan sin errores y soportan flags `--dry-run`.
✅ [CODE] Comando `fap bundle validate-payload` rechaza payloads con goal/backstory < 10 caracteres con advertencias claras.
✅ [BACKEND] Endpoint `GET /api/tools/available` responde estructuradamente bajo el modelo `ToolsListResponse`.
✅ [BACKEND] Endpoint `GET /api/templates` y `GET /api/templates/{id}` son públicos (sin auth) y soportan filtro `?category=`.
✅ [BACKEND] Endpoint `POST /agents/{role}/run` despacha tareas asíncronas y permite polling en `/tasks/{task_id}`.
✅ [FULLSTACK] El script `validate_builder_nav.py` reporta exit code 0 con verificación AST/Regex corregida de 5 checks críticos.
✅ [DX] Herramienta `fap dogfood check` ejecuta el flujo completo de validaciones cruzadas y retorna exit code 0 ante éxito.
```

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Implementar comando `fap dogfood check` | Media | 2.5h | Ninguna |
| 1 | **Bugfix:** Corregir regex, SSR y lógica en `validate_builder_nav.py` | Baja | 0.5h | Ninguna |
| 2 | **Validación HTTP:** Cablear comparación de REST API vs CLI en comando `check` | Media | 1.0h | Tarea 0 |
| 3 | **Ciclo E2E Dogfood:** Orquestar flujo completo de extremo a extremo | Media | 1.5h | Tarea 2, Tarea 1 |
| 4 | **Evidencia:** Ejecución de suite dogfood unificada y generación de reporte HTML | Baja | 0.5h | Tarea 3 |
| **TOTAL** | | | **6.0h** | |

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| **R1:** Inconsistencia por Bypass de HTTP | Alta | Los comandos locales leen DB directamente. Si la serialización Pydantic de la API cambia, el CLI no se entera. | `fap dogfood check` compara dinámicamente las respuestas directas de DB de los comandos con los endpoints REST reales. |
| **R2:** Bloqueo por timeout de LLM real | Media | `fap agent run` ejecuta agentes con APIs reales. El timeout por defecto de 120s podría ser insuficiente. | Configurar el timeout en 300 segundos durante la corrida de dogfooding, o proveer flag `--mock-llm` en el comando. |
| **R3:** Desincronización estática de UI Next.js | Baja | Cambios en el dashboard de Next.js rompen paths de `validate_builder_nav.py`. | Declarar las rutas de archivos Next.js como constantes globales bien documentadas en el encabezado del script. |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| **TP-1** | Ejecución de `fap dogfood check` | `uv run fap dogfood check --org-id test-org` | Tabla Rich consolidada, todos los pasos `[PASS]`, exit code 0. |
| **TP-2** | Fallo por API desincronizado (Bypass) | Alterar serialización de `GET /api/tools/available` | El comando detecta la discrepancia estructural y reporta `[FAIL]` en Tarea 3, exit code 1. |
| **TP-3** | NavMain sin prop `items` | Quitar prop `items` en `app-sidebar.tsx` | `validate_builder_nav.py` detecta el error en check B, reporta error y retorna exit 1. |

Comandos para validaciones directas:
- Ejecución completa: `uv run fap dogfood check --org-id <org-uuid>`
- Ejecución de integridad Next.js: `uv run python scripts/validate_builder_nav.py`
