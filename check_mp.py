import json

data = json.load(open("data/service_catalog_seed.json"))
print(f"Total tools: {len(data['tools'])}")

# Check MercadoPago base_url as per Testing section
mp_tools = [t for t in data["tools"] if "mercadopago" in t["id"]]
for t in mp_tools[:2]:
    print(f"{t['id']}: base_url = {t['provider'].get('base_url')}")
