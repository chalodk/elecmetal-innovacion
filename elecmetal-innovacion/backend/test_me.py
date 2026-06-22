"""Reproduce el error 500 de /api/v1/me paso a paso."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 1. Cargar token
token_path = os.path.join(os.path.dirname(__file__), ".test_token")
with open(token_path) as f:
    token = f.read().strip()
print(f"Token: {len(token)} chars")

async def main():
    # 2. Validar JWT
    from app.core.security import decode_supabase_jwt
    try:
        payload = decode_supabase_jwt(token)
        print(f"JWT OK. sub={payload.get('sub')}, email={payload.get('email')}")
    except Exception as e:
        print(f"JWT FAIL: {e}")
        import traceback
        traceback.print_exc()
        return

    user_id = payload.get("sub")
    print(f"user_id={user_id}, is_valid_uuid=OK")

    # 3. Query DB
    from app.core.database import get_pool, create_pool
    await create_pool()

    pool = get_pool()
    print("Pool acquired")

    async with pool.acquire() as conn:
        print("Connection acquired, running query...")
        sql = f"SELECT id, full_name, role, avatar_url, created_at FROM profiles WHERE id = '{user_id}'"
        print(f"SQL: {sql}")
        try:
            row = await conn.fetchrow(sql)
            print(f"Row type: {type(row)}, value: {row}")
        except Exception as e:
            print(f"QUERY FAILED: {e}")
            import traceback
            traceback.print_exc()
            return

    if not row:
        print("No row found -> would return 404")
    else:
        ca = row["created_at"]
        if ca is not None and not isinstance(ca, str):
            ca = ca.isoformat()
        result = {
            "id": row["id"],
            "full_name": row["full_name"],
            "role": row["role"],
            "avatar_url": row["avatar_url"],
            "created_at": ca,
        }
        print(f"SUCCESS: {result}")

asyncio.run(main())
