"""Developer Seeding Script — Creates a default organization for testing."""

import sys
import os

# Add src to path if needed (though uv run usually handles this if called correctly)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.db.session import get_service_client
    from src.config import get_settings
except ImportError as e:
    print(f"Error importing project modules: {e}")
    sys.exit(1)

def seed():
    print("Starting Developer Data Seeding...")
    
    try:
        get_settings()
        supabase = get_service_client()
        
        # 1. Check if organization exists or create a new one
        org_name = "Empresa Demo"
        org_slug = "empresa-demo"
        
        # Use simple select to check existence
        res = supabase.table("organizations").select("id").eq("slug", org_slug).execute()
        
        if res.data:
            org_id = res.data[0]["id"]
            print(f"Organization '{org_name}' already exists.")
        else:
            print(f"Creating organization '{org_name}'...")
            res = supabase.table("organizations").insert({
                "name": org_name,
                "slug": org_slug
            }).execute()
            
            if not res.data:
                print("Failed to create organization. Check your Supabase permissions/RLS.")
                return
                
            org_id = res.data[0]["id"]
            print(f"Organization created successfully! ID: {org_id}")
            
        print("\n" + "="*50)
        print("PHASE 1 SEEDING COMPLETE!")
        print(f"   ORG_ID: {org_id}")
        print("   Use this UUID in the 'X-Org-ID' Header for your API requests.")
        print("Developer Data Seeding completed successfully.")
        print("="*50)

    except Exception as e:
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed()
