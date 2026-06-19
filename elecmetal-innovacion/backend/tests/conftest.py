"""Pytest configuration for backend tests.

Only used for pure unit tests (parser). DB-dependent tests use standalone scripts.
"""
import os

# Skip integration tests in pytest — use standalone scripts instead
os.environ.setdefault("SKIP_INTEGRATION", "1")
