import numpy as np
import time
import re
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from .database import get_connection
from softone.client import fetch_products, fetch_stock

client = OpenAI()

# γνωστά brands
BRANDS = [
"inim","dahua","hikvision","ajax","paradox","uniview","tiandy","ezviz",
"detnov","tyco","american dynamics","fireclass","risco","dsc","boss",
"samsung","sensormatic","honeywell","c-tec","toshiba","western digital",
"wisenet","panoramic","illustra","arecont vision","simtronics",
"eff eff","soyal","cometa","mobiak"
]


def normalize_query(text):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# AI query understanding
def understand_query(query):

    prompt = f"""
Μετέτρεψε την αναζήτηση προϊόντος σε απλές τεχνικές λέξεις.
Κράτησε μόνο σημαντικά keywords για συστήματα ασφαλείας.

Παραδείγματα:
"καμερα εξωτερικη 4mp poe" -> "ip camera 4mp poe outdoor"
"καμερα dome hikvision" -> "hikvision dome camera"
"πυρανιχνευση inim" -> "inim fire alarm"

Query:
{query}
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        new_query = response.choices[0].message.content.strip().lower()

        if len(new_query) > 2:
            return new_query

    except Exception as e:
        print(f"Error in understand_query: {e}")
        pass

    return query


# AI Advisor
def ai_product_advisor(query, products):

    if not products:
        return None

    product_list = "\n".join(
        [f"{p['factory_code']} - {p['description']}" for p in products[:5]]
    )

    prompt = f"""
Είσαι τεχνικός σύμβουλος συστημάτων ασφαλείας.

Ο χρήστης αναζητά:
{query}

Διαθέσιμα προϊόντα:
{product_list}

Δώσε σύντομη συμβουλή ποιο προϊόν είναι πιο κατάλληλο και γιατί.
Απάντησε σε 1-2 προτάσεις.
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error in advisor: {e}")
        return None


def search_products(query, category="all"):

    conn = get_connection()
    cursor = conn.cursor()

    query_lower = normalize_query(query)

    # AI intent understanding
    query_lower = understand_query(query_lower)

    print("AI Query:", query_lower)

    query_words = query_lower.split()

    # brand detection
    brand_query = None
    for brand in BRANDS:
        if brand in query_lower:
            brand_query = brand
            break

    # cache embeddings
    cursor.execute(
        "SELECT embedding FROM query_cache WHERE query = ?",
        (query_lower,)
    )
    cached = cursor.fetchone()

    if cached:

        print("⚡ Query από cache")

        query_embedding = np.frombuffer(cached[0], dtype=np.float64)

    else:

        print("🧠 Δημιουργία νέου embedding")

        for attempt in range(3):

            try:

                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_lower
                )

                query_embedding = np.array(
                    response.data[0].embedding,
                    dtype=np.float64
                )

                break

            except Exception:

                print(f"⚠ Σφάλμα API (προσπάθεια {attempt+1}/3)")
                time.sleep(1)

        else:

            conn.close()
            raise Exception("Αποτυχία σύνδεσης με OpenAI API")

        cursor.execute(
            "INSERT INTO query_cache (query, embedding) VALUES (?, ?)",
            (query_lower, query_embedding.tobytes())
        )

        conn.commit()

    # προϊόντα (με category filter)
    if category != "all":

        cursor.execute("""
        SELECT kodikos, factory_code, description, category, subcategory, stock, embedding
        FROM products
        WHERE embedding IS NOT NULL
        AND category = ?
        """, (category,))

    else:

        cursor.execute("""
        SELECT kodikos, factory_code, description, category, subcategory, stock, embedding
        FROM products
        WHERE embedding IS NOT NULL
        """)

    products = cursor.fetchall()

    conn.close()

    results = []

    for product in products:

        kodikos, factory_code, description, category, subcategory, stock, embedding_blob = product

        desc_lower = description.lower()

        # stock filter
        if not stock or float(stock) <= 0:
            continue

        # business rules
        if "αναλογ" in query_lower:
            if not any(word in desc_lower for word in ["αναλογ", "tvi", "ahd", "cvi"]):
                continue

        if "ip" in query_lower:
            if not any(word in desc_lower for word in ["ip", "network"]):
                continue

        product_embedding = np.frombuffer(embedding_blob, dtype=np.float64)

        similarity = cosine_similarity(
            [query_embedding],
            [product_embedding]
        )[0][0]

        keyword_match = any(word in desc_lower for word in query_words)

        if similarity < 0.35 and not keyword_match:
            continue

        keyword_score = 0

        for word in query_words:
            if word in desc_lower:
                keyword_score += 0.05

        brand_boost = 0

        if brand_query and brand_query in desc_lower:
            brand_boost = 0.20

        final_score = similarity + keyword_score + brand_boost

        results.append({
            "score": final_score,
            "kodikos": kodikos,
            "factory_code": factory_code,
            "description": description,
            "category": category,
            "subcategory": subcategory,
            "stock": stock
        })

    results.sort(reverse=True, key=lambda x: x["score"])

    if not results:
        return {"products": [], "advisor": None}

    top_results = results[:10]

    advisor = ai_product_advisor(query, top_results)

    return {
        "products": top_results,
        "advisor": advisor
    }


