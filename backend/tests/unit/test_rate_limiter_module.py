"""
Unit tests confirming rate limiter consolidation.

Tests:
- RateLimitMiddleware is importable from middleware.rate_limiter
- make_rate_limiter returns a callable that raises HTTPException(429) at limit
- main.py no longer defines RateLimitMiddleware (duplication removed)
- routes/query.py no longer defines _check_rate_limit (duplication removed)
"""
import ast
import pathlib
import pytest
from fastapi import HTTPException


class TestRateLimiterModule:
    def test_rate_limit_middleware_importable(self):
        from middleware.rate_limiter import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_make_rate_limiter_importable(self):
        from middleware.rate_limiter import make_rate_limiter
        assert callable(make_rate_limiter)

    def test_make_rate_limiter_raises_at_limit(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=3, window=60)
        for _ in range(3):
            check("ip-a")  # should not raise
        with pytest.raises(HTTPException) as exc:
            check("ip-a")
        assert exc.value.status_code == 429

    def test_different_ips_have_independent_limits(self):
        from middleware.rate_limiter import make_rate_limiter
        check = make_rate_limiter(limit=2, window=60)
        for _ in range(2):
            check("ip-x")
        check("ip-y")  # ip-y untouched, must not raise

    def test_main_py_does_not_define_rate_limit_middleware(self):
        """After refactor, main.py must not contain a class named RateLimitMiddleware."""
        main_file = pathlib.Path(__file__).parent.parent.parent / "main.py"
        src = main_file.read_text()
        tree = ast.parse(src)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "RateLimitMiddleware" not in class_names, (
            "RateLimitMiddleware is still defined in main.py — remove it"
        )

    def test_query_py_does_not_define_check_rate_limit(self):
        """After refactor, routes/query.py must not define _check_rate_limit."""
        query_file = pathlib.Path(__file__).parent.parent.parent / "routes" / "query.py"
        src = query_file.read_text()
        tree = ast.parse(src)
        func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "_check_rate_limit" not in func_names, (
            "_check_rate_limit is still defined in routes/query.py — remove it"
        )
