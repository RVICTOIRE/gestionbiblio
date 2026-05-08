"""
Étape 2 du pipeline DVC : Entraînement du modèle de recommandation.
Entrée  : data/loans_clean.csv
Sortie  : model/model.pkl
"""

import os
import sys
import pickle
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix

INPUT_PATH = os.path.join("data", "loans_clean.csv")
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
PARAMS_PATH = "params.yaml"


def load_params():
    try:
        import yaml
        with open(PARAMS_PATH) as f:
            return yaml.safe_load(f).get("train", {})
    except Exception:
        return {}


def train(input_path: str, model_path: str) -> dict:
    params = load_params()
    n_neighbors = int(params.get("n_neighbors", 5))
    metric = params.get("metric", "cosine")

    print(f"[train] Lecture de {input_path}...")
    df = pd.read_csv(input_path)
    print(f"[train] {len(df)} interactions chargées.")

    if df.empty:
        print("[train] ERREUR: données vides.", file=sys.stderr)
        sys.exit(1)

    # Construction de la matrice user-item
    user_ids = df["user_id"].unique().tolist()
    book_ids = df["book_id"].unique().tolist()

    user_index = {uid: i for i, uid in enumerate(user_ids)}
    book_index = {bid: i for i, bid in enumerate(book_ids)}

    rows = df["user_id"].map(user_index).values
    cols = df["book_id"].map(book_index).values
    scores = df["score"].values if "score" in df.columns else np.ones(len(df))

    matrix = csr_matrix((scores, (rows, cols)), shape=(len(user_ids), len(book_ids)))

    print(f"[train] Matrice user-item: {matrix.shape[0]} users × {matrix.shape[1]} livres")
    print(f"[train] Densité: {matrix.nnz / (matrix.shape[0] * matrix.shape[1]):.4%}")

    # Entraînement KNN
    k = min(n_neighbors + 1, len(user_ids))
    print(f"[train] Entraînement KNN (k={k}, metric={metric})...")
    knn = NearestNeighbors(n_neighbors=k, metric=metric, algorithm="brute")
    knn.fit(matrix)

    # Sérialisation du modèle et métadonnées
    state = {
        "model": knn,
        "user_item_matrix": matrix,
        "user_ids": user_ids,
        "book_ids": book_ids,
        "user_index": user_index,
        "book_index": book_index,
        "book_info": {},
        "params": {"n_neighbors": k, "metric": metric},
        "stats": {
            "n_users": len(user_ids),
            "n_books": len(book_ids),
            "n_interactions": int(matrix.nnz),
            "density": float(matrix.nnz / (matrix.shape[0] * matrix.shape[1])),
        },
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(state, f)

    print(f"[train] Modèle sauvegardé dans {model_path}")
    return state["stats"]


if __name__ == "__main__":
    if not os.path.exists(INPUT_PATH):
        print(f"[train] Fichier introuvable: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)
    stats = train(INPUT_PATH, MODEL_PATH)
    print(f"[train] Stats: {stats}")
