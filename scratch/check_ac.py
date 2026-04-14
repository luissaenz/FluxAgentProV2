import json
from pathlib import Path

def check_activecampaign():
    seed = Path("data/service_catalog_seed.json")
    seed_data = json.loads(seed.read_text(encoding="utf-8"))
    found = False
    for t in seed_data["tools"]:
        if t["id"].lower() == "activecampaign.create_contact":
            print(f"Tool: {t['id']}")
            print(f"Base URL: '{t['provider'].get('base_url')}'")
            print(f"Execution URL: {t['execution'].get('url')}")
            found = True
            break
    if not found:
        print("ActiveCampaign not found in seed.")

if __name__ == "__main__":
    check_activecampaign()
