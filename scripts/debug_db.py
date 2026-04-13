#!/usr/bin/env python
import os
import sys

# DEBUG VERSION
print("DEBUG: 1. Loading libraries...", flush=True)
from supabase import create_client
import dotenv

print("DEBUG: 2. Loading .env...", flush=True)
dotenv.load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

print(f"DEBUG: 3. URL found: {URL}", flush=True)
print(f"DEBUG: 4. Key found (len): {len(KEY) if KEY else 0}", flush=True)

print("DEBUG: 5. Creating client...", flush=True)
try:
    client = create_client(URL, KEY)
    print("DEBUG: 6. Client created successfully.", flush=True)
except Exception as e:
    print(f"DEBUG: 6. Client creation FAILED: {e}", flush=True)
    sys.exit(1)

print("DEBUG: 7. Testing small query...", flush=True)
try:
    res = client.table("organizations").select("id").limit(1).execute()
    print(f"DEBUG: 8. Query done. Rows: {len(res.data)}", flush=True)
except Exception as e:
    print(f"DEBUG: 8. Query FAILED: {e}", flush=True)

print("DEBUG: 9. End of test.", flush=True)
