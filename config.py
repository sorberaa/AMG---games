import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/amg_game.db")
PORT = int(os.getenv("PORT", "10000"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
if 8936384717 not in ADMIN_IDS:
    ADMIN_IDS.append(8936384717)
OWNER_ID = 8936384717

# Скрытый дневной лимит монет (игрокам не показывается)
COINS_SOFT_CAP = 350   # до этого значения — полная награда
COINS_HARD_CAP = 500   # после — почти ничего


