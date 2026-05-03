import pyodbc
import pandas as pd
from pathlib import Path
from .config import CLEAN_OUTPUT, DEDUP_OUTPUT

# Configurations SQL Server
SERVER = r'localhost\SQLEXPRESS'
DATABASE = 'SmartETL_DB'
DRIVER = 'ODBC Driver 17 for SQL Server'

# Tables SQL
TABLE_CLEAN = 'customers_clean'
TABLE_DEDUP = 'customers_dedup'


def create_database():
    """Création de la base de données si elle n'existe pas"""
    try:
        # Connexion à la master database d'abord
        conn_str = f'Driver={DRIVER};Server={SERVER};Database=master;Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        conn.autocommit = True

        # Vérifier l'existence de la base de données
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DATABASE}'")
        if not cursor.fetchone():
            print(f"📁 Création de la base de données: {DATABASE}...")
            cursor.execute(f"CREATE DATABASE {DATABASE}")
            print(f"✅ Base de données créée: {DATABASE}")
        else:
            print(f"✅ La base de données existe déjà: {DATABASE}")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création de la base de données: {e}")
        return False


def load_data_to_db(csv_path, table_name):
    """Chargement des données CSV dans la base de données de manière dynamique"""
    try:
        # Lecture des données avec auto-détection du séparateur
        df = pd.read_csv(csv_path, sep=None, engine='python')

        # Connexion à SQL Server
        conn_str = f'Driver={DRIVER};Server={SERVER};Database={DATABASE};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # 1. Supprimer la table si elle existe pour recréer le bon schéma dynamique
        cursor.execute(f"IF EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}') DROP TABLE {table_name}")

        # 2. Générer le schéma dynamiquement
        columns_sql = []
        for col, dtype in df.dtypes.items():
            if pd.api.types.is_integer_dtype(dtype):
                sql_type = 'INT'
            elif pd.api.types.is_float_dtype(dtype):
                sql_type = 'FLOAT'
            elif pd.api.types.is_bool_dtype(dtype):
                sql_type = 'BIT'
            else:
                sql_type = 'NVARCHAR(MAX)'
            columns_sql.append(f'[{col}] {sql_type}')
        
        schema = ',\n        '.join(columns_sql)
        create_query = f"CREATE TABLE {table_name} (\n        {schema}\n    )"
        cursor.execute(create_query)
        print(f"✅ Table dynamique recréée: {table_name}")

        # 3. Insérer les données
        for index, row in df.iterrows():
            # Remplacer NaN par None
            values = [None if pd.isna(val) else val for val in row]

            # Requête INSERT
            placeholders = ','.join(['?' for _ in values])
            cols = ','.join([f'[{c}]' for c in df.columns])
            query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

            cursor.execute(query, values)

        conn.commit()
        print(f"✅ {len(df)} lignes insérées dans la table {table_name}")
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erreur lors du chargement des données: {e}")
        return False


def verify_data():
    """Vérification des données chargées"""
    try:
        conn_str = f'Driver={DRIVER};Server={SERVER};Database={DATABASE};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Compter les lignes
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_CLEAN}")
        clean_count = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_DEDUP}")
        dedup_count = cursor.fetchone()[0]

        # Check if is_anomaly exists in DEDUP table
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{TABLE_DEDUP}' AND COLUMN_NAME = 'is_anomaly'")
        if cursor.fetchone():
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_DEDUP} WHERE is_anomaly = 1")
            anomaly_count = cursor.fetchone()[0]
        else:
            anomaly_count = "N/A"

        conn.close()

        print("\n" + "="*50)
        print("📊 Vérification des données:")
        print("="*50)
        print(f"📁 Table {TABLE_CLEAN}: {clean_count} lignes")
        print(f"📁 Table {TABLE_DEDUP}: {dedup_count} lignes")
        print(f"⚠️  Anomalies: {anomaly_count}")
        print("="*50)

        return True
    except Exception as e:
        print(f"❌ Erreur de vérification: {e}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "="*50)
    print("🗄️  Chargement des données dans SQL Server")
    print("="*50)

    # Etape 1: Création DB
    print("\n[1/4] Création de la base de données...")
    if not create_database():
        print("❌ Échec de la création de la base de données")
        return

    # Etape 2: Chargement données nettoyées
    print("\n[2/4] Chargement des données nettoyées...")
    if CLEAN_OUTPUT.exists():
        load_data_to_db(CLEAN_OUTPUT, TABLE_CLEAN)
    else:
        print(f"⚠️ Fichier introuvable: {CLEAN_OUTPUT}")

    # Etape 3: Chargement données finales
    print("\n[3/4] Chargement des données finales...")
    if DEDUP_OUTPUT.exists():
        load_data_to_db(DEDUP_OUTPUT, TABLE_DEDUP)
    else:
        print(f"⚠️ Fichier introuvable: {DEDUP_OUTPUT}")

    # Etape 4: Verification
    print("\n[4/4] Vérification des données...")
    verify_data()

    print("\n✅ Toutes les données ont été sauvegardées dans SQL Server avec succès !\n")
    print("🎯 Pour vérifier dans SSMS:")
    print(f"   SELECT * FROM {TABLE_CLEAN}")
    print(f"   SELECT * FROM {TABLE_DEDUP}")
    print(f"   SELECT * FROM {TABLE_DEDUP} WHERE is_anomaly = 1\n")


if __name__ == "__main__":
    main()
