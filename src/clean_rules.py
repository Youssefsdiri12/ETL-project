import pandas as pd
import numpy as np
from .utils import normalize_text, normalize_phone, is_valid_email, parse_date_safe

def apply_cleaning_rules(df: pd.DataFrame, detected_cols=None) -> tuple:
    report = {
        "rows_before": int(len(df)),
        "exact_duplicates_removed": 0,
        "invalid_emails": 0,
        "invalid_dates": 0,
        "rows_after": 0,
    }

    # 1. Normaliser les noms de colonnes (minuscules, sans espaces)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # 2. Nettoyage générique des colonnes de texte
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].apply(lambda x: normalize_text(x) if isinstance(x, str) else x)

    # 3. Détection automatique et nettoyage des colonnes spécifiques
    for col in df.columns:
        # Si c'est un email
        if 'email' in col or 'mail' in col:
            invalid_email_mask = ~df[col].apply(lambda x: is_valid_email(x) if pd.notna(x) else True)
            report["invalid_emails"] += int(invalid_email_mask.sum())
            df.loc[invalid_email_mask, col] = None
        
        # Si c'est un téléphone
        elif 'phone' in col or 'tel' in col:
            df[col] = df[col].apply(lambda x: normalize_phone(x) if pd.notna(x) else x)
        
        # Si c'est une date
        elif 'date' in col:
            parsed_dates = df[col].apply(parse_date_safe)
            invalid_date_mask = parsed_dates.isna() & df[col].notna()
            report["invalid_dates"] += int(invalid_date_mask.sum())
            df[col] = parsed_dates

    # 4. Convertir les colonnes qui ressemblent à des nombres
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                # Tenter de convertir en numérique si possible (ex: prix en texte)
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass

    # 5. Supprimer les lignes complètement vides
    df = df.dropna(how="all")

    # 6. Supprimer les doublons exacts
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    report["exact_duplicates_removed"] = int(before - after)

    report["rows_after"] = int(len(df))
    return df.reset_index(drop=True), report
