import os
from dotenv import load_dotenv
from supabase import create_client

def test():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    print(f"URL: {url}")
    print(f"Key present: {bool(key)}")
    if url and key:
        db = create_client(url, key)
        res = db.table("service_catalog").select("count").execute()
        print(f"Connection OK: {res}")

if __name__ == "__main__":
    test()
