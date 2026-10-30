"""Root conftest — presence of this file puts the repo root on sys.path for `courselib`."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
