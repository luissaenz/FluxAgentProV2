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


# Get all unique tools from prompts
all_prompt_tools = {}
for i in range(1, 5):
    with open(f"docs/prompt{i}.txt", "r", encoding="utf-8") as f:
        content = f.read()
    tools = extract_all_json_arrays(content)
    for t in tools:
        tid = t.get("tool_id") or t.get("id")
        if tid:
            tid_lower = tid.lower()
            if tid_lower not in all_prompt_tools:
                all_prompt_tools[tid_lower] = t

print(f"Unique tools from ALL prompts: {len(all_prompt_tools)}")

# Get original seed (50 tools from git)
git_seed = json.load(open("temp_seed.json"))
git_ids = set(t["id"].lower() for t in git_seed["tools"])

# Current seed
current = json.load(open("data/service_catalog_seed.json"))
current_ids = set(t["id"].lower() for t in current["tools"])

print(f"Original git seed: {len(git_ids)} tools")
print(f"Current seed: {len(current_ids)} tools")

# What's in prompts but NOT in current seed?
new_from_prompts = all_prompt_tools.keys() - current_ids
print(f"Tools in prompts but NOT in current seed: {len(new_from_prompts)}")
print(f"Sample: {list(new_from_prompts)[:10]}")
