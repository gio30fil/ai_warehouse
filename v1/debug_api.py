from softone.client import fetch_products, fetch_stock
import json

products = fetch_products()
stock = fetch_stock()

print("FIRST PRODUCT KEYS:", products[0].keys() if products else "NONE")
print("FIRST STOCK ENTRY:", stock[0] if stock else "NONE")
