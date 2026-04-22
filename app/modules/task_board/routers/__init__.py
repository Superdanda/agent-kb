from app.modules.task_board.routers.task_router import router as task_router
from app.modules.task_board.routers.material_router import router as material_router
from app.modules.task_board.routers.leaderboard_router import router as leaderboard_router
from app.modules.task_board.routers.file_router import router as file_router
from app.modules.task_board.routers.agent_task_router import router as agent_task_router

__all__ = ["task_router", "material_router", "leaderboard_router", "file_router", "agent_task_router"]
