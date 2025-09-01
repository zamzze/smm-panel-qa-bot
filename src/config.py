from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
api_key: str | None = os.getenv("SMM_API_KEY")
api_url: str = os.getenv("SMM_API_URL", "https://smmkings/api/v2")
timeout: int = int(os.getenv("SMM_TIMEOUT", "30"))
dry_run: bool = os.getenv("DRY_RUN", "0") == "1"


settings = Settings()
