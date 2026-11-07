
from pathlib import Path

import duckdb
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_connection():
    config = load_config()

    database_path = PROJECT_ROOT / config["database"]["path"]
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return duckdb.connect(str(database_path))


def initialize_database():
    connection = get_connection()

    result = connection.execute(
        "SELECT current_database()"
    ).fetchone()

    print("DuckDB connection successful!")
    print("Database:", result[0])

    connection.close()

def create_tables():
    schema_path = PROJECT_ROOT / "docs" / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    connection = get_connection()

    try:
        connection.execute(schema_sql)
        print("Database tables created successfully!")
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    create_tables()

