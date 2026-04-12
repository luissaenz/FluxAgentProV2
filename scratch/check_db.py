import asyncio
import os
from supabase import acreate_client
from dotenv import load_dotenv

load_dotenv()

async def run():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    c = await acreate_client(url, key)
    try:
        res = await c.rpc('debug_realtime_config', {}).execute()
        print("CONFIG:", res.data)
    except Exception as e:
        print("ERROR:", e)
    await c.aclose()

if __name__ == "__main__":
    asyncio.run(run())
