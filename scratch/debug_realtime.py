import asyncio
import os
import uuid
from supabase import create_client, AsyncClient
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    org_id = os.getenv("TEST_ORG_ID")

    print(f"URL: {url}")
    print(f"Key ends in: {key[-5:] if key else 'None'}")

    from supabase import acreate_client, AsyncClientOptions
    
    client: AsyncClient = await acreate_client(
        url, 
        key,
        options=AsyncClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10
        )
    )

    task_id = f"debug-{uuid.uuid4().hex[:8]}"
    received = []

    def callback(payload):
        print(f"GOT EV: {payload}")
        received.append(payload)

    print(f"Subscribing to domain_events for task_id={task_id}")
    channel = client.channel(f"debug_chan_{task_id}")
    channel.on_postgres_changes(
        event="INSERT",
        schema="public",
        table="domain_events",
        # filter=f"aggregate_id=eq.{task_id}", # Try without filter first
        callback=callback
    )
    
    res = await channel.subscribe()
    print(f"Subscribe result: {res}")
    
    # Wait a bit for WS to be ready
    await asyncio.sleep(2)

    print("Inserting event...")
    # Insert via RPC or direct (service_role can direct insert)
    # We must set current_org_id if we want RLS to pass for non-service_role, 
    # but here we are service_role.
    
    # Simulate what EventStore does
    ev_data = {
        "org_id": org_id,
        "aggregate_type": "task",
        "aggregate_id": task_id,
        "event_type": "debug_event",
        "payload": {"msg": "hello"},
        "sequence": 1
    }
    
    # We need to set app.org_id for the insert policy if it's strict, 
    # but 010 says service_role bypasses it.
    insert_res = await client.table("domain_events").insert(ev_data).execute()
    print(f"Insert result: {insert_res.data}")

    print("Waiting 10s for event via Realtime...")
    for _ in range(10):
        if received:
            print("SUCCESS: Event received!")
            break
        await asyncio.sleep(1)
        print(".", end="", flush=True)
    print()

    if not received:
        print("FAILURE: No events received via Realtime.")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
