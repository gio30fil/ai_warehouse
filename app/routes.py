from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, jsonify
from .services import search_products, sync_softone_products, sync_softone_stock
from create_pdf import create_offer_pdf
from .database import get_connection

main = Blueprint("main", __name__)


# SYNC FROM SOFTONE (PRODUCTS)
@main.route("/sync", methods=["POST"])
def sync():

    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Access denied"}), 403

    try:
        new_count = sync_softone_products()
        return jsonify({
            "success": True, 
            "message": f"Sync completed! Added {new_count} new products and updated others."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# FETCH STOCK FROM SOFTONE
@main.route("/api/fetch_stock", methods=["POST"])
def fetch_stock_api():

    if "user" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        count = sync_softone_stock()
        return jsonify({
            "success": True, 
            "message": f"Stock updated for {count} products!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# GET ALL PRODUCTS FOR TABLE
@main.route("/api/products")
def get_products():

    if "user" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT kodikos, description, stock FROM products ORDER BY description")
    rows = cursor.fetchall()
    conn.close()

    products = []
    for r in rows:
        products.append({
            "code": r[0],
            "description": r[1],
            "stock": r[2]
        })

    return jsonify(products)


# LOGIN
@main.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session.permanent = True
            session["user"] = username
            session["role"] = user[3]

            return redirect(url_for("main.home"))

    return render_template("login.html")


# LOGOUT
@main.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.login"))


# HOME (AI SEARCH PAGE)
@main.route("/", methods=["GET","POST"])
def home():

    if "user" not in session:
        return redirect(url_for("main.login"))

    conn = get_connection()
    cursor = conn.cursor()

    # 🔹 παίρνουμε όλες τις κατηγορίες
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = cursor.fetchall()

    conn.close()

    results = []
    advisor = None
    selected_category = "all"

    if request.method == "POST":

        query = request.form["query"]
        selected_category = request.form.get("category", "all")

        conn = get_connection()
        cursor = conn.cursor()

        # save search log
        cursor.execute(
            "INSERT INTO search_logs (user, query) VALUES (?,?)",
            (session["user"], query)
        )

        conn.commit()
        conn.close()

        data = search_products(query, selected_category)

        results = data["products"]
        advisor = data["advisor"]

    return render_template(
        "index.html",
        results=results,
        advisor=advisor,
        categories=categories,
        selected_category=selected_category
    )


# EXPORT PDF
@main.route("/export_pdf", methods=["POST"])
def export_pdf():

    if "user" not in session:
        return redirect(url_for("main.login"))

    products = request.json

    filename = create_offer_pdf(products)

    return send_file(filename, as_attachment=True)


# ADMIN PANEL
@main.route("/admin")
def admin():

    if "user" not in session:
        return redirect(url_for("main.login"))

    if session.get("role") != "admin":
        return "Access denied"

    conn = get_connection()
    cursor = conn.cursor()

    # USERS
    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()

    # LAST SEARCHES
    cursor.execute("""
    SELECT user, query, created_at
    FROM search_logs
    ORDER BY created_at DESC
    LIMIT 20
    """)
    logs = cursor.fetchall()

    # TOP SEARCHES
    cursor.execute("""
    SELECT query, COUNT(*) as total
    FROM search_logs
    GROUP BY query
    ORDER BY total DESC
    LIMIT 5
    """)
    top_searches = cursor.fetchall()

    # SEARCHES PER USER
    cursor.execute("""
    SELECT user, COUNT(*) as total
    FROM search_logs
    GROUP BY user
    ORDER BY total DESC
    """)
    user_stats = cursor.fetchall()

    # SEARCHES PER DAY
    cursor.execute("""
    SELECT DATE(created_at), COUNT(*)
    FROM search_logs
    GROUP BY DATE(created_at)
    ORDER BY DATE(created_at) DESC
    LIMIT 7
    """)
    daily_stats = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        logs=logs,
        top_searches=top_searches,
        user_stats=user_stats,
        daily_stats=daily_stats
    )


# VIEW USER SEARCH HISTORY
@main.route("/admin/user/<username>")
def user_searches(username):

    if session.get("role") != "admin":
        return "Access denied"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT query, created_at
    FROM search_logs
    WHERE user=?
    ORDER BY created_at DESC
    """,(username,))

    logs = cursor.fetchall()

    conn.close()

    return render_template(
        "user_logs.html",
        logs=logs,
        username=username
    )


# ADD USER
@main.route("/admin/add", methods=["POST"])
def add_user():

    if session.get("role") != "admin":
        return "Access denied"

    username = request.form["username"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (username,password,role) VALUES (?,?,?)",
        (username,password,"sales")
    )

    conn.commit()
    conn.close()

    return redirect(url_for("main.admin"))


# DELETE USER
@main.route("/admin/delete/<int:user_id>")
def delete_user(user_id):

    if session.get("role") != "admin":
        return "Access denied"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("main.admin"))


# EDIT USER
@main.route("/admin/edit/<int:user_id>", methods=["GET","POST"])
def edit_user(user_id):

    if session.get("role") != "admin":
        return "Access denied"

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "UPDATE users SET username=?, password=? WHERE id=?",
            (username, password, user_id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("main.admin"))

    cursor.execute(
        "SELECT id, username, password FROM users WHERE id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    return render_template("edit_user.html", user=user)