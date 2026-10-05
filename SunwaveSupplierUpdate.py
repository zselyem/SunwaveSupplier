import csv
import random
from datetime import datetime
from zoneinfo import ZoneInfo

# Timezone settings
SUPPLIER_TIMEZONE = "Europe/Budapest"
CUSTOMER_TIMEZONE = "America/New_York"

STOCK_CHANGE = 15
PRICE_CHANGE_PERCENT = 10

CSV_FILE = "SunwaveProducts.csv"
LOG_FILE = "SunwaveUpdateLogs.txt"


# 1. Load the CSV
with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    products = list(reader)


# 2. Edit stock and prices
for product in products:

    # Stock
    current_stock = int(product["Inventory quantity"])

    stock_change = random.randint(
        -STOCK_CHANGE,
        STOCK_CHANGE
    )

    new_stock = max(0, current_stock + stock_change)

    product["Inventory quantity"] = str(new_stock)


    # Price
    current_price = float(product["Price"])

    price_change = random.uniform(
        -PRICE_CHANGE_PERCENT / 100,
        PRICE_CHANGE_PERCENT / 100
    )

    new_price = current_price * (1 + price_change)

    new_price = int(new_price) + 0.99

    product["Price"] = f"{new_price:.2f}"


# 3. Save the modified CSV
with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=products[0].keys()
    )

    writer.writeheader()
    writer.writerows(products)

# 4. Formatting the timezones for both the customer and supplier

supplier_time = datetime.now(
    ZoneInfo(SUPPLIER_TIMEZONE)
)

customer_time = supplier_time.astimezone(
    ZoneInfo(CUSTOMER_TIMEZONE)
)

supplier_time_formatted = supplier_time.strftime(
    "%Y-%m-%d %H:%M:%S %Z"
)

customer_time_formatted = customer_time.strftime(
    "%Y-%m-%d %H:%M:%S %Z"
)

# 5. Save the current state to the log

with open(LOG_FILE, "a", encoding="utf-8") as log_file:

log_file.write("=" * 50 + "\n")
log_file.write(f"Supplier time: {supplier_time}\n")
log_file.write(f"Customer time: {customer_time}\n")
log_file.write("=" * 50 + "\n\n")

    for product in products:

        log_file.write(
            f"{product['Title']}\n"
            f"Stock: {product['Inventory quantity']}\n"
            f"Price: {product['Price']}\n\n"
        )


print(f"Updated {len(products)} products.")
print(f"Updated file: {CSV_FILE}")
print(f"Log saved to: {LOG_FILE}")
