import json
import os
from pathlib import Path

def validate():
    seed_path = Path("data/service_catalog_seed.json")
    if not seed_path.exists():
        print("Error: seed file not found")
        return

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tools = data.get("tools", [])
    total_tools = len(tools)
    print(f"Total tools: {total_tools}")
    
    # Criterio 2: >= 230
    if total_tools >= 230:
        print("✅ Criterio 2: >= 230 tools (PASS)")
    else:
        print(f"❌ Criterio 2: Not enough tools ({total_tools}) (FAIL)")
        
    # Criterio 3: Nested provider
    nested_check = all("provider" in t and isinstance(t["provider"], dict) for t in tools)
    if nested_check:
        print("✅ Criterio 3: All tools have nested provider (PASS)")
    else:
        print("❌ Criterio 3: Found tools without nested provider (FAIL)")
        
    # sample tools
    if total_tools > 0:
        t = tools[0]
        print(f"Sample Tool ID: {t.get('id')}")
        print(f"Sample Provider: {t.get('provider', {}).get('id')}")
        print(f"Sample Secret: {t.get('provider', {}).get('required_secrets')}")

if __name__ == "__main__":
    validate()
