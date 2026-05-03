# 📝 Sugerencias pendientes

## Issues acumulados de validación — Paso 3: Tool Calling Real

### 🟡 Importantes
- **ID-001:** `proyecto-config.json` desactualizado — `phase_name: "testing"` en vez de `"Patch agents"`. Riesgo de confusión en pipeline. **Recomendación:** Actualizar `phase_name`, `current_step`, `steps_completed` para reflejar fase activa.

### 🔵 Mejoras
- **ID-002:** `excel_writer.py` imports no utilizados (`datetime`, `Any`, `Dict`, `List`, `Optional`) — F401 lint. Fuera de alcance Paso 3. Recomendación: limpiar imports en paso futuro.
- **ID-003:** `presupuesto_flow.py` import `BaseFlowState` sin usar (F401). Recomendación: remover import.

> Generado el 2026-05-03 desde validación Paso 3 — Fase activa: Patch agents
