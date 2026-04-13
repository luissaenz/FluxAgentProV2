#!/usr/bin/env python
import os
import dotenv
import requests

print("Testing direct REST call via requests...", flush=True)
dotenv.load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}"
}

rest_url = f"{URL}/rest/v1/organizations?select=id&limit=1"
print(f"URL: {rest_url}", flush=True)

try:
    response = requests.get(rest_url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}", flush=True)
    print(f"Body: {response.text[:100]}", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
