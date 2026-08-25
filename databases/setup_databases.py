# Setting up the databases and installing required packages
import subprocess
import sys

from config import POSTGRES, MONGO_URI, get_postgres_connection, get_mongo_client


def check_mongodb():
    try:
        client = get_mongo_client()
        client.server_info()
        print("MongoDB is running")
        client.close()
        return True
    except Exception as e:
        print(f"MongoDB not available: {e}")
        return False


def check_postgresql():
    try:
        conn = get_postgres_connection(dbname='postgres')
        print("PostgreSQL is running")
        conn.close()
        return True
    except Exception as e:
        print(f"PostgreSQL not available: {e}")
        return False


def create_postgresql_database():
    try:
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = get_postgres_connection(dbname='postgres')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        target_db = POSTGRES['dbname']
        cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {target_db};")
            print(f"Database '{target_db}' created")
        else:
            print(f"Database '{target_db}' already exists")

        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def install_packages():
    packages = ['pandas', 'numpy', 'pymongo', 'psycopg2-binary',
                'matplotlib', 'seaborn', 'plotly', 'dash']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])


if __name__ == "__main__":
    print("Setting up databases...")

    install_packages()

    mongo_ok = check_mongodb()
    postgres_ok = check_postgresql()

    if postgres_ok:
        create_postgresql_database()

    if mongo_ok and postgres_ok:
        print("Setup complete. Ready to run scripts.")
    else:
        print("Setup incomplete. Check database connections and your .env file.")
