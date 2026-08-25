#Shared configuration for all scripts.Reads database credentials from a .env file in the project root,or falls back to environment variables.
import os
from pathlib import Path


def load_env_file(env_path='.env'):
    """Tiny .env loader so we don't need python-dotenv as a dependency."""
    env_file = Path(env_path)
    if not env_file.exists():
        env_file = Path('..') / '.env'
    if not env_file.exists():
        return

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value


# Load .env on import
load_env_file()


# PostgreSQL settings
POSTGRES = {
    'host':     os.getenv('PG_HOST', 'localhost'),
    'port':     os.getenv('PG_PORT', '5432'),
    'user':     os.getenv('PG_USER', 'postgres'),
    'password': os.getenv('PG_PASSWORD', ''),
    'dbname':   os.getenv('PG_DATABASE', 'rent_affordability'),
}

# MongoDB settings
MONGO_URI      = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'rent_affordability')


def get_postgres_connection(dbname=None):
    """Centralised PostgreSQL connection. Pass dbname='postgres' for admin tasks."""
    import psycopg2
    settings = POSTGRES.copy()
    if dbname:
        settings['dbname'] = dbname
    if not settings['password']:
        raise RuntimeError(
            "PostgreSQL password not set. Create a .env file in the project root "
            "with PG_PASSWORD=your_password (see .env.example)."
        )
    return psycopg2.connect(**settings)


def get_mongo_client():
    from pymongo import MongoClient
    return MongoClient(MONGO_URI)
