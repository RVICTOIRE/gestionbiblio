"""
Étape 3 du pipeline DVC : Évaluation du modèle de recommandation.
Entrée  : model/model.pkl, data/loans_clean.csv
Sortie  : metrics.json
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy.sparse import csr_matrix

MODEL_PATH = os.path.join("model", "model.pkl")
DATA_PATH = os.path.join("data", "loans_clean.csv")
METRICS_PATH = "metrics.json"


def evaluate(model_path: str, data_path: str, metrics_path: str) -> dict:
    print(f"[evaluate] Chargement du modèle depuis {model_path}...")
    with open(model_path, "rb") as f:
        state = pickle.load(f)

    knn = state["model"]
    matrix = state["user_item_matrix"]
    user_ids = state["user_ids"]
    book_ids = state["book_ids"]
    user_index = state["user_index"]
    book_index = state["book_index"]

    print(f"[evaluate] Lecture des données depuis {data_path}...")
    df = pd.read_csv(data_path)

    if len(df) < 5:
        print("[evaluate] Pas assez de données pour évaluer.", file=sys.stderr)
        sys.exit(1)

    # Split train/test (80/20)
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
    print(f"[evaluate] Train: {len(train_df)} | Test: {len(test_df)}")

    # Pour chaque interaction de test, prédire le score via les voisins KNN
    y_true = []
    y_pred = []

    for _, row in test_df.iterrows():
        uid = int(row["user_id"])
        bid = int(row["book_id"])
        true_score = float(row.get("score", 1.0))

        if uid not in user_index or bid not in book_index:
            continue

        u_idx = user_index[uid]
        b_idx = book_index[bid]

        user_vec = matrix[u_idx]

        try:
            n_neighbors = min(knn.n_neighbors, len(user_ids))
            distances, indices = knn.kneighbors(user_vec, n_neighbors=n_neighbors)
            neighbor_idxs = indices[0]

            # Score prédit = moyenne pondérée des scores des voisins pour ce livre
            neighbor_scores = []
            neighbor_weights = []
            for ni, dist in zip(neighbor_idxs, distances[0]):
                if ni == u_idx:
                    continue
                neighbor_vec = matrix[ni]
                if b_idx < neighbor_vec.shape[1] and neighbor_vec[0, b_idx] > 0:
                    neighbor_scores.append(neighbor_vec[0, b_idx])
                    weight = 1.0 / (dist + 1e-9)
                    neighbor_weights.append(weight)

            if neighbor_scores:
                total_w = sum(neighbor_weights)
                pred = sum(s * w for s, w in zip(neighbor_scores, neighbor_weights)) / total_w
                y_true.append(true_score)
                y_pred.append(pred)
        except Exception:
            continue

    if len(y_true) < 3:
        # Fallback : évaluation simplifiée avec scores moyens
        y_true = [float(s) for s in test_df["score"].values]
        mean_score = float(train_df["score"].mean())
        y_pred = [mean_score] * len(y_true)
        evaluation_method = "mean_baseline"
    else:
        evaluation_method = "knn_collaborative"

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))

    # Coverage : % de livres pouvant être recommandés
    coverage = float(len(book_ids) / max(len(df["book_id"].unique()), 1))

    metrics = {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "coverage": round(coverage, 4),
        "n_test_samples": len(y_true),
        "n_users": len(user_ids),
        "n_books": len(book_ids),
        "evaluation_method": evaluation_method,
        "model_stats": state.get("stats", {}),
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"[evaluate] RMSE     : {rmse:.4f}")
    print(f"[evaluate] MAE      : {mae:.4f}")
    print(f"[evaluate] Coverage : {coverage:.2%}")
    print(f"[evaluate] Métriques sauvegardées dans {metrics_path}")

    return metrics


if __name__ == "__main__":
    for path in [MODEL_PATH, DATA_PATH]:
        if not os.path.exists(path):
            print(f"[evaluate] Fichier introuvable: {path}", file=sys.stderr)
            sys.exit(1)
    evaluate(MODEL_PATH, DATA_PATH, METRICS_PATH)
