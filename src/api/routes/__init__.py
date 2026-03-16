from src.api.routes.character import router as character_router
from src.api.routes.game import router as game_router
from src.api.routes.llm import router as llm_router
from src.api.routes.lore import router as lore_router

__all__ = [
    "character_router",
    "game_router",
    "llm_router",
    "lore_router",
]
