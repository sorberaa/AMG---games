import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/amg_game.db")
PORT = int(os.getenv("PORT", "10000"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
SUPER_ADMINS = [8653358704, 8936384717]
for sa in SUPER_ADMINS:
    if sa not in ADMIN_IDS:
        ADMIN_IDS.append(sa)
OWNER_ID = 8653358704

# Скрытый дневной лимит монет (игрокам не показывается)
COINS_SOFT_CAP = 180   # до этого значения — полная награда в день
COINS_HARD_CAP = 250   # после — срабатывает антиабуз лимит


