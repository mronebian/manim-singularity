"""
Neon 主题全局单例。

颜色只从数据库加载，不内置任何 seed/fallback。
首次使用前需手动创建 "Neon" 主题并绑定角色，
参考 seed 文件：<项目根>/../chroma_seed.py
"""
from typing import Optional

from ._db import ColorDB


class _NeonTheme:
    """
    全局单例。颜色只从数据库加载。
    数据库无 "Neon" 主题时 _cache 保持空，
    访问任意颜色角色都会抛出 AttributeError。
    """

    BACKGROUND_COLOR: str
    SURFACE_COLOR: str
    GRID_LINE_COLOR: str
    GRID_AXIS_COLOR: str
    PRIMARY_FILL_COLOR: str
    SECONDARY_FILL_COLOR: str
    ACCENT_FILL_COLOR: str
    TITLE_COLOR: str
    TITLE_GRADIENT_END_COLOR: str
    TEXT_COLOR: str
    TEXT_MUTED_COLOR: str
    SUCCESS_COLOR: str
    DANGER_COLOR: str
    WARNING_COLOR: str
    INFORMATION_COLOR: str
    WHITE_COLOR: str
    BLACK_COLOR: str

    def __init__(self):
        self._db: Optional[ColorDB] = None
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """连接数据库 → 取 "Neon" 主题 → 写入缓存。主题不存在时保持空缓存。"""
        try:
            self._db = ColorDB()
            theme_data = self._db.get_theme("Neon")
            if theme_data:
                for role_lower, record in theme_data.items():
                    self._cache[role_lower.upper() + "_COLOR"] = record.hex_code
        except Exception:
            self._db = None

    def reload(self) -> None:
        """清空缓存并重新从数据库加载。"""
        self._cache.clear()
        self._load()

    def __getattr__(self, role: str) -> str:
        if role in self._cache:
            return self._cache[role]
        raise AttributeError(
            f"'NeonTheme' has no color role '{role}' — "
            f"make sure 'Neon' theme exists in DB with all required roles.\n"
            f"Available: {', '.join(sorted(self._cache)) if self._cache else '(empty)'}\n"
            f"See: chroma_seed.py for setup reference."
        )

    def title_gradient(self) -> tuple[str, str]:
        """返回标题渐变色 (TITLE_COLOR, TITLE_GRADIENT_END_COLOR)。"""
        return (self.TITLE_COLOR, self.TITLE_GRADIENT_END_COLOR)

theme = _NeonTheme()
