import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import config
import database
import models
import schemas

# Ensure sys.modules has both "models" and "backend.models" pointing to identical module object
sys.modules["backend.config"] = config
sys.modules["backend.database"] = database
sys.modules["backend.models"] = models
sys.modules["backend.schemas"] = schemas
