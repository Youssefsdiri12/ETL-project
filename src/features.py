import pandas as pd
import numpy as np
from rapidfuzz import fuzz

def compute_similarity(val1, val2, is_text=True):
    if pd.isna(val1) or pd.isna(val2):
        return 0.0
    
    if is_text:
        return fuzz.token_set_ratio(str(val1), str(val2)) / 100.0
    else:
        # Numérique : similarité basée sur la différence relative
        try:
            v1, v2 = float(val1), float(val2)
            if v1 == 0 and v2 == 0: return 1.0
            diff = abs(v1 - v2) / max(abs(v1), abs(v2))
            return max(0.0, 1.0 - diff)
        except:
            return 0.0

def create_pair_features(df):
    pairs = []
    text_cols = df.select_dtypes(include=['object']).columns.tolist()
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Limiter aux 500 premières lignes pour éviter un temps de calcul infini sur les gros datasets
    df_sample = df.head(500)
    
    for i in range(len(df_sample)):
        row_i = df_sample.iloc[i]
        for j in range(i + 1, len(df_sample)):
            row_j = df_sample.iloc[j]
            
            # Similarité textuelle globale
            text_sims = [compute_similarity(row_i[c], row_j[c], is_text=True) for c in text_cols]
            avg_text_sim = sum(text_sims) / len(text_sims) if text_sims else 0.0
            
            # Similarité numérique globale
            num_sims = [compute_similarity(row_i[c], row_j[c], is_text=False) for c in num_cols]
            avg_num_sim = sum(num_sims) / len(num_sims) if num_sims else 0.0
            
            # Si pas de colonnes de l'un ou l'autre type, on moyenne ce qu'on a
            if not text_cols and not num_cols:
                avg_sim = 0.0
            elif not text_cols:
                avg_sim = avg_num_sim
            elif not num_cols:
                avg_sim = avg_text_sim
            else:
                avg_sim = (avg_text_sim + avg_num_sim) / 2.0
            
            pairs.append({
                "idx_i": i,
                "idx_j": j,
                "text_sim": avg_text_sim,
                "num_sim": avg_num_sim,
                "avg_sim": avg_sim,
            })
            
    return pd.DataFrame(pairs) if pairs else pd.DataFrame()

def extract_features(df):
    return create_pair_features(df)
