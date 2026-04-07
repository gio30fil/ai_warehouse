import sqlite3
import pandas as pd

# Διαβάζουμε CSV
df = pd.read_csv("products.csv", sep=";", encoding="utf-8")
df.columns = df.columns.str.strip()

print("Στήλες:", df.columns.tolist())

# Δημιουργούμε καθαρή βάση
conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS products")

cursor.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kodikos TEXT,
    factory_code TEXT,
    description TEXT,
    category TEXT,
    subcategory TEXT,
    stock REAL,
    embedding BLOB
)
""")

# Εισαγωγή προϊόντων
for _, row in df.iterrows():

    stock_value = row.get("Ποσ.1.7") or 0

    try:
        stock = float(str(stock_value).replace(",", "."))
    except:
        stock = 0

    cursor.execute("""
        INSERT INTO products (
            kodikos,
            factory_code,
            description,
            category,
            subcategory,
            stock,
            embedding
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL)
    """, (
        str(row.get("Κωδικός", "")),
        str(row.get("Κωδ.εργοστασίου", "")),
        str(row.get("Περιγραφή", "")),
        str(row.get("Ομάδα", "")),
        str(row.get("Υποομάδα", "")),
        stock
    ))

conn.commit()
conn.close()

print("✔ Εισαγωγή ολοκληρώθηκε!")