from softone.client import fetch_stock
stock = fetch_stock()
target = "004977"
for item in stock:
    if item.get('item_code') == target:
        print(f"Product: {target}")
        print(f"Physical Stock: {item.get('physical_stock')}")
        print(f"Available Stock: {item.get('available_stock')}")
        break
