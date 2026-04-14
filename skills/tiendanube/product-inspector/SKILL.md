---
name: product-inspector
description: >
  Use this skill when asked to fetch or look up a product from the store:
  "dame el producto 776", "qué stock tiene el producto 711?", "mostrame el
  precio del producto 879", "traeme info del artículo con id X", "cuántas
  unidades quedan del producto X?", or any question that requires retrieving
  product details, stock levels, or pricing from Tienda Nube. This is the
  Tienda Nube channel view — it reads the live store catalog.
metadata:
  tools:
    - get_product
  classification: READ
  approval_required: false
---

# Skill: Product Inspector (Tienda Nube)

## What This Skill Does

Fetches a single product from the Tienda Nube store using the `get_product`
MCP tool. Returns a structured **product card** with name, price, and stock
levels per variant. This is a read-only operation — it never modifies catalog
data.

---

## Step 1 — Resolve the Product ID

Extract the product ID from the user's message.

| Input type | Strategy |
|---|---|
| Explicit ID ("producto 776") | Use directly as `product_id` |
| Name or SKU | Inform the user that `get_product` requires a numeric ID; ask for it |
| "El último / el más caro" | Explain that listing/filtering is out of scope; ask for a specific ID |

If no product ID can be resolved, ask the user: `¿Podés darme el ID numérico del producto?`

---

## Step 2 — Call the Tool

```
tool: get_product
input:
  product_id: "<id>"
```

**Mock mode note:** if `TIENDANUBE_MOCK=true`, the tool returns fixture data
for IDs `776`, `711`, and `879`. Any other ID returns a mock 404 message.

---

## Step 3 — Parse the Response

The tool returns a JSON object. Extract:

| Field | Description |
|---|---|
| `id` | Numeric product ID |
| `name` | Product name (may be a dict `{"es": "..."}`) |
| `variants[].price` | Price per variant |
| `variants[].stock` | Stock units per variant |
| `variants[].sku` | SKU per variant (if present) |

If the response contains an error key or a 404 message, surface it clearly
to the user and stop.

---

## Step 4 — Format the Product Card

Output as a structured card:

```
PRODUCTO #<id>
  Nombre:   <name>
  Variantes (<N> variante/s):
    [SKU: <sku>]  Precio: $<price>  |  Stock: <stock> unidades
    ...

  Estado de stock:
    ✓ Con stock     → stock > 5
    ⚠ Stock bajo    → 1 ≤ stock ≤ 5
    ✗ Sin stock     → stock = 0
```

If there is only one variant with no distinguishing attributes, skip the
variants table and show price and stock inline.

---

## Step 5 — Suggest Next Actions

After the card, offer context-aware suggestions:

- If stock is 0 or low → `"¿Querés que te avise cuando se reponga?"` (for future alert skill)
- If the user seems to be checking before placing an order → `"¿Necesitás cruzar este producto con pedidos pendientes?"`

---

## Constraints

- Read-only — never call tools that modify the catalog.
- Do not fabricate stock values — always use the tool response.
- If the tool is unreachable (network error, missing env vars), say so clearly
  and suggest verifying `TIENDANUBE_ACCESS_TOKEN` and `TIENDANUBE_STORE_ID`.
- Do not expose the raw bearer token or store credentials in any response.
