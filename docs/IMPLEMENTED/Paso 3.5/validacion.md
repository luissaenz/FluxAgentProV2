# Estado de Validación: RECHAZADO ❌

## Checklist de Criterios de Aceptación
| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | El script ejecuta un flujo completo de al menos 10 eventos sin intervención manual. | ❌ No cumple | Fallo de ejecución: `AttributeError: 'AsyncRealtimeChannel' object has no attribute 'on'`. |
| 2 | Se genera un reporte detallado en `LAST/log_latencia.json` con los resultados. | ❌ No cumple | El archivo no existe debido al crash de los tests. |
| 3 | P95 de latencia infra (DB -> Recv) < 800ms. | ❌ No cumple | No medible. El canal de Realtime no pudo configurarse. |
| 4 | Latencia máxima (Worst Case) < 1500ms. | ❌ No cumple | No medible. |
| 5 | Integridad de Mensajes = 100% (DB == Stream). | ❌ No cumple | No medible. |
| 6 | El script utiliza el orquestador `MultiCrewFlow` real para la inserción. | ❌ No cumple | El script falla antes de llegar a la ejecución del flujo. |
| 7 | Los tokens de Supabase se manejan vía variables de entorno `.env`. | ✅ Cumple | Verificado en `tests/test_3_5_latency.py:42-43`. |
| 8 | El test detecta y alerta sobre "Clock Skew" excesivo (> 5s). | ❌ No cumple | El RPC `get_server_time` falla con error interno: `'NoneType' object has no attribute 'send'`. |
| 9 | Manejo correcto de cierre de canales al finalizar o fallar. | ✅ Cumple | Estructuralmente correcto en el bloque `finally` y método `close()`. |

## Resumen
La validación ha sido **RECHAZADA** nuevamente. Aunque se implementó la migración SQL para el RPC y se migró al cliente asíncrono, el script `tests/test_3_5_latency.py` utiliza una sintaxis incorrecta para la librería `supabase-py` v2.x (async). Específicamente, intenta usar el método `.on()` que no existe en Python (se debe usar `.on_postgres_changes()`) y no espera (`await`) la llamada a `.subscribe()`. Además, persiste un error técnico en la ejecución de RPCs que impide la calibración de tiempo.

## Issues Encontrados

### 🔴 Críticos
- **ID-001:** Uso incorrecto de API Realtime (Python) → Criterio afectado: [#1, #3] → Recomendación: Cambiar `channel.on("postgres_changes", ...)` por `channel.on_postgres_changes(event="INSERT", schema="public", table="domain_events", filter=..., callback=...)`.
- **ID-002:** Falta `await` en suscripción → Criterio afectado: [#1] → Recomendación: La llamada a `self._channel.subscribe(...)` debe ser `await self._channel.subscribe(...)` para asegurar que el canal se abra correctamente en el cliente asíncrono.
- **ID-003:** Error en ejecución de RPC → Criterio afectado: [#8] → Recomendación: El error `'NoneType' object has no attribute 'send'` sugiere que el cliente HTTP interno no está listo o hay un conflicto de versiones. Verificar que `supabase-py` y `postgrest-py` estén correctamente instalados y que el cliente no se haya cerrado prematuramente.
- **ID-004:** Fallo de Integridad y Métricas → Criterio afectado: [#2, #3, #4, #5] → Recomendación: Corregir los errores de conexión para permitir que el script complete la medición y genere el reporte `log_latencia.json`.

### 🟡 Importantes
- **ID-005:** Warnings de Deprecación → Tipo: Deuda Técnica → Recomendación: Configurar el timeout y la verificación SSL en el cliente HTTP base (httpx) en lugar de pasarlos directamente al `AsyncPostgrestClient` para limpiar los logs de warnings.

### 🔵 Mejoras
- **ID-006:** Verificación de Migración en CI → Recomendación: Añadir un paso previo al test que verifique si el RPC `get_server_time` existe consultando `information_schema.routines`.

## Estadísticas
- Criterios de aceptación: 2/9 cumplidos
- Issues críticos: 4
- Issues importantes: 1
- Mejoras sugeridas: 1
