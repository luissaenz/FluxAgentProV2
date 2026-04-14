import json
import re
from pathlib import Path

def check_skipped():
    docs_dir = Path("docs")
    total_raw = 0
    skipped = 0
    unique_ids = set()
    
    for i in range(1, 5):
        p = docs_dir / f"prompt{i}.txt"
        if not p.exists(): continue
        content = p.read_text(encoding="utf-8")
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            total_raw += len(data)
            for t in data:
                tid = t.get("tool_id") or t.get("id")
                if not tid:
                    skipped += 1
                else:
                    unique_ids.add(tid.lower())
    
    print(f"Total raw tools in prompts: {total_raw}")
    print(f"Skipped (no ID): {skipped}")
    print(f"Unique IDs from prompts: {len(unique_ids)}")

if __name__ == "__main__":
    check_skipped()
