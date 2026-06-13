from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ITEMS_PATH = DATA_DIR / "items.json"
LOADOUTS_PATH = DATA_DIR / "loadouts.json"

WIKI_API_URL = "https://icarus.wiki.gg/api.php"
USER_AGENT = "icarus-calculator-poc/0.1 (+https://icarus-calculator.local)"