def sync_softone_products():
    """
    Fetches products from SoftOne and syncs them with the local database.
    """
    try:
        new_products = fetch_products()
    except Exception as e:
        print(f"Error fetching from SoftOne: {e}")
        return 0

    if not new_products:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    count = 0
    for prod in new_products:
        kodikos = str(prod.get('code', ''))
        factory_code = str(prod.get('name2', '')) 
        if not factory_code or factory_code == 'None':
            factory_code = kodikos
        
        description = str(prod.get('name', ''))
        
        group = prod.get('group')
        category = group.get('name') if group and isinstance(group, dict) else 'Unknown'
        
        subgroup = prod.get('subgroup')
        subcategory = subgroup.get('name') if subgroup and isinstance(subgroup, dict) else 'Unknown'
        
        cursor.execute("SELECT id FROM products WHERE kodikos = ?", (kodikos,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE products 
                SET description = ?, category = ?, subcategory = ?, factory_code = ?
                WHERE kodikos = ?
            """, (description, category, subcategory, factory_code, kodikos))
        else:
            cursor.execute("""
                INSERT INTO products (kodikos, factory_code, description, category, subcategory, stock, embedding)
                VALUES (?, ?, ?, ?, ?, 1.0, NULL)
            """, (kodikos, factory_code, description, category, subcategory))
            count += 1

    conn.commit()

    cursor.execute("SELECT id, factory_code, description, category, subcategory FROM products WHERE embedding IS NULL")
    to_embed = cursor.fetchall()

    if to_embed:
        print(f"Generating embeddings for {len(to_embed)} products...")
        for item in to_embed:
            item_id = item[0]
            text = f"{item[1]} {item[2]} {item[3]} {item[4]}"
            
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                embedding = np.array(response.data[0].embedding, dtype=np.float64)
                cursor.execute(
                    "UPDATE products SET embedding = ? WHERE id = ?",
                    (embedding.tobytes(), item_id)
                )
            except Exception as e:
                print(f"Embedding error for {item_id}: {e}")

    conn.commit()
    conn.close()
    
    return count


def sync_softone_stock(whouse_code=None):
    """
    Fetches stock levels from SoftOne and updates the local database.
    """
    try:
        stock_data = fetch_stock(whouse_code)
    except Exception as e:
        print(f"Error fetching stock from SoftOne: {e}")
        return 0

    if not stock_data:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    updated_count = 0
    for item in stock_data:
        item_code = item.get('item_code')
        stock = item.get('physical_stock', item.get('stock'))
        
        if item_code is not None and stock is not None:
            cursor.execute("SELECT id FROM products WHERE kodikos = ?", (item_code,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE products SET stock = ? WHERE kodikos = ?",
                    (stock, item_code)
                )
                updated_count += 1

    conn.commit()
    conn.close()
    
    return updated_count