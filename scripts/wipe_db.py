#!/usr/bin/env python
"""Reset Project Database — Phase CleanUp.

REST VERSION (using requests to avoid httpx/http2 hanging issues).
"""

import sys
import os
import requests
import dotenv

def main():
    print("Starting database cleanup (REST mode)...", flush=True)
    dotenv.load_dotenv()
    
    URL = os.getenv("SUPABASE_URL")
    KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not URL or not KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env", flush=True)
        sys.exit(1)
        
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    base_rest = f"{URL}/rest/v1"

    # 1. Identify Admin users/orgs to preserve
    print("Searching for admin users to preserve...", flush=True)
    admin_org_ids = []
    admin_user_ids = []
    try:
        r = requests.get(f"{base_rest}/org_members?select=*", headers=headers, timeout=10)
        if r.status_code == 200:
            all_members = r.json()
            # Priority: fap_admin, admin, org_owner
            admins = [m for m in all_members if m.get("role") == "fap_admin"]
            if not admins:
                admins = [m for m in all_members if m.get("role") in ("admin", "org_owner")]
            if not admins and all_members:
                admins = [all_members[0]]
            
            admin_user_ids = [m["user_id"] for m in admins]
            admin_org_ids = list(set([m["org_id"] for m in admins]))
            print(f"   Found {len(admin_user_ids)} admins in {len(admin_org_ids)} orgs.", flush=True)
        else:
            print(f"   Could not fetch members: {r.status_code} {r.text}", flush=True)
    except Exception as e:
        print(f"   Error identifying admins: {e}", flush=True)

    # 2. Cleanup tables (Correct Order)
    # snapshots uses task_id, others use id
    tables_to_clean = [
        ("snapshots", "task_id"),
        ("tasks", "id"),
        ("domain_events", "id"),
        ("conversations", "id"),
        ("tickets", "id"),
        ("pending_approvals", "id"),
        ("agent_metadata", "id"),
        ("workflow_templates", "id"),
        ("org_mcp_servers", "id"),
        ("agent_catalog", "id"),
        ("memory_vectors", "id"),
        ("flow_presentations", "id"),
    ]

    print("Cleaning operational tables...", flush=True)
    dummy_uuid = "00000000-0000-0000-0000-000000000000"
    for table, pk in tables_to_clean:
        try:
            print(f"Cleaning '{table}'...", flush=True)
            # URL format for delete: table?pk=neq.dummy
            del_url = f"{base_rest}/{table}?{pk}=neq.{dummy_uuid}"
            r = requests.delete(del_url, headers=headers, timeout=15)
            if r.status_code in (200, 204):
                print(f"   Done.", flush=True)
            elif r.status_code == 404:
                print(f"   Skipped (Not found).", flush=True)
            else:
                print(f"   Failed: {r.status_code} {r.text}", flush=True)
        except Exception as e:
            print(f"   Error: {e}", flush=True)

    # 3. Clean Members and Organizations
    if admin_user_ids:
        print("Cleaning others from org_members...", flush=True)
        # delete?user_id=not.in.(id1,id2)
        u_list = ",".join([f'"{uid}"' for uid in admin_user_ids])
        del_url = f"{base_rest}/org_members?user_id=not.in.({u_list})"
        requests.delete(del_url, headers=headers, timeout=10)

    if admin_org_ids:
        print("Cleaning other organizations...", flush=True)
        o_list = ",".join([f'"{oid}"' for oid in admin_org_ids])
        del_url = f"{base_rest}/organizations?id=not.in.({o_list})"
        requests.delete(del_url, headers=headers, timeout=10)

    print("\n" + "="*50, flush=True)
    print("CLEANUP COMPLETE! (REST Mode)", flush=True)
    print("====================================", flush=True)

if __name__ == "__main__":
    main()
