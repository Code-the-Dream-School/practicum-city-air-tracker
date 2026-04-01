from __future__ import annotations

import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SRC = PIPELINE_ROOT / "src"

for path in (PIPELINE_SRC, PIPELINE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
