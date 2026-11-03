import os
import csv
import requests
import uuid
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")

SUPPLIER_CSV_URL = (
    "https://raw.githubusercontent.com/"
    "zselyem/SunwaveSupplier/main/SunwaveProducts.csv"
)
SHOPIFY_API_VERSION = "2026-10"


# --------------------------------------------------
# Shopify authentication
# --------------------------------------------------

def get_access_token():

    response = requests.post(
        f"https://{SHOPIFY_STORE}/admin/oauth/access_token",
        json={
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    )

    response.raise_for_status()

    return response.json()["access_token"]


# --------------------------------------------------
# Get products from Shopify
# --------------------------------------------------

def get_shopify_products(access_token, location_id):

    query = """
    {
      products(first: 20) {
        nodes {
          id
          title

          variants(first: 10) {
            nodes {
              id
              sku
              price

              inventoryItem {
                id

                inventoryLevels(first: 10) {
                  nodes {
                    location {
                      id
                      name
                    }

                    quantities(names: ["available"]) {
                      name
                      quantity
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        },
        json={"query": query}
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    shopify_products = {}

    products = data["data"]["products"]["nodes"]

    for product in products:

        for variant in product["variants"]["nodes"]:

            sku = variant["sku"]

            if not sku:
                continue

            inventory = None

            inventory_levels = (
                variant["inventoryItem"]["inventoryLevels"]["nodes"]
            )

            for level in inventory_levels:

                if level["location"]["id"] != location_id:
                    continue

                for quantity in level["quantities"]:

                    if quantity["name"] == "available":
                        inventory = quantity["quantity"]

            if inventory is None:
                inventory = 0

            shopify_products[sku] = {
                "title": product["title"],
                "price": float(variant["price"]),
                "inventory": inventory,
                "product_id": product["id"],
                "variant_id": variant["id"],
                "inventory_item_id": variant["inventoryItem"]["id"]
            }

    return shopify_products

    query = """
    {
      products(first: 20) {
        nodes {
          id
          title

          variants(first: 10) {
            nodes {
              id
              sku
              price

              inventoryItem {
                id

                inventoryLevels(first: 10) {
                  nodes {
                    quantities(names: ["available"]) {
                      name
                      quantity
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        },
        json={
            "query": query
        }
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    shopify_products = {}

    products = data["data"]["products"]["nodes"]

    for product in products:

        for variant in product["variants"]["nodes"]:

            sku = variant["sku"]

            if not sku:
                continue

            inventory = 0

            inventory_levels = (
                variant["inventoryItem"]["inventoryLevels"]["nodes"]
            )

            for level in inventory_levels:

                for quantity in level["quantities"]:

                    if quantity["name"] == "available":
                        inventory += quantity["quantity"]

            shopify_products[sku] = {
                "title": product["title"],
                "price": float(variant["price"]),
                "inventory": inventory,
                "product_id": product["id"],
                "variant_id": variant["id"],
                "inventory_item_id": variant["inventoryItem"]["id"]
            }

    return shopify_products

def get_shopify_location(access_token):

    query = """
    {
      locations(first: 10) {
        nodes {
          id
          name
          isActive
        }
      }
    }
    """

    response = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        },
        json={
            "query": query
        }
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    locations = data["data"]["locations"]["nodes"]

    for location in locations:

        if location["isActive"]:

            return {
                "id": location["id"],
                "name": location["name"]
            }

    raise Exception("No active Shopify location found.")

def update_inventory(
    access_token,
    inventory_item_id,
    location_id,
    current_quantity,
    new_quantity
):

    mutation = """
        mutation SetInventoryQuantity(
            $input: InventorySetQuantitiesInput!
            $idempotencyKey: String!
        ) {
            inventorySetQuantities(input: $input)
                @idempotent(key: $idempotencyKey) {

                inventoryAdjustmentGroup {
                    createdAt
                    reason

                    changes {
                        name
                        delta
                    }
                }

                userErrors {
                    field
                    message
                }
            }
        }
        """

    idempotency_key = str(uuid.uuid4())
    variables = {
    "input": {
        "name": "available",
        "reason": "correction",

        "quantities": [
            {
                "inventoryItemId": inventory_item_id,
                "locationId": location_id,
                "quantity": new_quantity,
                "changeFromQuantity": current_quantity
            }
        ]
    },

    "idempotencyKey": idempotency_key
    }

    response = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": variables
        }
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    user_errors = (
        data["data"]
        ["inventorySetQuantities"]
        ["userErrors"]
    )

    if user_errors:
        raise Exception(user_errors)

    return data["data"]["inventorySetQuantities"]  
# --------------------------------------------------
# Load supplier products
# --------------------------------------------------

def load_supplier_products():

    response = requests.get(
        SUPPLIER_CSV_URL
    )

    response.raise_for_status()

    csv_text = response.text

    reader = csv.DictReader(
        csv_text.splitlines()
    )

    return list(reader)


# --------------------------------------------------
# Compare supplier and Shopify
# --------------------------------------------------


def compare_products(supplier_products, shopify_products):

    changes = []

    print()
    print("=" * 60)
    print("SUPPLIER → SHOPIFY COMPARISON")
    print("=" * 60)

    for supplier in supplier_products:

        sku = supplier["SKU"]

        supplier_price = float(
            supplier["Price"]
        )

        supplier_inventory = int(
            supplier["Inventory quantity"]
        )

        print()
        print("SKU:", sku)

        if sku not in shopify_products:

            print("STATUS: NOT FOUND IN SHOPIFY")
            continue

        shopify = shopify_products[sku]

        if supplier_price != shopify["price"]:

            print(
                f"PRICE DIFFERENCE: "
                f"Supplier={supplier_price} "
                f"Shopify={shopify['price']}"
            )

        else:

            print("PRICE: OK")

        if supplier_inventory != shopify["inventory"]:

            print(
                f"INVENTORY DIFFERENCE: "
                f"Supplier={supplier_inventory} "
                f"Shopify={shopify['inventory']}"
            )

            changes.append({
                "sku": sku,
                "inventory_item_id": shopify["inventory_item_id"],
                "current_inventory": shopify["inventory"],
                "new_inventory": supplier_inventory
            })

        else:

            print(
                f"INVENTORY: OK "
                f"(Supplier={supplier_inventory}, "
                f"Shopify={shopify['inventory']})"
            )

    return changes

# --------------------------------------------------
# Main program
# --------------------------------------------------

def main():

    print("Authenticating with Shopify...")

    access_token = get_access_token()

    print("Authentication successful.")

    print("Finding Shopify inventory location...")

    location = get_shopify_location(
        access_token
    )

    print(
        f"Shopify inventory location: "
        f"{location['name']}"
    )

    print("Loading Shopify products...")

    shopify_products = get_shopify_products(
        access_token,
        location["id"]
    )

    print(
        f"Loaded {len(shopify_products)} Shopify products."
    )

    print("Loading supplier products from GitHub...")

    supplier_products = load_supplier_products()

    print(
        f"Loaded {len(supplier_products)} supplier products."
    )

    print(
        f"Shopify inventory location: "
        f"{location['name']}"
    )

    changes = compare_products(
        supplier_products,
        shopify_products
    )

    print()
    print("=" * 60)
    print("INVENTORY CHANGES DETECTED")
    print("=" * 60)

    for change in changes:

        print(
            f"{change['sku']}: "
            f"{change['current_inventory']} "
            f"→ "
            f"{change['new_inventory']}"
        )

    print()
    print(
        f"Total inventory changes: "
        f"{len(changes)}"
    )

    # --------------------------------------------------
    # Update products
    # --------------------------------------------------

    if not changes:

        print()
        print("No inventory changes required.")
        return

    for change in changes:

        print()
        print(f"Updating {change['sku']}...")

        result = update_inventory(
            access_token,
            change["inventory_item_id"],
            location["id"],
            change["current_inventory"],
            change["new_inventory"]
        )

        print("Inventory update successful.")
   
    


# --------------------------------------------------
# Start program
# --------------------------------------------------

if __name__ == "__main__":
    main()