from softone.client import login, fetch_products

# Step 1: Authenticate and retrieve the clientId
client_id = login()

if client_id:
    print(f"\n[KEY] clientId received: {client_id}\n")

    # Step 2: Use the session to fetch products
    data = fetch_products()
    print(data[:2])
else:
    print("[STOP] Cannot proceed - login failed.")