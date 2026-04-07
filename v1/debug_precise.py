from softone.client import fetch_stock
import json

stock = fetch_stock()
if stock:
    print("KEYS TOP LEVEL:", list(stock[0].keys()))
    print("SAMPLE TYPE OF ONE KEY:", type(list(stock[0].keys())[0]))
    # check for trailing spaces in keys
    for k in stock[0].keys():
        if k != k.strip():
            print(f"WARNING: Key '{k}' has trailing/leading spaces!")
    
    # check specific keys
    item = stock[0]
    print(f"item_code: {item.get('item_code')}")
    print(f"physical_stock: {item.get('physical_stock')}")
    print(f"available_stock: {item.get('available_stock')}")
    
else:
    print("No data")
