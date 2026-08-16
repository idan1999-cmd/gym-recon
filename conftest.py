"""
Root conftest for gym-recon pytest.

The legacy test files (test_idan_fixes.py, test_resilience.py, test_acceptance.py)
use a custom `check()` harness that calls `sys.exit()` at module import time,
which is incompatible with pytest collection. They are excluded here so
`python -m pytest tests/` runs the NEW pytest suites only.

The legacy harness is NOT deleted — it still runs standalone:
    python tests/test_idan_fixes.py   (etc.)
"""
collect_ignore = [
    "tests/test_idan_fixes.py",
    "tests/test_resilience.py",
    "tests/test_acceptance.py",
]