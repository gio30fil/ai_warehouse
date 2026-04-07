from softone.client import fetch_stock
stock_all = fetch_stock()
target="004977"
for item in stock_all:
    if item.get('item_code') == target:
        print(f"PRODUCT {target} TOTAL {item.get('physical_stock')}")
        for wh in item.get('stock_per_warehouse', []):
            print(f"  WH {wh.get('whouse_code','?')} ({wh.get('whouse_name','?')}): {wh.get('physical_stock ',wh.get('physical_stock',0))}")
        break

