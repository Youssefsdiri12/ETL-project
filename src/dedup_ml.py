import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from .features import extract_features

def train_dedup_model(df_clean):
    features_df = extract_features(df_clean)
    if len(features_df) == 0:
        return None
        
    X = features_df[["text_sim", "num_sim", "avg_sim"]].values
    
    # Label généré automatiquement pour l'entraînement :
    # Si la similarité globale est très forte (> 0.85), on le considère comme un doublon.
    # RandomForest va apprendre ces frontières.
    y = (features_df["avg_sim"] > 0.85).astype(int).values
    
    # Si toutes les étiquettes sont pareilles (ex: aucun doublon trouvé), le modèle plantera
    if sum(y) == 0 or sum(y) == len(y):
        return None
        
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

def load_dedup_model(path):
    try:
        return joblib.load(path)
    except Exception:
        return None

def predict_duplicate_pairs(df, model, threshold=0.75):
    features_df = extract_features(df)
    if len(features_df) == 0:
        return []
        
    X = features_df[["text_sim", "num_sim", "avg_sim"]].values
    
    try:
        proba = model.predict_proba(X)
        # Si le modèle n'a qu'une classe, predict_proba retourne une seule colonne
        if proba.shape[1] == 1:
            return []
        proba_dup = proba[:, 1]
    except:
        return []
        
    dup_pairs = features_df[proba_dup >= threshold][["idx_i", "idx_j"]].values.tolist()
    return dup_pairs

def drop_predicted_duplicates(df, dup_pairs):
    if not dup_pairs:
        return df, []
        
    indices_to_drop = set()
    for idx_i, idx_j in dup_pairs:
        indices_to_drop.add(idx_j)
    dropped = list(indices_to_drop)
    
    df_deduped = df.drop(index=dropped).reset_index(drop=True)
    return df_deduped, dropped

def save_dedup_model(model, path):
    if model is not None:
        joblib.dump(model, path)
