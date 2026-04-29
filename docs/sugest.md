# Sugerencias y Issues No Críticos

## 🟡 Importantes
- **ID-V01:** [Paso 2] El comando `dev` asume que el archivo ZIP se genera en el directorio padre o en el CWD. Podría ser más robusto si `package_bundle` devolviera la ruta exacta del archivo generado. → Tipo: Estabilidad → Recomendación: Refactorizar `package_bundle` para retornar el path del ZIP.

## 🔵 Mejoras
- **ID-V02:** [Paso 2] Mostrar un contador de sincronizaciones exitosas en el CLI para dar feedback visual de actividad. → Recomendación: Añadir una variable de estado en el EventHandler.
- **ID-V03:** [Paso 2] Permitir configurar el debounce mediante variables de entorno además de flags de CLI. → Recomendación: Integrar con `CLIConfig` o lectura de `.env`.
