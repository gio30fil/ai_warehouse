from softone.client import fetch_stock
from app.services import sync_softone_stock
from app.database import get_connection
import json

stock_data = fetch_stock()
target = "004977"
for item in stock_data:
    if item.get('item_code') == target:
        print("SOFTONE ITEM FOR", target)
        print(json.dumps(item, indent=2))
        break

print("\nStarting sync...")
sync_softone_stock()

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT stock, description FROM products WHERE kodikos = ?", (target,))
row = cursor.fetchone()
print(f"DATABASE {target}: Stock={row[0]}, Desc={row[1]}")
conn.close()
