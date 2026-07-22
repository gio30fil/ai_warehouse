import numpy as np
import logging
import re
import threading
from sklearn.metrics.pairwise import cosine_similarity
from app.database import get_connection
from app.services.ai_service import understand_and_check_query, get_embedding, ai_product_advisor

logger = logging.getLogger(__name__)

# Known brands
BRANDS = [
    "inim", "dahua", "hikvision", "ajax", "paradox", "uniview", "tiandy", "ezviz",
    "detnov", "tyco", "american dynamics", "fireclass", "risco", "dsc", "boss",
    "samsung", "sensormatic", "honeywell", "c-tec", "toshiba", "western digital",
    "wisenet", "panoramic", "illustra", "arecont vision", "simtronics",
    "eff eff", "soyal", "cometa", "mobiak",
]

# ─── In-Memory Embedding Cache ─────────────────────────────────────────
# Holds all product embeddings in a single numpy matrix for vectorized search.
# Refreshed periodically or after sync.

_cache_lock = threading.Lock()
_embedding_cache = {
    "loaded": False,
    "matrix": None,       # np.ndarray shape (N, dim)
    "product_ids": [],    # parallel list of product IDs
    "product_data": [],   # parallel list of product dicts
}


def _load_embedding_cache():
    """Load all product embeddings into memory as a numpy matrix."""
    global _embedding_cache

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, kodikos, factory_code, description, category, subcategory, stock, available_stock, embedding
        FROM products
        WHERE embedding IS NOT NULL
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        with _cache_lock:
            _embedding_cache = {
                "loaded": True,
                "matrix": None,
                "product_ids": [],
                "product_data": [],
            }
        return

    embeddings = []
    product_ids = []
    product_data = []

    for row in rows:
        emb = np.frombuffer(row["embedding"], dtype=np.float64)
        embeddings.append(emb)
        product_ids.append(row["id"])
        product_data.append({
            "kodikos": row["kodikos"],
            "factory_code": row["factory_code"],
            "description": row["description"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "stock": row["stock"],
            "available_stock": row["available_stock"],
        })

    matrix = np.vstack(embeddings)

    with _cache_lock:
        _embedding_cache = {
            "loaded": True,
            "matrix": matrix,
            "product_ids": product_ids,
            "product_data": product_data,
        }

    logger.info(f"Embedding cache loaded: {len(product_ids)} products, matrix shape {matrix.shape}")


def invalidate_cache():
    """Call after product sync to force cache reload."""
    global _embedding_cache
    with _cache_lock:
        _embedding_cache["loaded"] = False
    logger.info("Embedding cache invalidated.")


def _ensure_cache():
    """Ensure embeddings are loaded into memory."""
    if not _embedding_cache["loaded"]:
        _load_embedding_cache()


def normalize_query(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _lookup_by_code(query: str, category: str = "all") -> list:
    """
    Direct database lookup by SoftOne product code (kodikos), factory code (factory_code),
    or product model name in description.
    Prioritizes products with available stock (available_stock >= 1.0 or stock >= 1.0)
    so exact matching in-stock products appear FIRST.
    """
    conn = get_connection()
    cursor = conn.cursor()

    q_clean = normalize_query(query)
    if not q_clean:
        conn.close()
        return []

    # 1. Try exact match first on either kodikos or factory_code (case-insensitive)
    if category != "all":
        cursor.execute("""
            SELECT kodikos, factory_code, description, category, subcategory, stock, available_stock
            FROM products
            WHERE (LOWER(kodikos) = ? OR LOWER(factory_code) = ?) AND category = ?
        """, (q_clean, q_clean, category))
    else:
        cursor.execute("""
            SELECT kodikos, factory_code, description, category, subcategory, stock, available_stock
            FROM products
            WHERE LOWER(kodikos) = ? OR LOWER(factory_code) = ?
        """, (q_clean, q_clean))

    rows = cursor.fetchall()

    if rows:
        results = []
        for row in rows:
            eff_stock = float(row["available_stock"]) if row["available_stock"] is not None else (float(row["stock"]) if row["stock"] is not None else 0.0)
            has_stock = 1 if eff_stock >= 1.0 else 0
            results.append({
                "score": 3.0 + (1.0 if has_stock else 0.0),
                "kodikos": row["kodikos"],
                "factory_code": row["factory_code"],
                "description": row["description"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "stock": row["stock"],
                "available_stock": row["available_stock"],
                "_has_stock": has_stock,
            })
        conn.close()
        # Direct exact code matches: in-stock items first
        results.sort(key=lambda x: x["_has_stock"], reverse=True)
        for r in results:
            r.pop("_has_stock", None)
        return results

    # 2. Check for product model name or code in description, factory_code, or kodikos
    # ONLY return products with available stock >= 1.0 when searching by description/model
    like_pattern = f"%{q_clean}%"
    code_prefix = f"{q_clean}%"

    if category != "all":
        cursor.execute("""
            SELECT kodikos, factory_code, description, category, subcategory, stock, available_stock
            FROM products
            WHERE ((LOWER(kodikos) LIKE ? OR LOWER(factory_code) LIKE ? OR LOWER(description) LIKE ?)
               OR (LOWER(kodikos) LIKE ? OR LOWER(factory_code) LIKE ?))
              AND category = ?
              AND (available_stock >= 1.0 OR (available_stock IS NULL AND stock >= 1.0))
            LIMIT 50
        """, (like_pattern, like_pattern, like_pattern, code_prefix, code_prefix, category))
    else:
        cursor.execute("""
            SELECT kodikos, factory_code, description, category, subcategory, stock, available_stock
            FROM products
            WHERE ((LOWER(kodikos) LIKE ? OR LOWER(factory_code) LIKE ? OR LOWER(description) LIKE ?)
               OR (LOWER(kodikos) LIKE ? OR LOWER(factory_code) LIKE ?))
              AND (available_stock >= 1.0 OR (available_stock IS NULL AND stock >= 1.0))
            LIMIT 50
        """, (like_pattern, like_pattern, like_pattern, code_prefix, code_prefix))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    regex_exact_word = re.compile(r'\b' + re.escape(q_clean) + r'\b', re.IGNORECASE)

    results = []
    for row in rows:
        desc = row["description"] or ""
        fcode = row["factory_code"] or ""
        kod = row["kodikos"] or ""

        eff_stock = float(row["available_stock"]) if row["available_stock"] is not None else (float(row["stock"]) if row["stock"] is not None else 0.0)
        # Strict stock rule: description/model search ONLY returns products with available stock >= 1.0
        if eff_stock < 1.0:
            continue

        is_exact_word = bool(regex_exact_word.search(desc) or regex_exact_word.search(fcode) or regex_exact_word.search(kod))

        score = 2.0 if is_exact_word else 1.0

        results.append({
            "score": score,
            "kodikos": row["kodikos"],
            "factory_code": row["factory_code"],
            "description": row["description"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "stock": row["stock"],
            "available_stock": row["available_stock"],
            "_is_exact_word": is_exact_word,
        })

    # Sort results: exact model word match first, then score
    results.sort(key=lambda x: (x["_is_exact_word"], x["score"]), reverse=True)

    for r in results:
        r.pop("_is_exact_word", None)

    return results[:10]


def search_products(query: str, category: str = "all") -> dict:
    """
    Optimized product search:
    0. Direct code/model lookup (fast-path for SoftOne, Factory codes, or product model names)
    1. Single AI call: checks relevance + translates query
    2. Cached query embeddings
    3. Vectorized cosine similarity (batch numpy operation)
    4. AI advisor returned separately (non-blocking)
    """
    query_lower = normalize_query(query)

    # ── Step 0: Direct code/model lookup ──
    direct_results = _lookup_by_code(query_lower.strip(), category)
    if direct_results:
        logger.info(f"Direct code/model match for '{query}' → {len(direct_results)} result(s)")
        return {"products": direct_results, "advisor": None}

    # ── Step 1: AI combined check + translation (single API call) ──
    ai_result = understand_and_check_query(query_lower)

    if not ai_result["related"]:
        logger.info(f"Query '{query}' not product-related → returning empty")
        return {"products": [], "advisor": None, "not_related": True}

    translated_query = ai_result["translated"]
    logger.info(f"AI translated: '{query}' → '{translated_query}'")

    query_words = translated_query.split()
    raw_query_words = query_lower.split()
    all_query_words = list(set(query_words + raw_query_words))

    # ── Step 2: Brand detection ──
    brand_query = None
    for brand in BRANDS:
        if brand in translated_query:
            brand_query = brand
            break

    # ── Step 3: Get query embedding (with cache) ──
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT embedding FROM query_cache WHERE query = ?",
        (translated_query,),
    )
    cached = cursor.fetchone()

    if cached:
        logger.debug("Query embedding from cache")
        query_embedding = np.frombuffer(cached["embedding"], dtype=np.float64)
    else:
        logger.debug("Generating new query embedding")
        query_embedding = get_embedding(translated_query)
        if query_embedding is None:
            conn.close()
            raise Exception("Αποτυχία σύνδεσης με OpenAI API")

        cursor.execute(
            "INSERT OR IGNORE INTO query_cache (query, embedding) VALUES (?, ?)",
            (translated_query, query_embedding.tobytes()),
        )
        conn.commit()

    conn.close()

    # ── Step 4: Vectorized cosine similarity ──
    _ensure_cache()

    with _cache_lock:
        matrix = _embedding_cache["matrix"]
        product_data = _embedding_cache["product_data"]

    if matrix is None or len(product_data) == 0:
        return {"products": [], "advisor": None}

    # Single batch operation — O(1) numpy call instead of O(n) Python loop
    similarities = cosine_similarity([query_embedding], matrix)[0]

    # ── Step 5: Scoring & filtering ──
    results = []

    for i, sim in enumerate(similarities):
        prod = product_data[i]
        desc_lower = prod["description"].lower() if prod["description"] else ""
        fcode_lower = prod["factory_code"].lower() if prod["factory_code"] else ""
        kod_lower = prod["kodikos"].lower() if prod["kodikos"] else ""
        stock = prod["stock"]
        available_stock = prod["available_stock"]

        # Category filter
        if category != "all" and prod["category"] != category:
            continue

        # Stock filter
        eff_stock = float(available_stock) if available_stock is not None else (float(stock) if stock is not None else 0)
        has_stock = 1 if eff_stock >= 1.0 else 0
        if eff_stock < 1.0:
            continue

        # Business rules
        if "αναλογ" in translated_query:
            if not any(w in desc_lower for w in ["αναλογ", "tvi", "ahd", "cvi"]):
                continue

        if "ip" in query_words:
            if not any(w in desc_lower for w in ["ip", "network"]):
                continue

        keyword_match = any(word in desc_lower or word in fcode_lower or word in kod_lower for word in all_query_words)

        if sim < 0.35 and not keyword_match:
            continue

        # Scoring
        keyword_score = 0.0
        for word in all_query_words:
            if word in desc_lower or word in fcode_lower or word in kod_lower:
                regex_w = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                if regex_w.search(desc_lower) or regex_w.search(fcode_lower) or regex_w.search(kod_lower):
                    keyword_score += 0.40  # Exact word match boost
                else:
                    keyword_score += 0.10  # Substring match

        brand_boost = 0.20 if (brand_query and brand_query in desc_lower) else 0
        stock_boost = 0.30 if has_stock else 0.0
        final_score = float(sim) + keyword_score + brand_boost + stock_boost

        results.append({
            "score": final_score,
            "kodikos": prod["kodikos"],
            "factory_code": prod["factory_code"],
            "description": prod["description"],
            "category": prod["category"],
            "subcategory": prod["subcategory"],
            "stock": stock,
            "available_stock": available_stock,
            "_has_stock": has_stock,
        })

    # Sort results: items with stock first, then highest score
    results.sort(reverse=True, key=lambda x: (x["_has_stock"], x["score"]))

    for r in results:
        r.pop("_has_stock", None)

    if not results:
        return {"products": [], "advisor": None}

    top_results = results[:10]

    return {
        "products": top_results,
        "advisor": None,  # Advisor loaded via separate AJAX call
    }


def get_advisor_for_products(query: str, products: list) -> str | None:
    """Separate call for AI advisor — loaded asynchronously via AJAX."""
    return ai_product_advisor(query, products)
