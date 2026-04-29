# Sugerencias y Issues No Críticos

## 🟡 Importantes
- **ID-V01:** [Paso 2] El comando `dev` asume que el archivo ZIP se genera en el directorio padre o en el CWD. Podría ser más robusto si `package_bundle` devolviera la ruta exacta del archivo generado. → Tipo: Estabilidad → Recomendación: Refactorizar `package_bundle` para retornar el path del ZIP.
- **ID-V04:** [Paso 3] Inconsistencia en Naming de Tools Locales. La `LocalExecutor` registra tools usando el nombre del archivo, pero los agentes podrían usar el nombre de la clase. → Tipo: Estabilidad → Recomendación: Normalizar el registro para incluir ambos nombres en el registry transiente.
- **ID-V06:** [Paso 4] Inconsistencia de esquemas de `manifest.json`. `fap scaffold` genera el esquema v2.0 correcto (`bundle_info`), pero `fap init` y `fap package` siguen usando el esquema viejo (root keys). → Recomendación: Unificar toda la lógica en `src/utils/bundle_utils.py` y actualizar `init.py` y `package.py`.
- **ID-V07:** [Paso 4] Error de encoding `UnicodeEncodeError` en Windows. El uso de emojis (✅, ⚠️) en la salida de `rich` rompe la ejecución en terminales con encoding CP1252. → Recomendación: Eliminar emojis o forzar salida ASCII en Windows.
- **ID-V08:** [Paso 4] Fallo de Linting. `src/utils/bundle_utils.py` tiene imports no utilizados (`List`, `Optional`) y desordenados. → Recomendación: Ejecutar `npm run lint:fix`.



## 🔵 Mejoras
- **ID-V02:** [Paso 2] Mostrar un contador de sincronizaciones exitosas en el CLI para dar feedback visual de actividad. → Recomendación: Añadir una variable de estado en el EventHandler.
- **ID-V03:** [Paso 2] Permitir configurar el debounce mediante variables de entorno además de flags de CLI. → Recomendación: Integrar con `CLIConfig` o lectura de `.env`.
- **ID-V05:** [Paso 3] Soporte para `async def` nativo en Typer. Se recomienda usar `async def` directamente en los comandos de Typer (requiere Typer 0.12+) en lugar de wrappers con `asyncio.run`. → Recomendación: Refactorizar comandos en `run.py`.
- **ID-V09:** [Paso 4] La documentación de la skill (`SKILL.md` y `bundle_schemas.md`) referencia `BaseTool` en lugar de `OrgBaseTool`. Para aprovechar el Vault y RLS de FAP, se debe recomendar heredar de `OrgBaseTool`.



Próximos pasos sugeridos: Realizar pruebas de integración con un bundle real que contenga dependencias cruzadas entre un agente y una skill local para validar la resolución en el tool_registry transiente.

