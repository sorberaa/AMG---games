import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/amg_game.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

PORT = int(os.getenv("PORT", "10000"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "8936384717").split(",") if x.strip().isdigit()]
SUPER_ADMINS = [8936384717]
for sa in SUPER_ADMINS:
    if sa not in ADMIN_IDS:
        ADMIN_IDS.append(sa)
OWNER_ID = 8936384717

# Дневная экономика монет (цель: 2000-3000 монет в неделю, плавный прогресс 300-450 монет в день)
COINS_SOFT_CAP = 320    # Зона стабильного полного прогресса
COINS_HARD_CAP = 450    # Финальная плавная зона
COINS_MAX_DAY = 480     # Абсолютный дневной лимит защиты от автоботов



