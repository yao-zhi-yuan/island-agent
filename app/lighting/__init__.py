# lighting 包的对外入口。
# 这里只暴露 store 生命周期函数，让 app.main 能像 chat/memory/task 一样统一初始化和关闭。
from app.lighting.store import (
    close_lighting_store,
    get_lighting_store_status,
    init_lighting_store,
)

# 白名单，外面只能导入这 3 个
__all__ = [
    "close_lighting_store",
    "get_lighting_store_status",
    "init_lighting_store",
]
