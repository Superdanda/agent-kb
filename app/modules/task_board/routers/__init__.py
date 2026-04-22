from app.modules.task_board.routers.task_router import router as task_router
from app.modules.task_board.routers.material_router import router as material_router
from app.modules.task_board.routers.leaderboard_router import router as leaderboard_router

__all__ = ["task_router", "material_router", "leaderboard_router"]
