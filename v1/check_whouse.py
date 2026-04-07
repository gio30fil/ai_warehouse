from softone.client import fetch_stock
import json

print("FETCHING FOR WHOUSE 100:")
res100 = fetch_stock("100")
target = "004977"
for item in res100:
    if item.get('item_code') == target:
        print(f"WH100 Stock for {target}: {item.get('physical_stock')}")
        break
else:
    print(f"{target} NOT FOUND in WH100 response")

print("\nFETCHING ALL (NO WHOUSE_CODE):")
res_all = fetch_stock()
for item in res_all:
    if item.get('item_code') == target:
        print(f"TOTAL Stock for {target}: {item.get('physical_stock')}")
        break

