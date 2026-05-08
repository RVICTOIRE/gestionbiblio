import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "bibliotheque"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "isbn": row["isbn"],
        "genre": row["genre"],
        "published_year": row["published_year"],
        "description": row["description"],
        "total_copies": row["total_copies"],
        "available_copies": row["available_copies"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "livres"})


# GET /books — liste tous les livres
@app.route("/books", methods=["GET"])
def list_books():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM books ORDER BY title")
        books = [book_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(books)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /books/<id> — détail d'un livre
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Livre non trouvé"}), 404
        return jsonify(book_to_dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# POST /books — ajouter un livre
@app.route("/books", methods=["POST"])
def add_book():
    data = request.get_json()
    required = ["title", "author", "isbn"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Champ requis: {field}"}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """INSERT INTO books (title, author, isbn, genre, published_year, description, total_copies, available_copies)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (
                data["title"],
                data["author"],
                data["isbn"],
                data.get("genre"),
                data.get("published_year"),
                data.get("description"),
                data.get("total_copies", 1),
                data.get("total_copies", 1),
            ),
        )
        book = book_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return jsonify(book), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "ISBN déjà existant"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PUT /books/<id> — modifier un livre
@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json()
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
        if not cur.fetchone():
            return jsonify({"error": "Livre non trouvé"}), 404

        fields = []
        values = []
        for key in ["title", "author", "isbn", "genre", "published_year", "description", "total_copies", "available_copies"]:
            if key in data:
                fields.append(f"{key} = %s")
                values.append(data[key])

        if not fields:
            return jsonify({"error": "Aucune donnée à mettre à jour"}), 400

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(book_id)

        cur.execute(
            f"UPDATE books SET {', '.join(fields)} WHERE id = %s RETURNING *",
            values,
        )
        book = book_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return jsonify(book)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DELETE /books/<id> — supprimer un livre
@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM books WHERE id = %s RETURNING id", (book_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Livre non trouvé"}), 404
        return jsonify({"message": "Livre supprimé", "id": book_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /books/search?q=&type= — recherche par titre, auteur ou ISBN
@app.route("/books/search", methods=["GET"])
def search_books():
    q = request.args.get("q", "").strip()
    search_type = request.args.get("type", "all")

    if not q:
        return jsonify({"error": "Paramètre de recherche manquant"}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if search_type == "title":
            cur.execute("SELECT * FROM books WHERE LOWER(title) LIKE %s ORDER BY title", (f"%{q.lower()}%",))
        elif search_type == "author":
            cur.execute("SELECT * FROM books WHERE LOWER(author) LIKE %s ORDER BY title", (f"%{q.lower()}%",))
        elif search_type == "isbn":
            cur.execute("SELECT * FROM books WHERE isbn = %s", (q,))
        else:
            cur.execute(
                "SELECT * FROM books WHERE LOWER(title) LIKE %s OR LOWER(author) LIKE %s OR isbn = %s ORDER BY title",
                (f"%{q.lower()}%", f"%{q.lower()}%", q),
            )

        books = [book_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(books)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PATCH /books/<id>/availability — mis à jour de la disponibilité (appelé par service emprunts)
@app.route("/books/<int:book_id>/availability", methods=["PATCH"])
def update_availability(book_id):
    data = request.get_json()
    delta = data.get("delta", 0)  # -1 pour emprunter, +1 pour retourner

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """UPDATE books
               SET available_copies = available_copies + %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s AND available_copies + %s >= 0 AND available_copies + %s <= total_copies
               RETURNING *""",
            (delta, book_id, delta, delta),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Mise à jour impossible (exemplaire indisponible ou livre introuvable)"}), 400
        return jsonify(book_to_dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=os.getenv("FLASK_ENV") == "development")
