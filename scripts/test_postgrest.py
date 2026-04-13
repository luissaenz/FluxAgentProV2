#!/usr/bin/env python
import os
import dotenv
from postgrest import SyncPostgrestClient

print("Testing direct Postgrest client...", flush=True)
dotenv.load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}"
}

rest_url = f"{URL}/rest/v1"
print(f"Connecting to: {rest_url}", flush=True)

try:
    client = SyncPostgrestClient(rest_url, headers=headers)
    print("Client initialized. Querying...", flush=True)
    res = client.from_("organizations").select("id").limit(1).execute()
    print(f"Got result: {len(res.data)} rows", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
