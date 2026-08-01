# src/warehouse/db.py
import psycopg2
from dotenv import load_dotenv
import os

# Charger .env seulement si le fichier existe (pour le développement local)
env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    # En production (GitHub Actions), les variables sont déjà dans l'environnement
    pass

def get_connection():
    """
    Retourne une connexion à la base de données PostgreSQL.
    Utilise les variables d'environnement (GitHub Actions) ou le fichier .env (local).
    """
    host = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "5432")
    
    # Vérification des variables requises
    if not all([host, database, user, password]):
        missing = []
        if not host: missing.append("DB_HOST")
        if not database: missing.append("DB_NAME")
        if not user: missing.append("DB_USER")
        if not password: missing.append("DB_PASSWORD")
        raise ValueError(f"Variables d'environnement manquantes: {', '.join(missing)}")
    
    print(f"🔗 Connexion à {host}:{port}/{database}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            sslmode="require"
        )
        print("✅ Connexion réussie !")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Erreur de connexion: {e}")
        raise
