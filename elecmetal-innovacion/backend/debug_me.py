"""Debug the /me endpoint — test JWT validation + DB query."""
import httpx
import sys
sys.path.insert(0, ".")

# Get a token
resp = httpx.post(
    "https://vvmynowrxnirfkgzxstk.supabase.co/auth/v1/token?grant_type=password",
    headers={
        "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2bXlub3dyeG5pcmZrZ3p4c3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MTA2NzEsImV4cCI6MjA5NzI4NjY3MX0.JlKX1BeedAeGndNnrlbWPgU9sRe7-pjLPcmymF6btYE",
        "Content-Type": "application/json",
    },
    json={"email": "test@elecmetal.cl", "password": "Test2026!"},
)
data = resp.json()
token = data.get("access_token", "")
print(f"Got token: {len(token)} chars")

# Test JWT validation
from app.core.security import decode_supabase_jwt  # noqa: E402
try:
    payload = decode_supabase_jwt(token)
    print(f"JWT decoded OK. sub={payload.get('sub')}, email={payload.get('email')}")
except Exception as e:
    print(f"JWT decode FAILED: {e}")
    import traceback
    traceback.print_exc()
