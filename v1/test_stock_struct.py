from softone.client import login, BASE_URL, APPID
import requests
import json

cli = login()
if cli:
    payload = {
        "service": "getItemsStockPerWhouse",
        "clientid": cli,
        "appid": APPID,
        # "whouse_code": "100" 
    }

    r = requests.post(BASE_URL, json=payload)
    data = r.json()
    if data.get('success'):
        entries = data.get('data', [])
        if entries:
            # Group by item code to see if there are multiple warehouses for each.
            by_code = {}
            for e in entries:
                code = e.get('code')
                if code not in by_code:
                    by_code[code] = []
                by_code[code].append(e)
            
            # Find one with multiple entries
            multi = [c for c, e in by_code.items() if len(e) > 1]
            if multi:
                print(f"FOUND {len(multi)} ITEMS WITH MULTIPLE WAREHOUSES")
                print("EXAMPLE MULTI:", json.dumps(by_code[multi[0]], indent=2))
            else:
                print("NO ITEMS FOUND WITH MULTIPLE WAREHOUSES")
                print("EXAMPLE SINGLE ENTRY:", json.dumps(entries[0], indent=2))
