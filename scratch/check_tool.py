import json
import re
from pathlib import Path

def check_prompt_tool():
    prompt4 = Path("docs/prompt4.txt")
    content = prompt4.read_text(encoding="utf-8")
    match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
    if not match: return
    data = json.loads(match.group())
    first_tool = data[0]
    tid = first_tool.get("tool_id").lower()
    print(f"Tool ID from prompt4: {tid}")
    
    seed = Path("data/service_catalog_seed.json")
    seed_data = json.loads(seed.read_text(encoding="utf-8"))
    for t in seed_data["tools"]:
        if t["id"].lower() == tid:
            print(f"Found in seed: {t['id']}")
            print(f"Base URL: {t['provider'].get('base_url')}")
            print(f"Secrets: {t['provider'].get('required_secrets')}")
            break

if __name__ == "__main__":
    check_prompt_tool()
