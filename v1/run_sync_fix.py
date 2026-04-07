from app.services import sync_softone_stock
from app.database import get_connection

print("Starting stock sync with fixed keys...")
count = sync_softone_stock()
print(f"Updated {count} products in database.")

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT stock FROM products WHERE kodikos = '004977'")
row = cursor.fetchone()
if row:
    print(f"Product 004977 now has stock: {row[0]}")
else:
    print("Product 004977 not found in DB")
conn.close()
