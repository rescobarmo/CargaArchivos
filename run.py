import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
