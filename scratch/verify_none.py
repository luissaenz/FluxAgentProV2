import json
import re
from pathlib import Path

def verify_none_mapping():
    # Find a tool in a prompt that has auth.type = none
    found_tid = None
    for i in range(1, 5):
        p = Path(f"docs/prompt{i}.txt")
        if not p.exists(): continue
        content = p.read_text(encoding="utf-8")
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            for t in data:
                if t.get("auth", {}).get("type") == "none":
                    found_tid = (t.get("tool_id") or t.get("id")).lower()
                    print(f"Found 'none' tool in prompt: {found_tid}")
                    break
        if found_tid: break
    
    if not found_tid:
        print("No 'none' tool found in prompts.")
        return

    # Check in seed
    seed = Path("data/service_catalog_seed.json")
    seed_data = json.loads(seed.read_text(encoding="utf-8"))
    for t in seed_data["tools"]:
        if t["id"].lower() == found_tid:
            print(f"Tool in seed: {t['id']}")
            print(f"Auth Type: {t['provider'].get('auth_type')}")
            print(f"Required Secrets: {t['provider'].get('required_secrets')}")
            break

if __name__ == "__main__":
    verify_none_mapping()
