from handlers.admin import router as admin_router
from handlers.garage import router as garage_router
from handlers.menu import router as menu_router
from handlers.profile import router as profile_router
from handlers.race import router as race_router
from handlers.shop import router as shop_router

# admin первым — чтобы FSM-ввод админа обрабатывался раньше остальных
all_routers = [admin_router, menu_router, garage_router, shop_router, race_router, profile_router]

