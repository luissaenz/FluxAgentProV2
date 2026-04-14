import json

git_version = json.load(open("temp_seed.json"))
current_version = json.load(open("data/service_catalog_seed.json"))

print(f"Git version: {len(git_version['tools'])} tools")
print(f"Current version: {len(current_version['tools'])} tools")

git_ids = set(t["id"] for t in git_version["tools"])
current_ids = set(t["id"] for t in current_version["tools"])

print(f"IDs in git but not current: {len(git_ids - current_ids)}")
print(f"IDs in current but not git: {len(current_ids - git_ids)}")
