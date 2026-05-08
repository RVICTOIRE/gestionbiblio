import os
import csv
import io
import psycopg2
import psycopg2.extras
import urllib.request
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from datetime import date, timedelta

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "bibliotheque"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

BOOKS_SERVICE_URL = os.getenv("BOOKS_SERVICE_URL", "http://livres:5001")
LOAN_DURATION_DAYS = 14


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def loan_to_dict(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "book_id": row["book_id"],
        "loan_date": row["loan_date"].isoformat() if row["loan_date"] else None,
        "due_date": row["due_date"].isoformat() if row["due_date"] else None,
        "return_date": row["return_date"].isoformat() if row["return_date"] else None,
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def call_books_service(path, method="GET", data=None):
    url = f"{BOOKS_SERVICE_URL}{path}"
    if data:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method=method)
        req.add_header("Content-Type", "application/json")
    else:
        req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        return body, e.code


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "emprunts"})


# GET /loans — liste tous les emprunts
@app.route("/loans", methods=["GET"])
def list_loans():
    status = request.args.get("status")
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Met à jour les emprunts en retard
        cur.execute(
            "UPDATE loans SET status = 'en_retard' WHERE status = 'actif' AND due_date < CURRENT_DATE"
        )

        if status:
            cur.execute("SELECT * FROM loans WHERE status = %s ORDER BY loan_date DESC", (status,))
        else:
            cur.execute("SELECT * FROM loans ORDER BY loan_date DESC")

        loans = [loan_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(loans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /loans/<id> — détail d'un emprunt
@app.route("/loans/<int:loan_id>", methods=["GET"])
def get_loan(loan_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM loans WHERE id = %s", (loan_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Emprunt non trouvé"}), 404
        return jsonify(loan_to_dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# POST /loans — emprunter un livre
@app.route("/loans", methods=["POST"])
def create_loan():
    data = request.get_json()
    for field in ["user_id", "book_id"]:
        if not data.get(field):
            return jsonify({"error": f"Champ requis: {field}"}), 400

    user_id = data["user_id"]
    book_id = data["book_id"]

    try:
        # Vérifie disponibilité via service Livres
        book, status = call_books_service(f"/books/{book_id}")
        if status == 404:
            return jsonify({"error": "Livre non trouvé"}), 404
        if book.get("available_copies", 0) <= 0:
            return jsonify({"error": "Aucun exemplaire disponible"}), 400

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Vérifie que l'utilisateur n'a pas déjà ce livre en emprunt
        cur.execute(
            "SELECT id FROM loans WHERE user_id = %s AND book_id = %s AND status = 'actif'",
            (user_id, book_id),
        )
        if cur.fetchone():
            return jsonify({"error": "Livre déjà emprunté par cet utilisateur"}), 409

        loan_date = date.today()
        due_date = loan_date + timedelta(days=LOAN_DURATION_DAYS)

        cur.execute(
            """INSERT INTO loans (user_id, book_id, loan_date, due_date, status)
               VALUES (%s, %s, %s, %s, 'actif') RETURNING *""",
            (user_id, book_id, loan_date, due_date),
        )
        loan = loan_to_dict(cur.fetchone())
        cur.close()
        conn.close()

        # Met à jour la disponibilité du livre
        call_books_service(f"/books/{book_id}/availability", method="PATCH", data={"delta": -1})

        return jsonify(loan), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PUT /loans/<id>/return — retourner un livre
@app.route("/loans/<int:loan_id>/return", methods=["PUT"])
def return_loan(loan_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM loans WHERE id = %s", (loan_id,))
        loan = cur.fetchone()

        if not loan:
            return jsonify({"error": "Emprunt non trouvé"}), 404
        if loan["status"] == "retourne":
            return jsonify({"error": "Livre déjà retourné"}), 400

        cur.execute(
            """UPDATE loans SET status = 'retourne', return_date = CURRENT_DATE, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s RETURNING *""",
            (loan_id,),
        )
        updated = loan_to_dict(cur.fetchone())
        cur.close()
        conn.close()

        # Libère l'exemplaire
        call_books_service(f"/books/{loan['book_id']}/availability", method="PATCH", data={"delta": 1})

        return jsonify(updated)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /loans/user/<user_id> — historique d'un utilisateur
@app.route("/loans/user/<int:user_id>", methods=["GET"])
def user_loans(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM loans WHERE user_id = %s ORDER BY loan_date DESC", (user_id,))
        loans = [loan_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(loans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /loans/user/<user_id>/stats — statistiques d'un utilisateur
@app.route("/loans/user/<int:user_id>/stats", methods=["GET"])
def user_stats(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE status = 'actif') AS actifs,
               COUNT(*) FILTER (WHERE status = 'retourne') AS retournes,
               COUNT(*) FILTER (WHERE status = 'en_retard') AS en_retard
               FROM loans WHERE user_id = %s""",
            (user_id,),
        )
        stats = dict(cur.fetchone())
        cur.close()
        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /loans/overdue — emprunts en retard
@app.route("/loans/overdue", methods=["GET"])
def overdue_loans():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """UPDATE loans SET status = 'en_retard'
               WHERE status = 'actif' AND due_date < CURRENT_DATE"""
        )
        cur.execute(
            "SELECT * FROM loans WHERE status = 'en_retard' ORDER BY due_date"
        )
        loans = [loan_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(loans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /loans/export — export CSV pour le ML
@app.route("/loans/export", methods=["GET"])
def export_loans():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT user_id, book_id, loan_date, due_date, return_date, status
               FROM loans ORDER BY user_id, loan_date"""
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "book_id", "loan_date", "due_date", "return_date", "status"])
        for r in rows:
            writer.writerow([
                r["user_id"], r["book_id"],
                r["loan_date"], r["due_date"], r["return_date"], r["status"]
            ])

        # Sauvegarde aussi sur disque pour DVC
        data_path = "/app/data/loans.csv"
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        with open(data_path, "w", newline="") as f:
            f.write(output.getvalue())

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=loans.csv"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=os.getenv("FLASK_ENV") == "development")
