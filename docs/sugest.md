# Sugerencias y Issues No Críticos

## 🟡 Importantes
- **ID-V01:** [Paso 2] El comando `dev` asume que el archivo ZIP se genera en el directorio padre o en el CWD. Podría ser más robusto si `package_bundle` devolviera la ruta exacta del archivo generado. → Tipo: Estabilidad → Recomendación: Refactorizar `package_bundle` para retornar el path del ZIP.
- **ID-V04:** [Paso 3] Inconsistencia en Naming de Tools Locales. La `LocalExecutor` registra tools usando el nombre del archivo, pero los agentes podrían usar el nombre de la clase. → Tipo: Estabilidad → Recomendación: Normalizar el registro para incluir ambos nombres en el registry transiente.


## 🔵 Mejoras
- **ID-V02:** [Paso 2] Mostrar un contador de sincronizaciones exitosas en el CLI para dar feedback visual de actividad. → Recomendación: Añadir una variable de estado en el EventHandler.
- **ID-V03:** [Paso 2] Permitir configurar el debounce mediante variables de entorno además de flags de CLI. → Recomendación: Integrar con `CLIConfig` o lectura de `.env`.
- **ID-V05:** [Paso 3] Soporte para `async def` nativo en Typer. Se recomienda usar `async def` directamente en los comandos de Typer (requiere Typer 0.12+) en lugar de wrappers con `asyncio.run`. → Recomendación: Refactorizar comandos en `run.py`.


Próximos pasos sugeridos: Realizar pruebas de integración con un bundle real que contenga dependencias cruzadas entre un agente y una skill local para validar la resolución en el tool_registry transiente.

