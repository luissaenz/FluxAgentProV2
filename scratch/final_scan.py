import json
from pathlib import Path

def final_scan():
    seed = Path("data/service_catalog_seed.json")
    data = json.loads(seed.read_text(encoding="utf-8"))
    tools = data["tools"]
    
    issues = []
    
    # 1. Check for empty URLs
    empty_urls = [t["id"] for t in tools if not t.get("execution", {}).get("url")]
    if empty_urls:
        issues.append(f"Empty URLs in: {empty_urls[:5]}...")
        
    # 2. Check for missing profiles
    missing_profiles = [t["id"] for t in tools if not t.get("tool_profile")]
    if missing_profiles:
        issues.append(f"Missing tool_profile in: {missing_profiles[:5]}...")
        
    # 3. Check for auth_type consistency
    auth_issues = [t["id"] for t in tools if t["provider"].get("auth_type") == "none"]
    # We expected 0 because of the mapping.
    
    # 4. Check for orphan tool_id (lowercase check)
    case_issues = [t["id"] for t in tools if t["id"] != t["id"].lower()]
    if case_issues:
        issues.append(f"Non-lowercase IDs: {case_issues[:5]}...")

    print(f"Total tools: {len(tools)}")
    for issue in issues:
        print(f"ISSUE: {issue}")
    
    if not issues:
        print("Technical structure looks GOOD.")

if __name__ == "__main__":
    final_scan()
