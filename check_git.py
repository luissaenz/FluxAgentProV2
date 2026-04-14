import json

git_seed = json.load(open("temp_seed.json"))
print(f"Git seed tools: {len(git_seed['tools'])}")

# Show all providers in git seed
providers = {}
for t in git_seed["tools"]:
    p = t.get("provider", {}).get("id", "unknown")
    providers[p] = providers.get(p, 0) + 1

print("Providers in git seed:")
for p, c in sorted(providers.items()):
    print(f"  {p}: {c}")
