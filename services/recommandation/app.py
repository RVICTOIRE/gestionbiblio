import os
import pickle
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Service Recommandation - Bibliothèque DIT",
    description="API de recommandation de livres basée sur l'historique des emprunts",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "bibliotheque"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/model/model.pkl"))
DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data/loans.csv"))

# État global du modèle
model_state = {
    "model": None,
    "user_item_matrix": None,
    "user_ids": None,
    "book_ids": None,
    "book_info": None,
    "is_trained": False,
}


def get_db():
    return psycopg2.connect(**DB_CONFIG)


def load_data_from_db():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT user_id, book_id, loan_date, status FROM loans")
    loans = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT id, title, author, genre FROM books")
    books = pd.DataFrame(cur.fetchall())
    cur.close()
    conn.close()
    return loans, books


def train_model(loans_df: pd.DataFrame, books_df: pd.DataFrame):
    """Entraîne un modèle KNN collaboratif user-item."""
    if loans_df.empty:
        raise ValueError("Pas assez de données pour entraîner le modèle")

    # Matrice user-item : rating implicite (1 = emprunté)
    loans_df = loans_df[["user_id", "book_id"]].drop_duplicates()
    loans_df["rating"] = 1

    user_ids = loans_df["user_id"].unique().tolist()
    book_ids = loans_df["book_id"].unique().tolist()

    user_index = {uid: i for i, uid in enumerate(user_ids)}
    book_index = {bid: i for i, bid in enumerate(book_ids)}

    rows = loans_df["user_id"].map(user_index)
    cols = loans_df["book_id"].map(book_index)
    data = loans_df["rating"].values

    matrix = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(book_ids)))

    # KNN sur les utilisateurs (user-based collaborative filtering)
    n_neighbors = min(5, len(user_ids))
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine", algorithm="brute")
    knn.fit(matrix)

    book_info = books_df.set_index("id").to_dict("index") if not books_df.empty else {}

    return {
        "model": knn,
        "user_item_matrix": matrix,
        "user_ids": user_ids,
        "book_ids": book_ids,
        "user_index": user_index,
        "book_index": book_index,
        "book_info": book_info,
    }


def load_model():
    """Charge le modèle depuis le disque."""
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            state = pickle.load(f)
        model_state.update(state)
        model_state["is_trained"] = True
        logger.info("Modèle chargé depuis %s", MODEL_PATH)
        return True
    return False


def save_model(state: dict):
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(state, f)
    logger.info("Modèle sauvegardé dans %s", MODEL_PATH)


@app.on_event("startup")
async def startup():
    if not load_model():
        logger.info("Aucun modèle trouvé, entraînement initial...")
        try:
            loans_df, books_df = load_data_from_db()
            if not loans_df.empty:
                state = train_model(loans_df, books_df)
                save_model(state)
                model_state.update(state)
                model_state["is_trained"] = True
                logger.info("Modèle entraîné au démarrage")
        except Exception as e:
            logger.warning("Impossible d'entraîner au démarrage: %s", e)


@app.get("/health")
def health():
    return {"status": "ok", "service": "recommandation", "model_trained": model_state["is_trained"]}


class TrainResponse(BaseModel):
    message: str
    n_users: int
    n_books: int
    n_interactions: int


@app.post("/train", response_model=TrainResponse)
async def train(background_tasks: BackgroundTasks):
    """Ré-entraîne le modèle sur l'historique complet des emprunts."""
    try:
        loans_df, books_df = load_data_from_db()
        if loans_df.empty:
            raise HTTPException(status_code=400, detail="Pas de données d'emprunt disponibles")

        state = train_model(loans_df, books_df)
        save_model(state)
        model_state.update(state)
        model_state["is_trained"] = True

        return TrainResponse(
            message="Modèle entraîné avec succès",
            n_users=len(state["user_ids"]),
            n_books=len(state["book_ids"]),
            n_interactions=int(loans_df.shape[0]),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int, n: int = 5):
    """Retourne les N livres recommandés pour un utilisateur."""
    if not model_state["is_trained"]:
        raise HTTPException(status_code=503, detail="Modèle non entraîné. Appelez POST /train d'abord.")

    user_ids = model_state["user_ids"]
    book_ids = model_state["book_ids"]
    matrix = model_state["user_item_matrix"]
    knn = model_state["model"]
    book_info = model_state.get("book_info", {})
    user_index = model_state.get("user_index", {})
    book_index = model_state.get("book_index", {})

    if user_id not in user_index:
        # Utilisateur inconnu : retourne les livres les plus populaires
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """SELECT b.id, b.title, b.author, b.genre, COUNT(l.id) AS borrow_count
                   FROM books b LEFT JOIN loans l ON b.id = l.book_id
                   GROUP BY b.id ORDER BY borrow_count DESC LIMIT %s""",
                (n,),
            )
            popular = cur.fetchall()
            cur.close()
            conn.close()
            return {
                "user_id": user_id,
                "strategy": "popular",
                "recommendations": [dict(r) for r in popular],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    idx = user_index[user_id]
    user_vector = matrix[idx]

    # Livres déjà empruntés par l'utilisateur
    already_borrowed = set(
        book_ids[j] for j in user_vector.indices
    )

    # Voisins les plus proches
    distances, indices = knn.kneighbors(user_vector, n_neighbors=min(6, len(user_ids)))
    neighbor_indices = indices[0][1:]  # Exclut l'utilisateur lui-même

    # Agrège les livres empruntés par les voisins
    scores = {}
    for ni in neighbor_indices:
        neighbor_vector = matrix[ni]
        for j in neighbor_vector.indices:
            bid = book_ids[j]
            if bid not in already_borrowed:
                scores[bid] = scores.get(bid, 0) + 1

    # Trie par score et prend les N meilleurs
    recommended_ids = sorted(scores, key=scores.get, reverse=True)[:n]

    recommendations = []
    for bid in recommended_ids:
        info = book_info.get(bid, {})
        recommendations.append({
            "book_id": bid,
            "title": info.get("title", "Inconnu"),
            "author": info.get("author", "Inconnu"),
            "genre": info.get("genre"),
            "score": scores[bid],
        })

    return {
        "user_id": user_id,
        "strategy": "collaborative_filtering",
        "recommendations": recommendations,
    }


@app.get("/model/info")
def model_info():
    if not model_state["is_trained"]:
        return {"trained": False}
    return {
        "trained": True,
        "n_users": len(model_state["user_ids"]),
        "n_books": len(model_state["book_ids"]),
        "model_path": str(MODEL_PATH),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
