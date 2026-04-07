import requests

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
LOGIN_URL = "https://ifsas.oncloud.gr/s1services"
BASE_URL = "https://ifsas.oncloud.gr/s1services/js/CLIfsasWebConnector.S1Lib/ApiServices"

# ---------------------------------------------------------------------------
# Login credentials & IDs  (from postman.json / Env_Ifsas)
# ---------------------------------------------------------------------------
USERNAME = "WebConnector"
PASSWORD = "WebConnector!1"
APPID    = "2222"
COMPANY  = "100"
BRANCH   = "1000"
MODULE   = "0"
REFID    = "2222"

# Cached clientId returned after a successful login
CLIENT_ID = None


def login() -> str | None:
    """
    Authenticate against the SoftOne web services.

    Sends a 'login' service request to the main endpoint using the
    credentials and IDs defined in postman.json (Env_Ifsas environment).

    Returns:
        str: The clientId token to be used in subsequent API calls.
        None: If authentication failed.
    """
    global CLIENT_ID

    payload = {
        "service":  "login",
        "username": USERNAME,
        "password": PASSWORD,
        "appId":    APPID,
        "company":  COMPANY,
        "branch":   BRANCH,
        "module":   MODULE,
        "refid":    REFID,
    }

    response = requests.post(LOGIN_URL, json=payload)
    data = response.json()

    print("LOGIN RESPONSE:", data)

    if data.get("success"):
        CLIENT_ID = data.get("clientID")
        print(f"[OK] Logged in - clientId: {CLIENT_ID}")
        return CLIENT_ID

    print("[ERROR] Login failed:", data.get("error"))
    return None


def fetch_products():
    global CLIENT_ID

    # Auto-login if we don't have a session yet
    if not CLIENT_ID:
        CLIENT_ID = login()
        if not CLIENT_ID:
            print("[ABORT] fetch_products: login failed, aborting.")
            return []

    payload = {
        "service": "getItems",
        "clientid": CLIENT_ID,
        "appid": APPID,
        "upddate_from": "2026-03-23T00:00:00"
    }

    response = requests.post(BASE_URL, json=payload)

    data = response.json()

    print("RESPONSE:", data)

    if data.get("success"):

        products = data.get("data", [])

        print(f"[OK] Loaded {len(products)} products")

        return products

    print("[ERROR] fetch_products:", data.get("error"))
    return []


def fetch_stock(whouse_code: str | None = None):
    """
    Fetches stock levels per warehouse from SoftOne.
    If whouse_code is None, fetches for all warehouses.
    """
    global CLIENT_ID

    if not CLIENT_ID:
        CLIENT_ID = login()
        if not CLIENT_ID:
            print("[ABORT] fetch_stock: login failed.")
            return []

    payload = {
        "service": "getItemsStockPerWhouse",
        "clientid": CLIENT_ID,
        "appid": APPID
    }

    if whouse_code:
        payload["whouse_code"] = whouse_code

    try:
        response = requests.post(BASE_URL, json=payload)
        data = response.json()

        if data.get("success"):
            return data.get("data", [])
        
        print("[ERROR] fetch_stock:", data.get("error"))
    except Exception as e:
        print(f"[ERROR] fetch_stock exception: {e}")
    
    return []


def fetch_pending_orders():
    """
    Fetches pending sales orders from SoftOne.
    """
    global CLIENT_ID

    if not CLIENT_ID:
        CLIENT_ID = login()
        if not CLIENT_ID:
            print("[ABORT] fetch_pending_orders: login failed.")
            return []

    payload = {
        "service": "getSalesDocuments",
        "clientid": CLIENT_ID,
        "appid": APPID
    }

    try:
        # Increase timeout as SoftOne API is slow
        response = requests.post(BASE_URL, json=payload, timeout=60)
        data = response.json()

        if data.get("success"):
            return data.get("data", [])
        
        print("[ERROR] fetch_pending_orders:", data.get("error"))
    except Exception as e:
        print(f"[ERROR] fetch_pending_orders exception: {e}")
    
    return []