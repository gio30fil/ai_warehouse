from softone.client import login, BASE_URL, APPID
import requests
import json

cli = login()
if not cli:
    print("Login failed")
    exit()

services_to_try = [
    "getReservedItems",
    "getPendingOrders",
    "getSalesOrders",
    "getCustomerReservations",
    "getReservedStock",
    "getPendingVouchers",
    "getOrders"
]

for svc in services_to_try:
    payload = {
        "service": svc,
        "clientid": cli,
        "appid": APPID
    }
    try:
        r = requests.post(BASE_URL, json=payload)
        data = r.json()
        print(f"Service '{svc}': Success={data.get('success')}")
        if data.get('success'):
            print(f"  Sample data: {json.dumps(data.get('data', [])[:1], indent=2)}")
    except Exception as e:
        print(f"Service '{svc}': Error {e}")
