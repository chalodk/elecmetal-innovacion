"""Run migrations via Supabase Management API, splitting by statement."""
import os
import re
import requests

SUPABASE_ACCESS_TOKEN = "REDACTED_TOKEN"
PROJECT_REF = "REDACTED_PROJECT_REF"
API_URL = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"

HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def run_sql(sql: str, description: str = ""):
    """Execute SQL via Management API. Returns result or None on failure."""
    label = f" {description}" if description else ""
    print(f"Executing{label} ({len(sql)} chars)...", end=" ", flush=True)
    resp = requests.post(API_URL, headers=HEADERS, json={"query": sql})
    if resp.status_code in (200, 201):
        print("OK")
        return resp.json()
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:400]}")
        return None


def extract_up_sql(sql: str) -> str:
    """Extract just the Up section SQL, removing goose markers."""
    match = re.search(
        r'-- \+goose Up.*?-- \+goose StatementBegin\n(.*?)\n-- \+goose StatementEnd',
        sql, re.DOTALL
    )
    if not match:
        raise ValueError("Could not find Up section")
    return match.group(1)


def split_sql(body: str) -> list[str]:
    """Split SQL body into individual statements.
    Handles $$...$$ blocks (function bodies) and avoids splitting inside them.
    """
    statements = []
    current = []
    in_dollar = False
    dollar_tag = None

    i = 0
    while i < len(body):
        ch = body[i]

        if not in_dollar and ch == '$':
            # Check if this starts a dollar-quoted string
            # Match $$ or $tag$
            m = re.match(r'\$[a-zA-Z_]*\$', body[i:])
            if m:
                dollar_tag = m.group()
                current.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar = True
                continue

        if in_dollar and dollar_tag:
            # Look for end tag
            end = body.find(dollar_tag, i)
            if end >= 0:
                current.append(body[i:end + len(dollar_tag)])
                i = end + len(dollar_tag)
                in_dollar = False
                dollar_tag = None
                continue

        if ch == ';' and not in_dollar:
            # End of statement
            stmt = ''.join(current).strip()
            # Skip comment-only statements
            if stmt and not all(line.strip().startswith('--') or line.strip() == ''
                               for line in stmt.split('\n')):
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1

    # Remaining
    stmt = ''.join(current).strip()
    if stmt and not all(line.strip().startswith('--') or line.strip() == ''
                       for line in stmt.split('\n')):
        statements.append(stmt)

    return statements


def main():
    migrations_dir = os.path.join(
        os.path.dirname(__file__), "..", "migrations"
    )
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))

    # Cleanup test table
    run_sql("DROP TABLE IF EXISTS test_connection CASCADE;", "cleanup")

    for fname in files:
        path = os.path.join(migrations_dir, fname)
        print(f"\n{'='*60}")
        print(f"File: {fname}")

        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()

        up_sql = extract_up_sql(sql)
        statements = split_sql(up_sql)

        print(f"Found {len(statements)} statements")

        failed = 0
        for i, stmt in enumerate(statements):
            # Get first meaningful line as description
            lines = [line for line in stmt.split('\n')
                     if line.strip() and not line.strip().startswith('--')]
            desc = lines[0][:60] if lines else f"stmt {i+1}"
            result = run_sql(stmt, f"[{i+1}] {desc}")
            if result is None:
                failed += 1
                # If statement failed, we might want to continue or stop
                print(f"  WARNING: statement {i+1} failed (may cascade)")
                # For critical failures, stop
                if "already exists" not in str(result) and i < 5:
                    pass  # continue anyway for CREATE IF NOT EXISTS patterns

        print(f"  {fname}: {len(statements)-failed}/{len(statements)} succeeded, {failed} failed")

    # Verify
    print("\n" + "="*60)
    result = run_sql(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name;",
        "verify"
    )
    if result:
        print("Tables in public schema:")
        for row in result:
            print(f"  - {row['table_name']}")
    else:
        # Retry to see what tables exist
        result2 = run_sql(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name;",
            "retry verify"
        )
        if result2:
            print("Tables in public schema (retry):")
            for row in result2:
                print(f"  - {row['table_name']}")


if __name__ == "__main__":
    main()
