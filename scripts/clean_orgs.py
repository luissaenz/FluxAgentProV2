#!/usr/bin/env python
import os
import requests
import dotenv

def main():
    print("Starting final organization cleanup...", flush=True)
    dotenv.load_dotenv()
    
    URL = os.getenv("SUPABASE_URL")
    KEY = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }
    base_rest = f"{URL}/rest/v1"

    # 1. Identify valid admin orgs
    r = requests.get(f"{base_rest}/org_members?select=org_id", headers=headers)
    active_org_ids = list(set([m["org_id"] for m in r.json()]))
    
    if not active_org_ids:
        print("No active organizations with members found. Aborting cleanup to avoid data loss.", flush=True)
        return

    # 2. Delete organizations WITHOUT members
    print(f"Preserving {len(active_org_ids)} orgs. Deleting others...", flush=True)
    
    # We do them one by one to be safe and avoid URL length issues
    r_all = requests.get(f"{base_rest}/organizations?select=id", headers=headers)
    for org in r_all.json():
        oid = org["id"]
        if oid not in active_org_ids:
            print(f"   Deleting orphaned org {oid}...", flush=True)
            requests.delete(f"{base_rest}/organizations?id=eq.{oid}", headers=headers)

    # 3. Rename the main organization if it's still named CoctelPro
    for oid in active_org_ids:
        r_detail = requests.get(f"{base_rest}/organizations?id=eq.{oid}", headers=headers).json()
        if r_detail and ("Coctel" in r_detail[0]["name"] or "Demo" in r_detail[0]["name"]):
            print(f"   Renaming {r_detail[0]['name']} to 'FluxAgentPro HQ'...", flush=True)
            requests.patch(f"{base_rest}/organizations?id=eq.{oid}", headers=headers, json={
                "name": "FluxAgentPro HQ",
                "slug": "fap-hq"
            })

    print("\nCLEANUP COMPLETE!", flush=True)

if __name__ == "__main__":
    main()
