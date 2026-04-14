import json
import re
import shutil

# Restore original 50-tool seed
shutil.copy("temp_seed.json", "data/service_catalog_seed.json")

# Verify restore
data = json.load(open("data/service_catalog_seed.json"))
print(f"Restored to: {len(data['tools'])} tools")

# Now run expand script
import subprocess

result = subprocess.run(
    ["python", "scripts/expand_catalog.py"], capture_output=True, text=True
)
print(result.stdout)

# Check final count
data = json.load(open("data/service_catalog_seed.json"))
print(f"Final count: {len(data['tools'])} tools")
