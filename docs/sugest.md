# Sugerencias y Issues No Críticos

### 🟡 Importantes
- **ID-018-01:** [Paso 18] El documento `docs/estado-fase.md` no ha sido actualizado por el implementador para reflejar que el Paso 18 está completado. → Tipo: Documentación → Recomendación: Sincronizar el estado de fase tras la validación.
- **ID-019-01:** [Paso 19] Error de mapeo HTTP para versiones malformadas. Actualmente devuelve 409 Conflict vía `VersionConflictError`, pero debería ser 400 Bad Request por error de formato. → Tipo: Consistencia API → Recomendación: Diferenciar excepciones de formato vs. excepciones de lógica de negocio (downgrade).

### 🔵 Mejoras
- **ID-018-02:** [Paso 18] Considerar añadir logs de nivel INFO en `FlowRegistry.get` cuando ocurre un `_load_from_db` exitoso para facilitar el debugging de fallos de caché. → Recomendación: Añadir log descriptivo.
- **ID-019-02:** [Paso 19] Mejorar la granularidad de los mensajes de error en el Version Guard para incluir el nombre del bundle afectado, facilitando el troubleshooting en importaciones masivas. → Recomendación: Incluir `bundle_name` en el mensaje de la excepción.
