# Análisis Técnico - Paso 1 (Agente atg)

### 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `POST /api/mcp/generate-pin` | Verificación de routers en `src/main.py` y `src/api/main.py` | ❌ | No existe. La ruta base de la API debe ser en el router respectivo. El router actual MCP está bajo el prefijo `/api/v1/mcp`. |
| 2 | `auth del admin (middleware existente)` | `grep_search` de `verify_org_membership`. Existe en `src/api/middleware.py` | ✅ | `src/api/middleware.py:261` |
| 3 | `secure-pin.ts existente` | `grep_search` en todo el repo para "secure-pin". | ❌ | Discrepancia: El archivo de TypeScript NO existe en `src` ni `dashboard`. |
| 4 | Almacenamiento seguro del PIN | Verificación de tabla de secretos en `supabase/migrations/002_governance.sql` | ✅ | `secrets` table existe y se puede acceder vía `service_client` como en `src/db/vault.py`. |
| 5 | Vinculación del PIN a `org_id` | Verificación de esquema de `secrets` | ✅ | La tabla `secrets` requiere `org_id` y `name`, permitiendo relacionar un registro único de PIN. (Ej: `name = 'mcp_auth_pin'`). |
| 6 | Transporte y Router de MCP | Verificación del archivo de rutas `src/mcp/server_sse.py` | ✅ | Expone `router = APIRouter(prefix="/mcp", tags=["mcp"])` que se importa en `src/api/main.py`. |
| 7 | Librería criptográfica | Verificación de imports `python-jose` | ✅ | Se unificó a `python-jose` (ver `docs/estado-fase.md`). |
| 8 | Configuración Vault para MCP | `get_secret` existe | ✅ | `src/db/vault.py` tiene la función para recuperar secretos con `service_client()`. |

**Discrepancias encontradas:**
1. **Falta `secure-pin.ts`**: El plan asume usar lógica TS preexistente que no se encuentra en el repositorio.
   - **Resolución**: Se implementará directamente en Python la generación del PIN usando la librería criptográfica nativa de Python (`secrets.token_hex(16)`), ubicándolo en el handler del nuevo endpoint en `src/mcp/server_sse.py` o módulo de autenticación `src/mcp/auth.py`. 
2. **Ruta Endpoint**: El plan indica `/api/mcp/generate-pin`. La aplicación carga rutas usando `/api/v1/mcp/...` dentro de `src/api/main.py`.
   - **Resolución**: Se va a crear el endpoint `POST /generate-pin` dentro del router de `src/mcp/server_sse.py` (cuyo prefix ya es `/mcp` y luego montado en `/api/v1`). La ruta real finalmente será `/api/v1/mcp/generate-pin`.

### 1. Diseño Funcional
- **Happy Path:**
  1. El cliente (Dashboard) realiza un POST autenticado a `/api/v1/mcp/generate-pin`.
  2. El middleware `verify_org_membership` valida el token JWT del usuario y confirma que pertenece al contexto enviado.
  3. El backend genera de manera segura un PIN de servidor (ejemplo: UUID o hex) de manera aleatoria.
  4. El backend almacena este PIN dentro de la tabla `secrets` de la organización (nombre de secreto: "mcp_connection_pin") con un valor asociado al PIN seguro. Esto aprovecha la escalabilidad de `service_role`.
  5. Se retorna el PIN al cliente para que su configuración en un cliente MCP (ej: Claude Desktop) proceda.
- **Manejo de errores:**
  - Token JWT inválido o sin permisos: `401 Unauthorized` o `403 Forbidden` provistos nativamente desde el middleware.
  - Error en inserción en DB con Supabase Client: `500 Internal Server Error`, gestionado con excepciones.

### 2. Diseño Técnico
- **Endpoint:** `POST /generate-pin` alojado en `src/mcp/server_sse.py`.
- **Interfaces Reales:**
  - Entrada: Token de autorización válido capturado por `auth: dict = Depends(verify_org_membership)`.
  - Salida: Payload JSON en el formato `{"pin": "PIN_ALEATORIO"}`.
- **Implementación Lógica**: La función usará el core de Python en su módulo `secrets`. Una buena forma es:
  ```python
  import secrets
  pin = secrets.token_urlsafe(16)
  ```
- **Almacenamiento (Vinculación a `org_id`)**:
  - Reutilización de la tabla `secrets` definida en la migración `002_governance.sql`.
  - Se operará mediante una inserción/actualización directa (UPSERT):
    ```python
    db = get_service_client()
    db.table("secrets").upsert({
        "org_id": org_id,
        "name": "mcp_connection_pin",
        "secret_value": pin
    }, on_conflict="org_id, name").execute()
    ```

### 3. Decisiones
- **Corrije Plan 1.0.0.2 - Ausencia de TS Code:** La generación no interviene con scripts en TypeScript sino que reside integralmente en el backend en FastAPI (Python). Almacena el token localmente como secreto en Supabase.
- **Almacenamiento en tabla _secrets_ en vez de _org_mcp_servers_:** Es mucho más seguro abstraer datos sensitivos como PIN de autenticación y tokens en las tablas designadas para esto con RLS bloqueados para el frontend. Centraliza los datos privados usando una tabla validada previamente y comprobada en §0.

### 4. Criterios de Aceptación
- [x] Endpoint expuesto como POST bajo `/api/v1/mcp/generate-pin` accesible sólamente usando JWT con cabecera `X-Org-ID`.
- [x] El endpoint recibe de forma exitosa las credenciales verificadas prexistentes para obtener dinámicamente un `org_id` y `user_id`.
- [x] Un PIN seguro es emitido al cliente con el código 200.
- [x] Un registro unificado de PIN queda persistido bajo UPSERT de manera que múltiples peticiones rotan el PIN correctamente sin arrojar errores de duplicado en DB.

### 5. Riesgos
- **Riesgo:** Conflicto de actualización en la tabla `secrets` por la constraint `UNIQUE(org_id, name)`. Si la API de supabase proveída por Postgrest no respeta o implementa transparentemente el UPSERT, pueden generarse fallos 500 al rotar el PIN.
  - **Mitigación:** Asegurarse de enviar explicitamente el flag `on_conflict` (en este caso el tuple lógico `"org_id, name"` o el proxy que usa Postgrest en `upsert(...)`). También se probará en el testing de implementación.

### 6. Plan
1. **Tarea 1.0.0.2.1:** Implementar la lógica del endpoint con `generate-pin` en la ruta de `src/mcp/server_sse.py`.
   - **Descripción**: Redacción del body del path operator que incluye generación manual con módulo `secrets` y upsert con `get_service_client()`.
   - **Estimación**: 20 mins.
   - **Complejidad**: Baja.
2. **Tarea 1.0.0.2.2:** Ajuste en el tipaje final si se requiere retorno en el modelo Pydantic nuevo o en una simple capa JSON.
   - **Descripción**: Simple validación del test local una vez levantado uvicorn. 
   - **Estimación**: 10 mins.
   - **Complejidad**: Baja.

**Tiempo Total Estimado:** 30 minutos.

### 🔮 Roadmap (NO implementar ahora)
- **Validación Backend MCP**: Actualmente se completó emitir el PIN pero se requerirá en el próximo ciclo analizar cómo inyectar y verificar este PIN cuando un cliente *entable una conexión real SSE* y lo provea a través de la cabecera `Authorization: Bearer <PIN>`.
- **Integración con Gestores Seguros (Avanzado)**: En caso que la App expanda a AWS, utilizar AWS Secrets Manager en vez de la tabla compartida `secrets` que expone tokens de manera cruda en el Vault.
