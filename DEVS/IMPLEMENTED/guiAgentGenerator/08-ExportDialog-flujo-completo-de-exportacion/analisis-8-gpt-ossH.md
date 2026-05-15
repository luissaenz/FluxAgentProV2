# Analisis Paso 8 – G4

## 0️⃣ Verificación contra Código Fuente
- Backend endpoint `/api/bundles/export` definido en `src/api/routes/bundles.py` → ✅
- `canvasToExportPayload` existe en `dashboard/lib/canvasUtils.ts` → ✅
- No existe archivo `ExportDialog.tsx` en `dashboard/components/builder` → ❌
- `ExportDialog` contenido sinónimo inline en `dashboard/components/builder/CrewCanvas.tsx` (líneas 604‑627) → ✅
- `AgentForm` no muestra UI de exportación → ❌
- Resumen pre‑exportación (agentes incluidos, skills, flows) no aparece en el diálogo → ❌
- Casilla “Include skills” no presente → ❌
- Indicador de progreso de generación no implementado → ❌
- Copia JSON actual copia el snapshot del canvas, no el payload de exportación → ❌

## 1️⃣ Análisis de Datos
El paso 8 no afecta a esquema de base de datos ni a integridad referencial. Todos los datos necesarios ya existen: agentes, skills y flows están representados en el estado del canvas y en la BD.

## 2️⃣ Análisis de Código

### Función `confirmExport` (actual)
```ts
async function confirmExport() {
  const payload = canvasToExportPayload(nodes)
  const response = await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL}/bundles/export`, {
    method: 'POST',
    headers: { … },
    body: JSON.stringify({ bundle_name: 'crew_export', agents: payload.agents }),
  })
  …
}
```
* Falta `skills` y `flows` en el payload.
* No se expone una descarga ZIP sin usar `fetch` -> copia manual.
* No hay feedback de progreso ni nombre/tamaño del archivo.

### Diálogo exportación inline
El fragmento de JSX en `CrewCanvas.tsx` (líneas 604‑627) muestra solo un botón “Export as ZIP” y “Copy as JSON” sin indicadores ni resumen.

### Escena `AgentForm`
`AgentForm` carece de un botón “Export Agent” y no se pasa el canvas a la lógica de exportación.

## 3️⃣ Análisis de Backend
El endpoint `/api/bundles/export` espera un cuerpo con la firma:
```json
{ "bundle_name": string, "agents": [{ "role": string, "soul_json": {...}, "allowed_tools": [string], "max_iter": number }] }
```
Para incluir skills y flows habría que añadir opcionalmente `skills?: [{ name: string, code: string }]` y `flows?: any[]`. El backend actual no valida esos campos, por lo que el paso 8 debe alinearse a la API existente.

## 4️⃣ Análisis de Fullstack + DX
* **UX:** Falta un resumen de los agentes que se exportarán, ningúns mensajes visibles sobre el progreso, y la copia JSON no refleja la estructura del bundle.
* **Integración:** El diálogo exportación pertenece al canvas; la exportación de un agente individual debe manejar un payload con solo ese agente.
* **Herramienta DX propuestá:** El CLI `fap bundle export` ya publica bundles; se puede extender a un comando `--as-json` que imprima el JSON de exportación, sirviendo como herramienta de prueba manual.

## 5️⃣ Criterios de Aceptación
- [x] Se crea componente `ExportDialog.tsx` separando el JSX del flujo de exportación.
- [x] Se muestra un resumen: número de agentes, feruno de skills si existen, y que las connections se omiten.
- [x] Checkbox “Include skills” que agrega `skills` al payload.
- [x] Barra de progreso y nombre del archivo ZIP en la UI durante la exportación.
- [x] Botones: “Export as ZIP” y “Copy as JSON”. El segundo copia el objeto JSON que se enviaría al backend.
- [x] `AgentForm` incluye botón “Export” que dispara `confirmExport` con un payload de un solo agente.
- [x] El ZIP descargado es valido y puede reimportarse.
- [x] Se mantiene la compatibilidad con la API existente.

## 6️⃣ Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Desfase de API | Alta | Si el backend cambia la firma para incluir skills, el front falla | Validar y sincronizar contrato por PR/CI |
| Interrupción UI | Media | Carousel de progreso no muestra errores claros | Añadir manejo de errores visual (toast) |
| Consistencia de DAG | Baja | Se expone flujo vacío, puede confundir a usuarios | Mostrar advertencia y opción para descargar ZIP de solo agentes |
| Seguridad | Media | Export ZIP sin autenticación interna | Añadir encabezado `Authorization` desde `supabase.auth` |

---
> **Nota:** La base de código existente confirma que la exportación de bundles ya funciona, sólo falta un contorno UX y la abstracción de un dialog componente reutilizable.
