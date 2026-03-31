"""Manual Test Flow — Bypasses FastAPI to test the core logic directly."""

import asyncio
import sys
import os
from uuid import uuid4

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.flows.generic_flow import GenericFlow
    from src.config import get_settings
except ImportError as e:
    print(f"Error importing project modules: {e}")
    sys.exit(1)

async def main():
    # Use the ORG_ID from seeding
    org_id = "c63290a1-32df-46e3-9ddd-266ea72b8721"
    
    print(f"🚀 Starting Manual Test for Org: {org_id}")
    print(f"🔗 Using LLM Provider: {get_settings().llm_provider}")
    
    flow = GenericFlow(org_id=org_id)
    
    input_data = {"text": "Explain in one sentence why AI agents are the future of automation."}
    correlation_id = str(uuid4())
    
    try:
        print("⏳ Executing flow (this will call the LLM)...")
        state = await flow.execute(input_data, correlation_id)
        
        print("\n" + "="*50)
        print(f"✅ FLOW COMPLETED SUCCESSFULLY!")
        print(f"   Task ID: {state.task_id}")
        print(f"   Status: {state.status}")
        print(f"   Result: {state.output_data}")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ FLOW FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
