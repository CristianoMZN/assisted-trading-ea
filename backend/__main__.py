"""Run the local API using environment-backed settings."""

import uvicorn

from backend.config import log_level, server_host, server_port


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=server_host(), port=server_port(), log_level=log_level())
