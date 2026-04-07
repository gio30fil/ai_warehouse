from softone.client import fetch_stock
import json

stock = fetch_stock()
target = "004977"
for item in stock:
    if item.get('item_code') == target:
        print("FOUND", target)
        print(json.dumps(item, indent=2))
        break
else:
    print(target, "NOT FOUND in SoftOne response")
