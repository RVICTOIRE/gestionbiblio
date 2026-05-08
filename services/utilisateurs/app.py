import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "bibliotheque"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

USER_TYPES = ("etudiant", "professeur", "personnel")


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def user_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "user_type": row["user_type"],
        "student_id": row["student_id"],
        "phone": row["phone"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "utilisateurs"})


# GET /users — liste tous les utilisateurs
@app.route("/users", methods=["GET"])
def list_users():
    user_type = request.args.get("type")
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_type and user_type in USER_TYPES:
            cur.execute("SELECT * FROM users WHERE user_type = %s ORDER BY name", (user_type,))
        else:
            cur.execute("SELECT * FROM users ORDER BY name")
        users = [user_to_dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /users/<id> — profil utilisateur
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        return jsonify(user_to_dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# POST /users — créer un utilisateur
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    for field in ["name", "email", "user_type"]:
        if not data.get(field):
            return jsonify({"error": f"Champ requis: {field}"}), 400

    if data["user_type"] not in USER_TYPES:
        return jsonify({"error": f"Type invalide. Valeurs: {USER_TYPES}"}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """INSERT INTO users (name, email, user_type, student_id, phone)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (data["name"], data["email"], data["user_type"], data.get("student_id"), data.get("phone")),
        )
        user = user_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return jsonify(user), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Email déjà utilisé"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PUT /users/<id> — modifier un utilisateur
@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        if "user_type" in data and data["user_type"] not in USER_TYPES:
            return jsonify({"error": f"Type invalide. Valeurs: {USER_TYPES}"}), 400

        fields, values = [], []
        for key in ["name", "email", "user_type", "student_id", "phone", "is_active"]:
            if key in data:
                fields.append(f"{key} = %s")
                values.append(data[key])

        if not fields:
            return jsonify({"error": "Aucune donnée à mettre à jour"}), 400

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s RETURNING *", values)
        user = user_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return jsonify(user)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DELETE /users/<id> — désactiver un utilisateur
@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s RETURNING id", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        return jsonify({"message": "Utilisateur désactivé", "id": user_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET /users/<id>/profile — profil complet avec stats
@app.route("/users/<int:user_id>/profile", methods=["GET"])
def get_user_profile(user_id):
    loans_url = os.getenv("LOANS_SERVICE_URL", "http://emprunts:5003")
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        profile = user_to_dict(user)

        import urllib.request, json as _json
        try:
            req = urllib.request.urlopen(f"{loans_url}/loans/user/{user_id}/stats", timeout=3)
            profile["stats"] = _json.loads(req.read())
        except Exception:
            profile["stats"] = None

        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=os.getenv("FLASK_ENV") == "development")
