import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _load_dotenv() -> None:
    """Tiny .env loader so we don't need python-dotenv."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'civicpulse.db'}")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-me")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

APNS_TEAM_ID = os.environ.get("APNS_TEAM_ID", "")
APNS_KEY_ID = os.environ.get("APNS_KEY_ID", "")
APNS_KEY_PATH = os.environ.get("APNS_KEY_PATH", str(BASE_DIR / "AuthKey.p8"))
APNS_TOPIC = os.environ.get("APNS_TOPIC", "org.techoversight.civicpulse")
APNS_ENV = os.environ.get("APNS_ENV", "sandbox")

# Public datasets used for member-of-Congress lookup.
LEGISLATORS_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
ZCCD_URL = "https://raw.githubusercontent.com/OpenSourceActivismTech/us-zipcodes-congress/master/zccd.csv"
