from softone.client import login, BASE_URL, APPID
import requests
import json

cli = login()
if not cli:
    print("Login failed")
    exit()

# Try without whouse_code or with '*' to see if it returns all
payload = {
    "service": "getItemsStockPerWhouse",
    "clientid": cli,
    "appid": APPID,
    # "whouse_code": "100" # Let's see if we can omit it
}

r = requests.post(BASE_URL, json=payload)
data = r.json()
print("NO WHOUSE_CODE SUCCESS:", data.get('success'))
if data.get('success'):
    print("TOTAL STOCK ENTRIES:", len(data.get('data', [])))
    if data.get('data'):
        print("FIRST ENTRY WHOUSE:", data.get('data')[0].get('whouse'))
        # Check if multiple warehouses exist for the same item code
        # ...

# Try to get warehouse list
payload_wh = {
    "service": "getWarehouses",
    "clientid": cli,
    "appid": APPID
}
r_wh = requests.post(BASE_URL, json=payload_wh)
print("GET WAREHOUSES RESPONSE:", r_wh.json())
