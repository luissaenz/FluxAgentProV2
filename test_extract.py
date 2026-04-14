import json, re


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


# Check all prompts
for i in range(1, 5):
    with open(f"docs/prompt{i}.txt", "r", encoding="utf-8") as f:
        content = f.read()
    tools = extract_all_json_arrays(content)
    print(f"prompt{i}: {len(tools)} total tools")

    # Show first few IDs
    ids = [(t.get("tool_id") or t.get("id")) for t in tools[:5]]
    print(f"  First 5: {ids}")
