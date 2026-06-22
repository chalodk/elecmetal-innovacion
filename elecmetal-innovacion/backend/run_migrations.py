"""Run migrations against Supabase database."""
import asyncio
import asyncpg
import os
import re

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def extract_up_section(sql: str) -> str:
    """Extract the Up section from a goose migration file."""
    # Find "-- +goose Up" and extract until "-- +goose Down"
    match = re.search(r'-- \+goose Up.*?-- \+goose StatementBegin\n(.*?)\n-- \+goose StatementEnd',
                      sql, re.DOTALL)
    if not match:
        raise ValueError("Could not find Up section in migration")
    return match.group(1).strip()


async def main():
    migrations_dir = os.path.join(
        os.path.dirname(__file__), "..", "migrations"
    )
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))

    conn = await asyncpg.connect(DATABASE_URL, ssl="require", statement_cache_size=0)

    try:
        for fname in files:
            path = os.path.join(migrations_dir, fname)
            print(f"Reading {fname}...")
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()

            up_sql = extract_up_section(sql)
            print(f"Executing {fname} ({len(up_sql)} chars)...")
            await conn.execute(up_sql)
            print(f"  {fname} OK")

        print("\nAll migrations applied successfully!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
