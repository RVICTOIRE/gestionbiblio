"""
Étape 1 du pipeline DVC : Prétraitement des données d'emprunts.
Entrée  : data/loans.csv
Sortie  : data/loans_clean.csv
"""

import os
import sys
import pandas as pd
import numpy as np

INPUT_PATH = os.path.join("data", "loans.csv")
OUTPUT_PATH = os.path.join("data", "loans_clean.csv")


def preprocess(input_path: str, output_path: str) -> None:
    print(f"[preprocess] Lecture de {input_path}...")
    df = pd.read_csv(input_path)
    print(f"[preprocess] {len(df)} lignes brutes chargées.")

    # 1. Suppression des doublons
    initial_len = len(df)
    df = df.drop_duplicates()
    print(f"[preprocess] {initial_len - len(df)} doublons supprimés.")

    # 2. Vérification des colonnes requises
    required_cols = ["user_id", "book_id"]
    for col in required_cols:
        if col not in df.columns:
            print(f"[preprocess] ERREUR: colonne '{col}' manquante.", file=sys.stderr)
            sys.exit(1)

    # 3. Suppression des lignes avec user_id ou book_id nuls
    before = len(df)
    df = df.dropna(subset=["user_id", "book_id"])
    print(f"[preprocess] {before - len(df)} lignes avec valeurs nulles supprimées.")

    # 4. Conversion des types
    df["user_id"] = df["user_id"].astype(int)
    df["book_id"] = df["book_id"].astype(int)

    # 5. Conversion des dates
    for date_col in ["loan_date", "due_date", "return_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # 6. Calcul du score implicite :
    #    - Livre retourné en avance ou à temps  → score 1.5
    #    - Livre retourné en retard             → score 0.8
    #    - Emprunt actif                        → score 1.0
    def compute_score(row):
        if row.get("status") == "retourne" and pd.notna(row.get("return_date")) and pd.notna(row.get("due_date")):
            if row["return_date"] <= row["due_date"]:
                return 1.5
            else:
                return 0.8
        return 1.0

    df["score"] = df.apply(compute_score, axis=1)

    # 7. Sélection et réordonnancement des colonnes finales
    final_cols = ["user_id", "book_id", "score", "loan_date", "status"]
    available = [c for c in final_cols if c in df.columns]
    df = df[available]

    # 8. Tri
    df = df.sort_values(["user_id", "book_id"])

    # 9. Sauvegarde
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"[preprocess] {len(df)} lignes propres sauvegardées dans {output_path}.")
    print(f"[preprocess] Utilisateurs uniques : {df['user_id'].nunique()}")
    print(f"[preprocess] Livres uniques       : {df['book_id'].nunique()}")
    print(f"[preprocess] Score moyen          : {df['score'].mean():.3f}")


if __name__ == "__main__":
    if not os.path.exists(INPUT_PATH):
        print(f"[preprocess] Fichier introuvable: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)
    preprocess(INPUT_PATH, OUTPUT_PATH)
