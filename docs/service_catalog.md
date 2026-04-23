# 📚 Catálogo de Servicios (TIPO C)

El Catálogo de Servicios de FluxAgentPro permite exponer integraciones REST genéricas a los agentes MCP de forma dinámica. Estas herramientas se cargan desde un archivo seed centralizado y se ejecutan mediante la `ServiceConnectorTool`.

## 📁 Ubicación de los Datos
- **Archivo Seed**: `data/service_catalog_seed.json`
- **Script de Importación**: `scripts/import_service_catalog.py`

## 🛠️ Estructura del Catálogo

El catálogo se distribuye en tres tablas:
1.  **`service_catalog`**: Definiciones globales de proveedores (GitHub, Stripe, etc.).
2.  **`service_tools`**: Definiciones globales de herramientas (schemas e instrucciones de ejecución).
3.  **`org_service_integrations`**: Registro de qué organización tiene activada qué integración (aislado por RLS).

### Formato de Herramienta (JSON)

Cada entrada en el archivo seed debe seguir este esquema para ser procesada correctamente por el importador:

```json
{
  "id": "identificador_unico",
  "name": "Nombre de la Herramienta",
  "version": "1.0.0",
  "provider": {
    "id": "id_del_proveedor",
    "name": "Nombre del Proveedor",
    "category": "dev_tools|communication|finance|crm|support|other",
    "auth_type": "api_key",
    "base_url": "https://api.ejemplo.com",
    "required_secrets": ["NOMBRE_SECRETO_EN_VAULT"]
  },
  "input_schema": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
  },
  "output_schema": {
    "type": "object",
    "properties": { ... }
  },
  "execution": {
    "url": "https://api.ejemplo.com/recurso/{id}",
    "method": "GET|POST|PUT|DELETE",
    "headers": {
      "Authorization": "Bearer {api_key}",
      "Content-Type": "application/json"
    }
  },
  "tool_profile": {
    "description": "Explicación para el modelo de lenguaje",
    "risk_level": "low|medium|high",
    "requires_approval": true|false
  }
}
```

## 🔐 Manejo de Secretos y Variables

La `ServiceConnectorTool` realiza una sustitución dinámica de variables en `execution.url` y `execution.headers` usando la sintaxis de llaves `{}`:

1.  **Variables de Ruta/Cuerpo**: Se resuelven desde los parámetros de entrada (`input_data`).
2.  **Secretos**: Se resuelven desde el **Vault** de la organización. Si la herramienta requiere `GITHUB_TOKEN`, el conector lo buscará en los secretos cifrados de la organización actual.

## 🚀 Proceso de Importación

Para sincronizar el archivo local con la base de datos Supabase, utilice el siguiente comando:

```bash
# Configurar variables de entorno primero
# $env:SUPABASE_URL = "..."
# $env:SUPABASE_SERVICE_KEY = "..."

python -m scripts.import_service_catalog
```

El script de importación realiza chequeos de integridad automáticos:
- **Proveedores Mínimos**: Exige al menos 15 proveedores únicos.
- **Validación de Schemas**: Corrige automáticamente formatos de `required` no estándar.
- **Chequeo de Huérfanos**: Asegura que toda herramienta pertenezca a un proveedor registrado.
