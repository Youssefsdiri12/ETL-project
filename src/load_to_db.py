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

        # Vérifier l'existence de la base de données
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DATABASE}'")
        if not cursor.fetchone():
            print(f"📁 Création de la base de données: {DATABASE}...")
            cursor.execute(f"CREATE DATABASE {DATABASE}")
            conn.commit()
            print(f"✅ Base de données créée: {DATABASE}")
        else:
            print(f"✅ La base de données existe déjà: {DATABASE}")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création de la base de données: {e}")
        return False


def create_tables(conn):
    """Création des tables"""
    cursor = conn.cursor()

    # Table des données nettoyées
    create_clean_table = f"""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{TABLE_CLEAN}')
    CREATE TABLE {TABLE_CLEAN} (
        customer_id INT,
        name NVARCHAR(255),
        email NVARCHAR(255),
        phone NVARCHAR(20),
        city NVARCHAR(100),
        country NVARCHAR(100),
        signup_date DATE,
        amount DECIMAL(10, 2)
    )
    """

    # Table des données dédupliquées avec anomalies
    create_dedup_table = f"""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{TABLE_DEDUP}')
    CREATE TABLE {TABLE_DEDUP} (
        customer_id INT,
        name NVARCHAR(255),
        email NVARCHAR(255),
        phone NVARCHAR(20),
        city NVARCHAR(100),
        country NVARCHAR(100),
        signup_date DATE,
        amount DECIMAL(10, 2),
        is_anomaly INT,
        anomaly_score FLOAT
    )
    """

    try:
        cursor.execute(create_clean_table)
        print(f"✅ Table créée: {TABLE_CLEAN}")

        cursor.execute(create_dedup_table)
        print(f"✅ Table créée: {TABLE_DEDUP}")

        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False


def load_data_to_db(csv_path, table_name):
    """Chargement des données CSV dans la base de données"""
    try:
        # Lecture des données
        df = pd.read_csv(csv_path)

        # Connexion à SQL Server
        conn_str = f'Driver={DRIVER};Server={SERVER};Database={DATABASE};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Vider la table (optionnel)
        cursor.execute(f"TRUNCATE TABLE {table_name}")

        # Insérer les données
        for index, row in df.iterrows():
            # Remplacer NaN par None
            values = [None if pd.isna(val) else val for val in row]

            # Requête INSERT
            placeholders = ','.join(['?' for _ in values])
            columns = ','.join(df.columns)
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

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

        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_DEDUP} WHERE is_anomaly = 1")
        anomaly_count = cursor.fetchone()[0]

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
    print("\n[1/5] Création de la base de données...")
    if not create_database():
        print("❌ Échec de la création de la base de données")
        return

    # Etape 2: Connexion SQL Server
    print("\n[2/5] Connexion à SQL Server...")
    try:
        conn_str = f'Driver={DRIVER};Server={SERVER};Database={DATABASE};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        print(f"✅ Connecté à {SERVER}\\{DATABASE}")
    except Exception as e:
        print(f"❌ Échec de la connexion: {e}")
        return

    # Etape 3: Création des tables
    print("\n[3/5] Création des tables...")
    if not create_tables(conn):
        print("❌ Échec de la création des tables")
        conn.close()
        return

    conn.close()

    # Etape 4: Chargement données nettoyées
    print("\n[4/5] Chargement des données nettoyées...")
    if CLEAN_OUTPUT.exists():
        load_data_to_db(CLEAN_OUTPUT, TABLE_CLEAN)
    else:
        print(f"⚠️ Fichier introuvable: {CLEAN_OUTPUT}")

    # Etape 5: Chargement données finales
    print("\n[5/5] Chargement des données finales...")
    if DEDUP_OUTPUT.exists():
        load_data_to_db(DEDUP_OUTPUT, TABLE_DEDUP)
    else:
        print(f"⚠️ Fichier introuvable: {DEDUP_OUTPUT}")

    # Verification
    print("\n[Vérification] Vérification des données...")
    verify_data()

    print("\n✅ Toutes les données ont été sauvegardées dans SQL Server avec succès !\n")
    print("🎯 Pour vérifier dans SSMS:")
    print(f"   SELECT * FROM {TABLE_CLEAN}")
    print(f"   SELECT * FROM {TABLE_DEDUP}")
    print(f"   SELECT * FROM {TABLE_DEDUP} WHERE is_anomaly = 1\n")


if __name__ == "__main__":
    main()
