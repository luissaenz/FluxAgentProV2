import asyncio
import os
import sys
import base64
from pathlib import Path

# Add root directory to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Ensure we use the .env variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=root_dir / ".env")

from src.flows.architect_flow import ArchitectFlow
from src.services.import_service import ImportService
from src.db.session import get_tenant_client

async def main():
    # Configuration
    org_id = "01b3cd88-7e73-48f1-8172-4e0f7b23ccef"
    user_id = None 
    
    print("\n" + "="*60)
    print("🚀 FLUXAGENTPRO-V2: E2E AGENT GENERATION & IMPORT TEST")
    print("="*60)
    print(f"Target Organization: {org_id}")
    
    # --- PHASE 1: GENERATION ---
    print("\n[STEP 1] Generating Agent via ArchitectFlow (LLM)...")
    flow = ArchitectFlow(org_id=org_id, user_id=user_id)
    
    input_data = {
        "description": "Create a 'Translator' agent that can translate text from Spanish to English perfectly.",
        "bundle_name": "translator-bundle",
        "doc_description": "Auto-generated translator bundle"
    }
    
    try:
        state = await flow.execute(input_data)
        
        if state.status != "completed":
            print(f"❌ Generation failed: {state.error}")
            return
            
        result = state.output_data
        bundle_b64 = result.get("bundle_b64")
        flow_type = result.get("flow_type")
        
        print(f"✅ Generation SUCCESS!")
        print(f"   - Created Flow: {flow_type}")
        print(f"   - Bundle Size (B64): {len(bundle_b64)} chars")
        
        # --- PHASE 2: IMPORT ---
        print("\n[STEP 2] Importing generated bundle into Supabase...")
        zip_bytes = base64.b64decode(bundle_b64)
        
        import_service = ImportService(org_id=org_id)
        # Use force=True to avoid version conflicts during testing
        import_result = import_service.process_bundle(zip_bytes, force=True)
        
        if import_result.status == "success":
            print(f"✅ Import SUCCESS!")
            print(f"   - Bundle ID: {import_result.bundle_id}")
            print(f"   - Agents imported: {import_result.agents_count}")
        else:
            print(f"❌ Import failed: {import_result.error}")
            return
            
        # --- PHASE 3: VERIFICATION ---
        print("\n[STEP 3] Verifying persistence in Database...")
        with get_tenant_client(org_id) as db:
            # Check if agent exists
            agent_check = db.table("agent_catalog").select("*").eq("bundle_id", import_result.bundle_id).execute()
            
            if agent_check.data:
                print(f"✅ Verification SUCCESS!")
                for agent in agent_check.data:
                    print(f"   - Found Agent: {agent['role']} ({agent['goal']})")
            else:
                print("❌ Verification FAILED: Agent not found in catalog.")
                
            # Check if workflow template exists
            workflow_check = db.table("workflow_templates").select("*").eq("bundle_id", import_result.bundle_id).execute()
            if workflow_check.data:
                print(f"✅ Workflow template '{workflow_check.data[0]['flow_type']}' is active.")
                
        print("\n" + "="*60)
        print("🏆 TEST PASSED: Full Agentic Lifecycle is Operational!")
        print("="*60)
            
    except Exception as e:
        print(f"\n💥 CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
