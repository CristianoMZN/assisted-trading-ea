"""Local FastAPI service for the assisted trading backend."""

from pathlib import Path

from dotenv import load_dotenv


# Load one project-local configuration file for both the API and Alembic.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
