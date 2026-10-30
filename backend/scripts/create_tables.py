"""Run from backend: python -m scripts.create_tables. Not run by the authoring agent."""
from pathlib import Path
import psycopg
from app.config import settings


def main():
    migrations = sorted((Path(__file__).resolve().parents[1] / "sql").glob("*.sql"))
    # Each migration has its own BEGIN/COMMIT and never modifies VYUHAM application tables.
    with psycopg.connect(settings().postgres_url, autocommit=True, connect_timeout=15) as conn:
        for migration in migrations:
            conn.execute(migration.read_text(encoding="utf-8"), prepare=False)
            print("Applied:", migration.name)
    print("Prompt War schema and direct-text submissions are ready. No Storage bucket is needed.")


if __name__ == "__main__":
    main()

