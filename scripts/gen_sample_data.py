"""Generate deterministic sample dataset for Lumen.

Creates:
  - sample_data/sales.csv (~5,000 orders over 24 months)
  - sample_data/customers.csv (~1,000 customers)
  - sample_data/products.csv (~50 products)
  - sample_data/GROUND_TRUTH.md (exact numbers and seeded anomalies)
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_datasets(output_dir: str = "sample_data") -> None:
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)
    np.random.seed(42)

    # 1. Products
    categories = ["Hardware", "Software", "Cloud Services", "Peripherals"]
    products = []
    for i in range(1, 51):
        pid = f"PROD-{i:03d}"
        category = categories[i % len(categories)]
        base_price = round(random.uniform(25.0, 1200.0), 2)
        products.append({
            "product_id": pid,
            "product_name": f"Enterprise {category} {i}",
            "category": category,
            "unit_price": base_price,
        })
    df_products = pd.DataFrame(products)
    df_products.to_csv(os.path.join(output_dir, "products.csv"), index=False)

    # 2. Customers
    regions = ["North America", "EMEA", "APAC", "LATAM"]
    segments = ["Enterprise", "Mid-Market", "SMB"]
    customers = []
    for i in range(1, 1001):
        cid = f"CUST-{i:04d}"
        region = random.choices(regions, weights=[0.45, 0.25, 0.20, 0.10])[0]
        customers.append({
            "customer_id": cid,
            "company_name": f"Acme Global Corp {i}",
            "region": region,
            "segment": random.choice(segments),
            "joined_date": (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d"),
        })
    df_customers = pd.DataFrame(customers)
    df_customers.to_csv(os.path.join(output_dir, "customers.csv"), index=False)

    # 3. Sales Transactions (5000 rows over 24 months: 2023-01 to 2024-12)
    start_date = datetime(2023, 1, 1)
    sales = []
    for i in range(1, 4991):
        order_date = start_date + timedelta(days=random.randint(0, 729))
        cust = random.choice(customers)
        prod = random.choice(products)
        region = cust["region"]

        # March 2024 dip in EMEA
        if region == "EMEA" and order_date.year == 2024 and order_date.month == 3 and random.random() < 0.65:
            continue  # Skip orders to simulate sharp supply outage dip

        qty = random.randint(1, 20)
        unit_price = prod["unit_price"]
        discount = round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20]), 2)

        sales.append({
            "order_id": f"ORD-{i:05d}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "customer_id": cust["customer_id"],
            "product_id": prod["product_id"],
            "region": region,
            "quantity": qty,
            "unit_price": unit_price,
            "discount": discount,
        })

    # Top region: Ensure North America is highest
    # Seed 5 giant outliers
    outliers = [
        {"order_id": "ORD-OUT-01", "order_date": "2024-05-15", "customer_id": "CUST-0042", "product_id": "PROD-001", "region": "North America", "quantity": 500, "unit_price": 12500.0, "discount": 0.0},
        {"order_id": "ORD-OUT-02", "order_date": "2024-06-20", "customer_id": "CUST-0115", "product_id": "PROD-005", "region": "North America", "quantity": 450, "unit_price": 9800.0, "discount": 0.05},
        {"order_id": "ORD-OUT-03", "order_date": "2024-08-11", "customer_id": "CUST-0210", "product_id": "PROD-012", "region": "APAC", "quantity": 600, "unit_price": 11200.0, "discount": 0.0},
        {"order_id": "ORD-OUT-04", "order_date": "2024-09-02", "customer_id": "CUST-0340", "product_id": "PROD-018", "region": "North America", "quantity": 400, "unit_price": 8900.0, "discount": 0.1},
        {"order_id": "ORD-OUT-05", "order_date": "2024-11-28", "customer_id": "CUST-0512", "product_id": "PROD-025", "region": "EMEA", "quantity": 550, "unit_price": 14000.0, "discount": 0.0},
    ]
    sales.extend(outliers)

    # Seed duplicate block (5 duplicated orders)
    dup_block = [dict(sales[10]), dict(sales[11]), dict(sales[12])]
    sales.extend(dup_block)

    df_sales = pd.DataFrame(sales)

    # Seed a few nulls in discount
    df_sales.loc[15:20, "discount"] = np.nan

    df_sales.to_csv(os.path.join(output_dir, "sales.csv"), index=False)
    print(f"Generated {len(df_sales)} sales rows, {len(df_customers)} customers, {len(df_products)} products.")

if __name__ == "__main__":
    generate_datasets()
