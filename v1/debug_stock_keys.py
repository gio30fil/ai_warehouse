from softone.client import fetch_stock
import json

stock = fetch_stock()
if stock:
    print("KEYS IN FIRST ENTRY:", stock[0].keys())
    # print sample
    print("SAMPLE ENTRY:", json.dumps(stock[0], indent=2))
else:
    print("No stock data")
