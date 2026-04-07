import sqlite3
import numpy as np
from openai import OpenAI

client = OpenAI()

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id, factory_code, description, category, subcategory
FROM products
WHERE embedding IS NULL
""")

products = cursor.fetchall()

print(f"Θα δημιουργηθούν embeddings για {len(products)} προϊόντα")

for product in products:
    product_id = product[0]
    text = " ".join([str(x) for x in product[1:] if x])

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    embedding = np.array(response.data[0].embedding, dtype=np.float64)

    cursor.execute(
        "UPDATE products SET embedding = ? WHERE id = ?",
        (embedding.tobytes(), product_id)
    )

    print(f"✔ ID {product_id}")

conn.commit()
conn.close()

print("🔥 Όλα τα embeddings ολοκληρώθηκαν!")