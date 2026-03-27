import sqlite3
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

client = OpenAI()

query = input("🔎 Γράψε τι ψάχνεις: ")

# Δημιουργία embedding για το query
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=query
)

query_embedding = np.array(response.data[0].embedding)

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("""
SELECT factory_code, description, category, subcategory, embedding
FROM products
WHERE embedding IS NOT NULL
""")

products = cursor.fetchall()
conn.close()

results = []

query_lower = query.lower()

for product in products:

    factory_code, description, category, subcategory, embedding_blob = product
    desc_lower = description.lower()

    # ===== BUSINESS FILTER =====

    # Αν ψάχνει αναλογική
    if "αναλογ" in query_lower:
        if not any(word in desc_lower for word in ["αναλογ", "tvi", "ahd", "cvi"]):
            continue

    # Αν ψάχνει IP
    if "ip" in query_lower:
        if not any(word in desc_lower for word in ["ip", "network"]):
            continue

    # ===== SEMANTIC SIMILARITY =====

    product_embedding = np.frombuffer(embedding_blob, dtype=np.float64)

    similarity = cosine_similarity(
        [query_embedding],
        [product_embedding]
    )[0][0]

    results.append((similarity, factory_code, description, category, subcategory))


results.sort(reverse=True, key=lambda x: x[0])

print("\n📦 Καλύτερα αποτελέσματα:\n")

for r in results[:10]:
    print(f"Score: {r[0]:.3f}")
    print(f"Κωδ.Εργοστασίου: {r[1]}")
    print(f"Περιγραφή: {r[2]}")
    print(f"Κατηγορία: {r[3]} / {r[4]}")
    print("-" * 50)