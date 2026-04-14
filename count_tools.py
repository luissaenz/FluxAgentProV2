import json
import re


def extract_all_json_arrays(text):
    matches = re.findall(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    results = []
    for m in matches:
        try:
            arr = json.loads(m)
            results.extend(arr)
        except:
            pass
    return results


# Count all tools from prompts (not unique - all occurrences)
total_tools = 0
unique_ids = set()
for i in range(1, 5):
    with open(f"docs/prompt{i}.txt", "r", encoding="utf-8") as f:
        content = f.read()
    tools = extract_all_json_arrays(content)
    print(f"prompt{i}: {len(tools)} raw tools")
    total_tools += len(tools)
    for t in tools:
        tid = t.get("tool_id") or t.get("id")
        if tid:
            unique_ids.add(tid.lower())

print(f"\nTotal raw tools (with duplicates): {total_tools}")
print(f"Unique tool IDs: {len(unique_ids)}")
