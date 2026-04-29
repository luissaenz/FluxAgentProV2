# 📦 ESQUEMAS TÉCNICOS DE BUNDLES (FAP-IMPLEMENTOR)

Los bundles en FluxAgentPro v2 siguen una estructura estricta para garantizar la integridad y seguridad.

## 1. Estructura de Carpetas
```text
bundle-name/
├── manifest.json       # Metadatos y hashes (OBLIGATORIO)
├── agents/             # Definiciones de Agentes (.json)
├── skills/             # Código de Habilidades (.py)
└── flows/              # Definiciones de Flujos (.json)
```

## 2. Esquema de `manifest.json` (v2.0)
El archivo `manifest.json` es el corazón del bundle.

```json
{
  "version": "2.0",
  "bundle_info": {
    "name": "nombre-del-bundle",
    "description": "Descripción detallada",
    "version": "1.0.0",
    "author": "dev@org.com"
  },

  "hashes": {
    "agents/mi-agente.json": "sha256:...",
    "skills/mi-habilidad.py": "sha256:...",
    "flows/mi-flujo.json": "sha256:..."
  }
}
```
**Reglas Críticas:**
- `version` (raíz): Debe ser `"2.0"`.
- `hashes`: Diccionario donde la llave es la ruta relativa (usando `/`) y el valor es el hash SHA256 prefijado con `sha256:`.
- **Integridad**: No intentes generar los hashes manualmente. Utilizá la herramienta del CLI `fap-hash-update` o similar antes de publicar.

## 3. Esquema de Agentes (`agents/*.json`)
```json
{
  "role": "Lead Finder",
  "goal": "Encontrar prospectos de alta calidad",
  "backstory": "Experto en búsqueda de datos con acceso a herramientas de scraping.",
  "allow_delegation": false,
  "verbose": true,
  "tools": ["lead_scraper"]
}
```

## 4. Esquema de Habilidades (`skills/*.py`)
Deben heredar de `src.tools.base_tool.OrgBaseTool`.


```python
from src.tools.base_tool import OrgBaseTool
from pydantic import Field

class MyCustomTool(OrgBaseTool):

    name: str = "my_tool"
    description: str = "Describe what it does"
    
    input_param: str = Field(..., description="An input parameter")

    def run(self, **kwargs):
        # Lógica de la herramienta
        return {"status": "success"}
```

## 5. Esquema de Flujos (`flows/*.json`)
```json
{
  "name": "Lead Research Flow",
  "type": "sequential",
  "steps": [
    {
      "agent": "Lead Finder",
      "task": "Busca 5 leads de tecnología en Madrid"
    }
  ]
}
```
