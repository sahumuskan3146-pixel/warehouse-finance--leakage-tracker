import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

# Connect and overwrite database
conn = sqlite3.connect('warehouse_finops.db')
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS fact_vendor_performance;")
cursor.execute("DROP TABLE IF EXISTS fact_inventory_status;")
cursor.execute("DROP TABLE IF EXISTS fact_sales;")
cursor.execute("DROP TABLE IF EXISTS dim_products;")

# 1. Product Dimensions Master (ABC Classes & Baseline Costs)
cursor.execute("""
CREATE TABLE dim_products (
    Product_ID TEXT PRIMARY KEY,
    Product_Name TEXT,
    Category TEXT,
    Cost_Price REAL,
    Handling_Cost REAL,
    Default_Selling_Price REAL,
    Reorder_Level INTEGER
);
""")

# 2. Sales Transactions Log (Spatio-Temporal Data)
cursor.execute("""
CREATE TABLE fact_sales (
    Order_ID TEXT PRIMARY KEY,
    Product_ID TEXT,
    Quantity_Sold INTEGER,
    Selling_Price REAL,
    Sale_Timestamp TEXT,
    Delivery_Sector TEXT,
    FOREIGN KEY(Product_ID) REFERENCES dim_products(Product_ID)
);
""")

# 3. Inventory Stock Snapshot (Theft/Damage Audit Points)
cursor.execute("""
CREATE TABLE fact_inventory_status (
    Product_ID TEXT,
    Stock_On_Hand INTEGER,
    Physical_Count INTEGER,
    Batch_Expiry_Date TEXT,
    Damaged_Units INTEGER,
    FOREIGN KEY(Product_ID) REFERENCES dim_products(Product_ID)
);
""")

# 4. Supply Chain Logistics & Vendor Logs
cursor.execute("""
CREATE TABLE fact_vendor_performance (
    Transaction_ID TEXT PRIMARY KEY,
    Vendor_Name TEXT,
    Product_ID TEXT,
    Order_Date TEXT,
    Actual_Delivery_Date TEXT,
    Damaged_Received INTEGER,
    FOREIGN KEY(Product_ID) REFERENCES dim_products(Product_ID)
);
""")

# Seed Dimension Table
products_data = [
    ('PROD_001', 'Amul Fresh Dahi 200g', 'Category A', 25.0, 2.0, 30.0, 50),
    ('PROD_002', 'Cadbury Silk Chocolate', 'Category B', 80.0, 5.0, 100.0, 20),
    ('PROD_003', 'Fortune Mustard Oil 1L', 'Category C', 130.0, 8.0, 160.0, 15)
]
cursor.executemany("INSERT INTO dim_products VALUES (?, ?, ?, ?, ?, ?, ?);", products_data)

# Generate Dynamic 7-day high-density sales matrix
start_date = datetime(2026, 5, 27, 0, 0, 0)
end_date = datetime(2026, 6, 2, 23, 59, 59)
current_time = start_date
order_counter = 5000
sales_rows = []
sectors = ['Sector-B_Kakadeo', 'Sector-A_SwaroopNagar', 'Barra', 'Kalyanpur']

while current_time <= end_date:
    is_wknd = current_time.weekday() in [4, 5, 6]
    hr = current_time.hour
    
    # Establish Spatio-Temporal Probability Clusters
    if (7 <= hr <= 10) or (18 <= hr <= 21):
        prob = 0.85 if is_wknd else 0.55
    else:
        prob = 0.15 if is_wknd else 0.05
        
    if random.random() < prob:
        order_id = f"ORD_{order_counter}"
        order_counter += 1
        
        if 7 <= hr <= 10:
            p_id = 'PROD_001'
        elif 18 <= hr <= 21:
            p_id = 'PROD_002'
        else:
            p_id = random.choice(['PROD_001', 'PROD_002', 'PROD_003'])
            
        sector = 'Sector-B_Kakadeo' if (p_id in ['PROD_001', 'PROD_002'] and random.random() < 0.65) else random.choice(sectors)
        qty = random.randint(6, 16) if (is_wknd and p_id != 'PROD_003') else random.randint(1, 4)
        sp = 30.0 if p_id == 'PROD_001' else (100.0 if p_id == 'PROD_002' else 160.0)
        
        sales_rows.append((order_id, p_id, qty, sp, current_time.strftime('%Y-%m-%d %H:%M:%S'), sector))
    current_time += timedelta(minutes=12)

cursor.executemany("INSERT INTO fact_sales VALUES (?, ?, ?, ?, ?, ?);", sales_rows)

# Inject controlled anomalies (Theft of 5 units of Silk, Expiry trap for Dahi)
inventory_data = [
    ('PROD_001', 120, 120, '2026-06-04', 0),
    ('PROD_002', 85, 78, '2026-12-15', 2),
    ('PROD_003', 45, 45, '2027-03-20', 0)
]
cursor.executemany("INSERT INTO fact_inventory_status VALUES (?, ?, ?, ?, ?);", inventory_data)

# Inject SLA vendor delays
vendor_data = [
    ('VEND_TXN_01', 'Shyam Logistics', 'PROD_001', '2026-05-25', '2026-05-30', 12),
    ('VEND_TXN_02', 'Balaji Traders', 'PROD_002', '2026-05-28', '2026-05-30', 0),
    ('VEND_TXN_03', 'Kanpur FMCG Dist', 'PROD_003', '2026-05-26', '2026-05-27', 1)
]
cursor.executemany("INSERT INTO fact_vendor_performance VALUES (?, ?, ?, ?, ?, ?);", vendor_data)

conn.commit()

# Single Excel Document Generator Engine
with pd.ExcelWriter('warehouse_finops_master.xlsx') as writer:
    pd.read_sql_query("SELECT * FROM dim_products", conn).to_excel(writer, sheet_name='Product_Catalog', index=False)
    pd.read_sql_query("SELECT * FROM fact_sales", conn).to_excel(writer, sheet_name='Sales_Transactions', index=False)
    pd.read_sql_query("SELECT * FROM fact_inventory_status", conn).to_excel(writer, sheet_name='Inventory_Status', index=False)
    pd.read_sql_query("SELECT * FROM fact_vendor_performance", conn).to_excel(writer, sheet_name='Vendor_Performance', index=False)

conn.close()
print("Success! SQL Engine and master workbook populated flawlessly.")