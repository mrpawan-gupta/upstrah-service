import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    uvicorn.run(
        "upstrah.asgi:app", host="127.0.0.1", port=8001, reload=True, log_level="info"
    )
