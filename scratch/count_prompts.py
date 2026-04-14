import json
import re
from pathlib import Path

def count_tools():
    docs_dir = Path("docs")
    total_found = 0
    for i in range(1, 5):
        p = docs_dir / f"prompt{i}.txt"
        if not p.exists(): continue
        content = p.read_text(encoding="utf-8")
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                print(f"{p.name}: {len(data)} tools")
                total_found += len(data)
            except:
                print(f"{p.name}: Invalid JSON")
    print(f"Sum of tools in prompts: {total_found}")

    # load original seed
    seed_path = Path("data/service_catalog_seed.json")
    # Wait, the seed file was already overwritten by the expand_catalog script.
    # I can't check the *original* count easily unless I check git or something.
    # But I can check the current one.

if __name__ == "__main__":
    count_tools()
