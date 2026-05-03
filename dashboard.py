import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# Configuration Streamlit
st.set_page_config(
    page_title="SmartETL - ETL & AI Dashboard",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Chemins des rapports ──────────────────────────────────────────────────────
REPORTS_DIR       = Path("reports/quality_reports")
PROFILING_JSON    = REPORTS_DIR / "profiling_report.json"
PROFILING_HTML    = REPORTS_DIR / "profiling_report.html"
BENCHMARK_JSON    = REPORTS_DIR / "benchmark_report.json"
BENCHMARK_HTML    = REPORTS_DIR / "benchmark_report.html"
QUALITY_JSON      = REPORTS_DIR / "quality_report.json"
CLEAN_CSV         = Path("data/processed/customers_clean.csv")
DEDUP_CSV         = Path("data/processed/customers_deduped.csv")
RAW_DIR           = Path("data/raw")

# ── Imports ETL (après set_page_config) ──────────────────────────────────────
@st.cache_resource
def load_etl_modules():
    from src.train    import main as train_main
    from src.pipeline import main as pipeline_main
    from src.profiling import main as profiling_main
    from src.benchmark import main as benchmark_main
    return train_main, pipeline_main, profiling_main, benchmark_main

train_main, pipeline_main, profiling_main, benchmark_main = load_etl_modules()

# ── Titre ─────────────────────────────────────────────────────────────────────
st.markdown("# 🧹 SmartETL — Pipeline ETL + Machine Learning")
st.markdown("*Automatiser le nettoyage et la déduplication de données avec l'IA*")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Navigation")
    page = st.radio(
        "Sélectionner une page:",
        ["📤 Traitement", "📊 Data Profiling", "🔄 Benchmark", "🗄️ SQL Server"]
    )
    st.markdown("---")
    st.markdown("**Fichiers générés**")
    st.markdown(f"{'✅' if CLEAN_CSV.exists() else '❌'} Données nettoyées")
    st.markdown(f"{'✅' if DEDUP_CSV.exists() else '❌'} Données finales")
    st.markdown(f"{'✅' if PROFILING_JSON.exists() else '❌'} Rapport profiling")
    st.markdown(f"{'✅' if BENCHMARK_JSON.exists() else '❌'} Rapport benchmark")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 : TRAITEMENT
# ══════════════════════════════════════════════════════════════════════════════
if page == "📤 Traitement":
    st.markdown("## 📤 Traitement des données")

    col1, col2 = st.columns([2, 1])

    # ── Colonne gauche : upload ───────────────────────────────────────────────
    with col1:
        st.markdown("### 1️⃣ Charger un fichier CSV")
        uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")

        input_path = None
        if uploaded_file:
            input_path = RAW_DIR / uploaded_file.name
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            input_path.write_bytes(uploaded_file.getbuffer())
            st.success(f"✅ Fichier chargé : **{uploaded_file.name}**")

            df = pd.read_csv(input_path, sep=None, engine='python')
            st.markdown("### 📋 Aperçu des données brutes")
            st.dataframe(df.head(10), use_container_width=True)
            st.markdown(f"**Dimensions :** {df.shape[0]} lignes × {df.shape[1]} colonnes")

        # Ou sélectionner un fichier déjà présent
        elif RAW_DIR.exists():
            existing = list(RAW_DIR.glob("*.csv"))
            if existing:
                selected = st.selectbox("…ou utiliser un fichier existant :", existing)
                if selected:
                    input_path = selected
                    df = pd.read_csv(input_path, sep=None, engine='python')
                    st.markdown("### 📋 Aperçu des données")
                    st.dataframe(df.head(10), use_container_width=True)
                    st.markdown(f"**Dimensions :** {df.shape[0]} lignes × {df.shape[1]} colonnes")

    # ── Colonne droite : actions ──────────────────────────────────────────────
    with col2:
        st.markdown("### 🎯 Actions")

        if input_path is None:
            st.info("⬅️ Chargez un fichier CSV pour activer les actions.")
        else:
            # Bouton 1 : Entraîner les modèles
            if st.button("🚀 1. Entraîner les modèles IA", use_container_width=True):
                with st.spinner("⏳ Entraînement en cours…"):
                    import io
                    import contextlib
                    log_stream = io.StringIO()
                    with contextlib.redirect_stdout(log_stream):
                        try:
                            train_main(str(input_path))
                            success = True
                        except Exception as e:
                            success = False
                            error_msg = str(e)
                    
                    with st.expander("📝 Voir les logs d'entraînement", expanded=True):
                        st.code(log_stream.getvalue(), language="text")
                        
                    if success:
                        st.success("✅ Modèles entraînés et sauvegardés !")
                    else:
                        st.error(f"❌ Erreur : {error_msg}")

            st.markdown("---")

            # Bouton 2 : Lancer le pipeline
            if st.button("🔧 2. Lancer le pipeline ETL", use_container_width=True):
                with st.spinner("⏳ Pipeline en cours…"):
                    import io
                    import contextlib
                    log_stream = io.StringIO()
                    with contextlib.redirect_stdout(log_stream):
                        try:
                            print("🔄 Entraînement automatique des modèles pour ce dataset...")
                            train_main(str(input_path))
                            print("🚀 Lancement du pipeline ETL...")
                            pipeline_main(str(input_path))
                            success = True
                        except Exception as e:
                            success = False
                            error_msg = str(e)
                    
                    with st.expander("📝 Voir les logs du pipeline", expanded=True):
                        st.code(log_stream.getvalue(), language="text")
                        
                    if success:
                        st.success("✅ Pipeline ETL terminé !")
                    else:
                        st.error(f"❌ Erreur : {error_msg}")

    # ── Résultats ─────────────────────────────────────────────────────────────
    if DEDUP_CSV.exists():
        st.markdown("---")
        st.markdown("### 📊 Résultats du pipeline")

        df_results = pd.read_csv(DEDUP_CSV)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📄 Lignes finales",    len(df_results))
        m2.metric("🚨 Anomalies",         int(df_results["is_anomaly"].sum()) if "is_anomaly" in df_results.columns else "—")
        m3.metric("📐 Score anomalie moy",f"{df_results['anomaly_score'].mean():.3f}" if "anomaly_score" in df_results.columns else "—")
        m4.metric("📊 Colonnes",          len(df_results.columns))

        # Qualité avant/après depuis quality_report.json
        if QUALITY_JSON.exists():
            with open(QUALITY_JSON, encoding="utf-8") as f:
                qr = json.load(f)
            st.markdown("#### 🔎 Rapport qualité")
            c1, c2, c3 = st.columns(3)
            c1.metric("Lignes originales",  qr.get("cleaning", {}).get("rows_before", "—"))
            c2.metric("Après nettoyage",    qr.get("cleaning", {}).get("rows_after",  "—"))
            c3.metric("Doublons ML",        qr.get("deduplication", {}).get("ml_duplicates_found", 0))

        st.markdown("#### 📋 Tableau des données nettoyées")
        st.dataframe(df_results, use_container_width=True)

        # Téléchargement
        st.download_button(
            "⬇️ Télécharger les données nettoyées (CSV)",
            data=df_results.to_csv(index=False).encode("utf-8"),
            file_name="donnees_nettoyees.csv",
            mime="text/csv"
        )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 : DATA PROFILING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Data Profiling":
    st.markdown("## 📊 Analyse complète des données (Profiling)")

    raw_files = list(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []
    if not raw_files:
        st.warning("⚠️ Aucun fichier CSV dans `data/raw/`. Allez d'abord dans **📤 Traitement** pour uploader un fichier.")
    else:
        input_file = st.selectbox("Choisir un fichier CSV à analyser :", raw_files)

        if st.button("🔍 Lancer l'analyse Profiling", use_container_width=True):
            with st.spinner("⏳ Profiling en cours…"):
                import io
                import contextlib
                log_stream = io.StringIO()
                with contextlib.redirect_stdout(log_stream):
                    try:
                        profiling_main(str(input_file))
                        success = True
                    except Exception as e:
                        success = False
                        error_msg = str(e)
                
                with st.expander("📝 Voir les logs du Profiling", expanded=True):
                    st.code(log_stream.getvalue(), language="text")
                
                if success:
                    st.success("✅ Profiling terminé !")
                else:
                    st.error(f"❌ Erreur profiling : {error_msg}")

        # Afficher le rapport si disponible
        if PROFILING_JSON.exists():
            with open(PROFILING_JSON, encoding="utf-8") as f:
                report = json.load(f)

            st.markdown("---")
            st.markdown("### 📈 Résultats du Profiling")

            # Métriques principales
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📄 Lignes",          report["general"]["total_rows"])
            m2.metric("📊 Colonnes",         report["general"]["total_columns"])
            # missing_values est un dict {col_name: count}
            total_missing = sum(report["missing_values"].values()) if report["missing_values"] else 0
            m3.metric("❓ Valeurs manquantes", total_missing)
            m4.metric("⭐ Score qualité",    f"{report['quality_score']:.0f}/100")

            # Grade coloré
            grade = report["quality_grade"]
            grade_color = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴"}.get(grade, "⚪")
            st.markdown(f"### {grade_color} Grade de qualité : **{grade}**")

            # Doublons
            dup = report["duplicates"]
            st.markdown(f"- **Doublons exacts :** {dup['exact_duplicates']} "
                        f"({dup['exact_duplicates_percentage']}%)")

            # Corrélations
            if report.get("correlations"):
                st.markdown("#### 🔗 Corrélations fortes (> 0.7)")
                corr_data = [{"Paire": k, "Corrélation": round(v, 3)}
                             for k, v in report["correlations"].items()]
                st.dataframe(pd.DataFrame(corr_data), use_container_width=True)

            # Statistiques par colonne
            st.markdown("#### 📋 Statistiques par colonne")
            stats_rows = []
            for col_name, stat in report["statistics"].items():
                row = {
                    "Colonne":     col_name,
                    "Type":        stat["type"],
                    "Non-null":    stat["non_null_count"],
                    "Manquants %": f"{stat['null_percentage']}%",
                    "Uniques":     stat["unique_count"],
                }
                if stat["type"] == "numeric":
                    row.update({
                        "Moyenne": f"{stat.get('mean', 0):.2f}",
                        "Min":     f"{stat.get('min', 0):.2f}",
                        "Max":     f"{stat.get('max', 0):.2f}",
                        "Outliers":stat.get("outliers_count", 0),
                    })
                else:
                    row["Plus fréquent"] = stat.get("most_common", "—")
                stats_rows.append(row)

            st.dataframe(pd.DataFrame(stats_rows), use_container_width=True)

            # Graphique valeurs manquantes
            if report["missing_values"]:
                fig_missing = px.bar(
                    x=list(report["missing_values"].keys()),
                    y=list(report["missing_values"].values()),
                    labels={"x": "Colonne", "y": "Valeurs manquantes"},
                    title="Valeurs manquantes par colonne",
                    color=list(report["missing_values"].values()),
                    color_continuous_scale="reds"
                )
                st.plotly_chart(fig_missing, use_container_width=True)

            # Rapport HTML téléchargeable
            if PROFILING_HTML.exists():
                with open(PROFILING_HTML, encoding="utf-8") as f:
                    html_content = f.read()
                st.markdown("---")
                st.markdown("#### 📄 Rapport HTML interactif")
                st.components.v1.html(html_content, height=600, scrolling=True)
                st.download_button(
                    "⬇️ Télécharger le rapport HTML",
                    data=html_content,
                    file_name="profiling_report.html",
                    mime="text/html"
                )
        else:
            st.info("ℹ️ Cliquez sur **Lancer l'analyse Profiling** pour générer le rapport.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 : BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔄 Benchmark":
    st.markdown("## 🔄 Benchmark : ETL Classique vs ETL avec IA")

    raw_files = list(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []
    if not raw_files:
        st.warning("⚠️ Aucun fichier CSV dans `data/raw/`.")
    else:
        input_file = st.selectbox("Choisir un fichier CSV :", raw_files)

        if st.button("⚡ Lancer le Benchmark complet", use_container_width=True):
            with st.spinner("⏳ Benchmark en cours…"):
                import io
                import contextlib
                log_stream = io.StringIO()
                with contextlib.redirect_stdout(log_stream):
                    try:
                        benchmark_main(str(input_file))
                        success = True
                    except Exception as e:
                        success = False
                        error_msg = str(e)
                        
                with st.expander("📝 Voir les logs du Benchmark", expanded=True):
                    st.code(log_stream.getvalue(), language="text")
                
                if success:
                    st.success("✅ Benchmark terminé !")
                else:
                    st.error(f"❌ Erreur benchmark : {error_msg}")

        if BENCHMARK_JSON.exists():
            with open(BENCHMARK_JSON, encoding="utf-8") as f:
                report = json.load(f)

            st.markdown("---")
            st.markdown("### 🎯 Comparaison des résultats")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🔧 ETL Classique")
                st.metric("⏱️ Temps",             f"{report['etl_classique']['duration']:.3f} s")
                st.metric("📋 Lignes traitées",    report['etl_classique']['rows_processed'])
                st.metric("📋 Lignes finales",      report['etl_classique']['rows_final'])
                st.metric("🔁 Doublons détectés",   report['etl_classique']['duplicates_found'])
                st.metric("⚠️ Anomalies détectées", report['etl_classique']['anomalies_found'])

            with col2:
                st.markdown("#### 🤖 ETL avec IA")
                st.metric("⏱️ Temps",             f"{report['etl_ai']['duration']:.3f} s")
                st.metric("📋 Lignes traitées",    report['etl_ai']['rows_processed'])
                st.metric("📋 Lignes finales",      report['etl_ai']['rows_final'])
                st.metric("🔁 Doublons détectés",   report['etl_ai']['duplicates_found'])
                st.metric("⚠️ Anomalies détectées", report['etl_ai']['anomalies_found'])

            # Graphique temps
            st.markdown("#### 📊 Visualisation comparative")
            fig_time = px.bar(
                x=["ETL Classique", "ETL avec IA"],
                y=[report['etl_classique']['duration'], report['etl_ai']['duration']],
                labels={"x": "Méthode", "y": "Temps (s)"},
                title="Comparaison des temps d'exécution",
                color=["ETL Classique", "ETL avec IA"],
                color_discrete_map={"ETL Classique": "#FF6B6B", "ETL avec IA": "#4ECDC4"}
            )
            st.plotly_chart(fig_time, use_container_width=True)

            # Graphique doublons
            fig_dup = px.bar(
                x=["ETL Classique", "ETL avec IA"],
                y=[report['etl_classique']['duplicates_found'], report['etl_ai']['duplicates_found']],
                labels={"x": "Méthode", "y": "Doublons détectés"},
                title="Doublons détectés par méthode",
                color=["ETL Classique", "ETL avec IA"],
                color_discrete_map={"ETL Classique": "#FF6B6B", "ETL avec IA": "#4ECDC4"}
            )
            st.plotly_chart(fig_dup, use_container_width=True)

            # Verdict
            st.markdown("---")
            st.markdown("### 🏆 Verdict")
            st.success(report["verdict"]["overall_winner"])
            for reason in report["verdict"].get("reasons", []):
                st.markdown(f"- {reason}")
            st.info(f"**Conclusion :** {report['conclusion']}")

            # Télécharger rapport HTML
            if BENCHMARK_HTML.exists():
                with open(BENCHMARK_HTML, encoding="utf-8") as f:
                    html_content = f.read()
                st.download_button(
                    "⬇️ Télécharger le rapport Benchmark HTML",
                    data=html_content,
                    file_name="benchmark_report.html",
                    mime="text/html"
                )
        else:
            st.info("ℹ️ Cliquez sur **Lancer le Benchmark** pour générer le rapport.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 : SQL SERVER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗄️ SQL Server":
    st.markdown("## 🗄️ Export vers SQL Server")

    st.info("""
    **Configuration requise :**
    - SQL Server Express installé localement
    - Serveur : `localhost\\SQLEXPRESS`
    - Base de données : `SmartETL_DB` *(créée automatiquement)*
    """)

    col_status1, col_status2 = st.columns(2)
    col_status1.markdown(f"**Données nettoyées :** {'✅ Disponibles' if CLEAN_CSV.exists() else '❌ Manquantes — lancez le pipeline d abord'}")
    col_status2.markdown(f"**Données finales :** {'✅ Disponibles' if DEDUP_CSV.exists() else '❌ Manquantes — lancez le pipeline d abord'}")

    if not CLEAN_CSV.exists() or not DEDUP_CSV.exists():
        st.warning("⚠️ Lancez d'abord le **Pipeline ETL** dans la page **📤 Traitement**.")
    else:
        if st.button("🚀 Charger les données dans SQL Server", use_container_width=True):
            with st.spinner("⏳ Chargement en cours…"):
                try:
                    from src.load_to_db import main as load_db_main
                    load_db_main()
                    st.success("✅ Données chargées dans SQL Server !")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

        st.markdown("---")
        st.markdown("### 📋 Requêtes SQL utiles")
        queries = {
            "Voir tous les clients":    "SELECT * FROM customers_clean;",
            "Voir les anomalies":       "SELECT * FROM customers_dedup WHERE is_anomaly = 1;",
            "Total de lignes":          "SELECT COUNT(*) AS total FROM customers_dedup;",
            "Clients par pays":         "SELECT country, COUNT(*) AS nb FROM customers_clean GROUP BY country ORDER BY nb DESC;",
        }
        for label, query in queries.items():
            st.markdown(f"**{label}**")
            st.code(query, language="sql")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("🧹 **SmartETL** — Pipeline ETL + Machine Learning &nbsp;|&nbsp; Made with ❤️ by GhassenGmatii")
