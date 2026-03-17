import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

import uvicorn
from src.api.main import app
from src.core.config import load_config

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="info",
    )
