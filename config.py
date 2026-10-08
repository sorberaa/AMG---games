import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/amg_game.db")
PORT = int(os.getenv("PORT", "10000"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Скрытый дневной лимит монет (игрокам не показывается)
COINS_SOFT_CAP = 350   # до этого значения — полная награда
COINS_HARD_CAP = 500   # после — почти ничего

