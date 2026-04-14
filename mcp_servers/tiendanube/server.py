"""
MCP Server: Tiendanube E-commerce

Connects Claude Code to the Tiendanube REST API.
All tools are READ-classified (no order mutations in MVP scope).

Mock mode: set TIENDANUBE_MOCK=true in .env to use local fixture data
instead of hitting the real API. Use this when credentials are not yet
available or for offline demo runs.

Run:  python mcp_servers/tiendanube/server.py
Env:  TIENDANUBE_STORE_ID, TIENDANUBE_ACCESS_TOKEN
      TIENDANUBE_MOCK=true  (optional, activates mock mode)
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tiendanube")

STORE_ID    = os.environ.get("TIENDANUBE_STORE_ID", "")
TOKEN       = os.environ.get("TIENDANUBE_ACCESS_TOKEN", "")
MOCK        = os.environ.get("TIENDANUBE_MOCK", "false").lower() == "true"
API_VERSION = os.environ.get("TIENDANUBE_API_VERSION", "2025-03")

BASE_URL = f"https://api.tiendanube.com/{API_VERSION}/{STORE_ID}"
HEADERS  = {
    "Authentication": f"bearer {TOKEN}",
    "User-Agent": "SpineAgent/1.0 (demo@spineagent.dev)",
    "Content-Type": "application/json",
}


# ── Mock fixtures (map to AdventureWorks demo orders) ────────────────────────

MOCK_ORDERS = {
    "9981": {
        "id": 9981,
        "number": 9981,
        "status": "closed",
        "payment_status": "paid",
        "shipping_status": "shipped",
        "adventureworks_ref": 43659,
        "customer": {
            "name": "Christy Zhu",
            "email": "christy.zhu@example.com",
            "phone": "+5491112345678",
        },
        "products": [
            {
                "product_id": 776,
                "name": "Mountain-200 Black, 38",
                "sku": "BK-M68B-38",
                "quantity": 1,
                "price": "2024.99",
            }
        ],
        "total": "20565.62",
        "currency": "ARS",
        "created_at": "2011-05-31T00:00:00-03:00",
        "updated_at": "2011-06-07T00:00:00-03:00",
        "note": "Demo order mapped from AdventureWorks #43659",
    },
    "9982": {
        "id": 9982,
        "number": 9982,
        "status": "open",
        "payment_status": "paid",
        "shipping_status": "unshipped",
        "adventureworks_ref": 43660,
        "customer": {
            "name": "Jon Yang",
            "email": "jon.yang@example.com",
            "phone": "+5491198765432",
        },
        "products": [
            {
                "product_id": 711,
                "name": "Road-650 Red, 52",
                "sku": "BK-R50R-52",
                "quantity": 1,
                "price": "2443.35",
                "stock": 0,
            },
            {
                "product_id": 879,
                "name": "Water Bottle",
                "sku": "WB-H098",
                "quantity": 3,
                "price": "4.50",
                "stock": 47,
            },
        ],
        "total": "3578.27",
        "currency": "ARS",
        "created_at": "2024-01-08T10:00:00-03:00",
        "updated_at": "2024-01-08T10:00:00-03:00",
        "note": "Demo order mapped from AdventureWorks #43660 — stock issue on main item",
    },
}

MOCK_ORDERS_LIST = list(MOCK_ORDERS.values())


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_order(order_id: str) -> dict:
    """
    Fetch a single order from Tiendanube by order ID.
    Returns order status, customer info, line items, payment and shipping
    status. Use this to get the live e-commerce view of an order to
    complement the AdventureWorks spine data.
    """
    if MOCK:
        order = MOCK_ORDERS.get(str(order_id))
        if not order:
            return {"error": f"Mock order '{order_id}' not found. Available: {list(MOCK_ORDERS.keys())}"}
        return order

    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{BASE_URL}/orders/{order_id}", headers=HEADERS)
        if r.status_code == 404:
            return {"error": f"Order {order_id} not found in Tiendanube"}
        r.raise_for_status()
        return r.json()


@mcp.tool()
def list_orders(
    status: str = "",
    page: int = 1,
    per_page: int = 20,
) -> list:
    """
    List orders from Tiendanube with optional filtering by status.
    Valid status values: open, closed, cancelled.
    Use this in Monitor mode to scan for orders needing attention.
    """
    if MOCK:
        if status:
            return [o for o in MOCK_ORDERS_LIST if o["status"] == status]
        return MOCK_ORDERS_LIST

    params = {"page": page, "per_page": per_page}
    if status:
        params["status"] = status

    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{BASE_URL}/orders", headers=HEADERS, params=params)
        # Tiendanube returns 404 {"description": "Last page is 0"} for empty collections
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_product(product_id: str) -> dict:
    """
    Fetch product details from Tiendanube including current stock levels,
    variants, and pricing. Use this to check availability when an order
    has a stock issue.
    """
    if MOCK:
        mock_products = {
            "776": {"id": 776, "name": "Mountain-200 Black, 38", "stock": 12, "price": "2024.99"},
            "711": {"id": 711, "name": "Road-650 Red, 52",       "stock": 0,  "price": "2443.35"},
            "879": {"id": 879, "name": "Water Bottle",            "stock": 47, "price": "4.50"},
        }
        p = mock_products.get(str(product_id))
        if not p:
            return {"error": f"Mock product '{product_id}' not found"}
        return p

    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{BASE_URL}/products/{product_id}", headers=HEADERS)
        if r.status_code == 404:
            return {"error": f"Product {product_id} not found in Tiendanube"}
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_store_info() -> dict:
    """
    Fetch general information about the Tiendanube store (name, currency,
    country, plan). Useful for contextualizing order data.
    """
    if MOCK:
        return {
            "id": STORE_ID or "demo-store",
            "name": "SpineAgent Demo Store",
            "country": "AR",
            "currency": "ARS",
            "plan": "business",
            "mode": "mock — set TIENDANUBE_MOCK=false and provide real credentials to connect",
        }

    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{BASE_URL}/store", headers=HEADERS)
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    if MOCK:
        print("[tiendanube] Running in MOCK mode — no real API calls will be made")
    elif not STORE_ID or not TOKEN:
        print("[tiendanube] WARNING: TIENDANUBE_STORE_ID or TIENDANUBE_ACCESS_TOKEN not set")
        print("[tiendanube] Set TIENDANUBE_MOCK=true in .env to use mock data instead")
    mcp.run()
