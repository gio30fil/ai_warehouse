from app import create_app

app = create_app()

print("🚀 Flask app created")

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=True)