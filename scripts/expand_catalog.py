import json
import re
from pathlib import Path
from urllib.parse import urlparse

# Configuración de rutas
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "docs" / "IMPLEMENTED" / "Sprint 2 - Expansion of Service Catalog"
DATA_DIR = BASE_DIR / "data"
SEED_PATH = DATA_DIR / "service_catalog_seed.json"

def extract_json_array(text):
    """Extrae el primer array JSON encontrado en el texto."""
    # Busca algo que empiece con [ y termine con ] con contenido JSON
    match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            print(f"Error decodificando JSON: {e}")
            return []
    return []

def infer_base_url(url):
    """Extrae protocolo + host de una URL."""
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""

def transform_tool(raw_tool):
    """Transforma una tool plana del prompt en el formato Nested TIPO C."""
    # 1. Normalizar ID
    raw_id = raw_tool.get("tool_id") or raw_tool.get("id")
    if not raw_id:
        return None
    
    tool_id = raw_id.lower()
    
    # 2. Extraer Provider Info
    provider_name = raw_tool.get("provider", "Unknown")
    provider_id = provider_name.lower().replace(" ", "_")
    
    # 3. Lógica de Autenticación y Secretos (Hallazgo #5)
    auth = raw_tool.get("auth", {})
    auth_type = auth.get("type", "api_key")
    scopes = auth.get("scopes", [])
    
    required_secrets = []
    if auth_type == "none":
        # Hallazgo #5: Mapear none a api_key con secretos vacíos para integridad
        auth_type = "api_key"
        required_secrets = []
    elif auth_type == "api_key":
        required_secrets = [f"{provider_id}_api_key"]
    elif auth_type == "oauth2":
        required_secrets = [f"{provider_id}_token"]
    elif auth_type == "basic_auth":
        required_secrets = [f"{provider_id}_auth_token"] # Estandarizado para Twilio/etc
    
    # 4. Inferencia de base_url
    exec_info = raw_tool.get("execution", {})
    exec_url = exec_info.get("url", "")
    base_url = infer_base_url(exec_url)
    
    # 5. Construcción del objeto Provider (TIPO C)
    provider_obj = {
        "id": provider_id,
        "name": provider_name,
        "category": raw_tool.get("category", "other"),
        "auth_type": auth_type,
        "base_url": base_url,
        "required_secrets": required_secrets,
        "auth_scopes": scopes
    }
    
    # 6. Tool Final
    transformed = {
        "id": tool_id,
        "name": raw_tool.get("name", tool_id),
        "provider": provider_obj,
        "version": raw_tool.get("version", "1.0.0"),
        "input_schema": raw_tool.get("input_schema", {}),
        "output_schema": raw_tool.get("output_schema", {}),
        "execution": {
            "url": exec_url,
            "method": exec_info.get("method", "GET"),
            "headers": exec_info.get("headers", {})
        },
        "tool_profile": raw_tool.get("tool_profile", {})
    }
    
    return transformed

def main():
    print("--- Iniciando expansion del catalogo de servicios (Sprint 2) ---")
    
    # 0. Identificar herramientas de prompts futuros (6-9) para excluirlas de este sprint
    future_prompt_ids = set()
    for i in range(6, 10):
        pf = DOCS_DIR / f"prompt{i}.txt"
        if pf.exists():
            with open(pf, "r", encoding="utf-8") as f:
                content = f.read()
                for t in extract_json_array(content):
                    tid = t.get("tool_id") or t.get("id")
                    if tid:
                        future_prompt_ids.add(tid.lower())
    
    # 1. Cargar el seed existente filtrando basura de sprints futuros
    all_tools = {}
    if SEED_PATH.exists():
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            try:
                seed_data = json.load(f)
                count_legacy = 0
                for t in seed_data.get("tools", []):
                    tid = t["id"].lower()
                    if tid not in future_prompt_ids:
                        all_tools[tid] = t
                        count_legacy += 1
                print(f"Loaded {count_legacy} base tools (legacy + Sprint 2) from seed.")
            except Exception as e:
                print(f"Warning: Error loading seed: {e}. Starting empty catalog.")
    
    # 2. Procesar Prompts (1 a 5) como indica el criterio de validación
    for i in range(1, 6):
        prompt_file = DOCS_DIR / f"prompt{i}.txt"
        if not prompt_file.exists():
            print(f"Warning: File {prompt_file.name} not found. Skipping.")
            continue
            
        print(f"File {prompt_file.name} processing...")
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        raw_tools = extract_json_array(content)
        count = 0
        for raw_tool in raw_tools:
            transformed = transform_tool(raw_tool)
            if transformed:
                all_tools[transformed["id"]] = transformed
                count += 1
        print(f"   OK: Extracted {count} tools.")

    # 3. Guardar el resultado final
    final_output = {
        "tools": list(all_tools.values())
    }
    
    # Ordenar por ID para mantener consistencia
    final_output["tools"].sort(key=lambda x: x["id"])
    
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcess finished successfully.")
    print(f"Total tools in catalog: {len(all_tools)}")
    print(f"Saved to: {SEED_PATH}")

if __name__ == "__main__":
    main()
