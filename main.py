"""Compatibility launcher for the FastAPI app now stored in src/."""

import os

from src.main import *  # noqa: F401,F403
from src.main import DEFAULT_PORT, app, logger


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", DEFAULT_PORT))
    logger.info("Open the tutor at http://localhost:%s", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
