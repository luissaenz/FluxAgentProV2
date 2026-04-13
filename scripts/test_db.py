#!/usr/bin/env python
import sys
import os
import time

# Set Python path to find src if script is in /scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.session import get_service_client

def main():
    print("Test: Starting...", flush=True)
    start = time.time()
    print("Test: Getting client...", flush=True)
    supabase = get_service_client()
    print(f"Test: Client obtained in {time.time()-start:.2f}s", flush=True)
    
    start = time.time()
    print("Test: Executing query on 'organizations'...", flush=True)
    try:
        res = supabase.table("organizations").select("id").limit(1).execute()
        print(f"Test: Query done in {time.time()-start:.2f}s. Result rows: {len(res.data)}", flush=True)
    except Exception as e:
        print(f"Test: Query failed: {e}", flush=True)

if __name__ == "__main__":
    main()
