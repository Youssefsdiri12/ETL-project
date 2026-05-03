import sys
import argparse
from .ingest import load_dataset
from .clean_rules import apply_cleaning_rules
from .dedup_ml import load_dedup_model, predict_duplicate_pairs, drop_predicted_duplicates
from .anomaly import load_anomaly_model, predict_anomalies
from .utils import save_json, now_iso
from .config import (
    CLEAN_OUTPUT,
    DEDUP_OUTPUT,
    QUALITY_REPORT_PATH,
    DEDUP_MODEL_PATH,
    ANOMALY_MODEL_PATH
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main(input_path: str):
    print(f"\n🚀 Traitement du fichier: {input_path}\n")
    
    # Etape 1: Chargement des donnees
    print("[1/5] Chargement des données...")
    raw, detected_cols = load_dataset(input_path)

    # Etape 2: Nettoyage des donnees
    print("[2/5] Nettoyage des données...")
    clean_df, clean_report = apply_cleaning_rules(raw, detected_cols)
    clean_df.to_csv(CLEAN_OUTPUT, index=False)
    print(f"  ✅ {len(clean_df)} lignes nettoyées")

    # Etape 3: Detection des doublons
    print("[3/5] Détection des doublons...")
    dedup_report = {"ml_duplicates_found": 0, "dropped_indices": []}
    try:
        dedup_model = load_dedup_model(DEDUP_MODEL_PATH)
        if dedup_model:
            dup_pairs = predict_duplicate_pairs(clean_df, dedup_model, threshold=0.75)
            dedup_df, dropped = drop_predicted_duplicates(clean_df, dup_pairs)
            dedup_report["ml_duplicates_found"] = len(dup_pairs)
            dedup_report["dropped_indices"] = dropped
            print(f"  ✅ {len(dup_pairs)} doublons supprimés")
        else:
            dedup_df = clean_df.copy()
            print("  ⚠️ Modèle de déduplication introuvable")
    except Exception as e:
        dedup_df = clean_df.copy()
        print(f"  ⚠️ Erreur: {str(e)}")

    # Etape 4: Detection d'anomalies
    print("[4/5] Détection d'anomalies...")
    anomaly_report = {"anomalies_found": 0}
    try:
        anomaly_model = load_anomaly_model(ANOMALY_MODEL_PATH)
        if anomaly_model:
            scored_df = predict_anomalies(dedup_df, anomaly_model)
            anomaly_report["anomalies_found"] = int(scored_df["is_anomaly"].sum())
            output_df = scored_df
            print(f"  ✅ {anomaly_report['anomalies_found']} anomalies détectées")
        else:
            output_df = dedup_df
            print("  ⚠️ Modèle d'anomalie introuvable")
    except Exception as e:
        output_df = dedup_df
        print(f"  ⚠️ Erreur: {str(e)}")

    # Etape 5: Sauvegarde des resultats
    print("[5/5] Sauvegarde des résultats...")
    output_df.to_csv(DEDUP_OUTPUT, index=False)

    final_report = {
        "generated_at": now_iso(),
        "input_path": input_path,
        "outputs": {
            "clean_csv": str(CLEAN_OUTPUT),
            "dedup_csv": str(DEDUP_OUTPUT),
        },
        "cleaning": clean_report,
        "deduplication": dedup_report,
        "anomaly": anomaly_report,
        "final_rows": int(len(output_df)),
    }

    save_json(QUALITY_REPORT_PATH, final_report)
    
    print("\n" + "="*50)
    print("✅ Traitement terminé avec succès !")
    print("="*50)
    print(f"📊 Fichier original: {len(raw)} lignes")
    print(f"🧹 Après nettoyage: {len(clean_df)} lignes")
    print(f"🔄 Après déduplication: {len(dedup_df)} lignes")
    print(f"⚠️ Anomalies: {anomaly_report['anomalies_found']}")
    print(f"📈 Résultat final: {len(output_df)} lignes")
    print("="*50)
    print(f"📁 Données nettoyées: {CLEAN_OUTPUT}")
    print(f"📁 Données finales: {DEDUP_OUTPUT}")
    print(f"📁 Rapport: {QUALITY_REPORT_PATH}")
    print("="*50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processeur de données universel - Compatible avec n'importe quel CSV")
    parser.add_argument("--input", required=True, help="Chemin du fichier CSV")
    args = parser.parse_args()
    main(args.input)
