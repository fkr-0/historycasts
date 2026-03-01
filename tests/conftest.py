"""Pytest configuration.

This repository uses a src/ layout.

We want `pytest` to work without requiring contributors (or CI) to do an
editable install first, so we add the repo's src/ directory to sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
