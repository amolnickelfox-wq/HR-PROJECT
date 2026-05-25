from pathlib import Path
from dotenv import load_dotenv

# Always load from project root .env (two levels up from backend/app/)
_ROOT = Path(__file__).parents[2]
load_dotenv(_ROOT / ".env", override=True)
