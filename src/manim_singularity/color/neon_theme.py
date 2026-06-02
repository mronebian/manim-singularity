"""Neon 主题全局单例。

Global Neon theme singleton.

颜色只从数据库加载，不内置任何 seed/fallback。
使用 chroma init 创建数据库后，手动添加颜色并绑定角色。
参考: chroma add / chroma create-theme / chroma set-role
"""
from typing import Optional

from ._db import ColorDB


class _NeonTheme:
    """颜色缓存单例，驱动 color.X 语法。

    Color cache singleton that powers the color.X syntax.

    数据库无 "Neon" 主题时 _cache 保持空，
    访问任意颜色角色都会抛出 AttributeError。
    """

    # ── 场景 ──
    SCENE_BACKGROUND_COLOR: str
    SCENE_FLASH_COLOR: str

    # ── 网格 ──
    GRID_LINE_COLOR: str
    GRID_AXIS_COLOR: str

    # ── 图形 ──
    PRIMARY_FILL_COLOR: str
    ACCENT_FILL_COLOR: str
    ORBIT_STROKE_COLOR: str
    RING_STROKE_COLOR: str
    ICON_FILL_COLOR: str

    # ── 文字 ──
    TITLE_COLOR: str
    TITLE_GRADIENT_END_COLOR: str
    INFINITY_COLOR: str
    TAGLINE_COLOR: str
    DECORATIVE_LINE_COLOR: str
    BODY_TEXT_COLOR: str
    MUTED_TEXT_COLOR: str

    # ── 语义 ──
    SUCCESS_COLOR: str
    DANGER_COLOR: str
    WARNING_COLOR: str
    INFORMATION_COLOR: str

    # ── 基础 ──
    WHITE_COLOR: str
    BLACK_COLOR: str

    def __init__(self) -> None:
        self._db: Optional[ColorDB] = None
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """连接数据库并加载 "Neon" 主题到缓存。

        Connect to the database and cache the "Neon" theme.

        主题不存在时保持空缓存，不写库、不抛异常。
        """
        try:
            self._db = ColorDB()
            theme_data = self._db.get_theme("Neon")
            if theme_data:
                for role_lower, record in theme_data.items():
                    self._cache[role_lower.upper() + "_COLOR"] = record.hex_code
        except Exception:
            self._db = None

    def reload(self) -> None:
        """清空缓存并重新从数据库加载。

        Clear the cache and reload from the database.
        """
        self._cache.clear()
        self._load()

    def __getattr__(self, role: str) -> str:
        if role in self._cache:
            return self._cache[role]
        raise AttributeError(
            f"'NeonTheme' has no color role '{role}' — "
            f"make sure 'Neon' theme exists in DB with all required roles.\n"
            f"Available: {', '.join(sorted(self._cache)) if self._cache else '(empty)'}"
        )

    def title_gradient(self) -> tuple[str, str]:
        """返回标题渐变色二元组 (TITLE_COLOR, TITLE_GRADIENT_END_COLOR)。

        Return the title gradient color pair.
        """
        return (self.TITLE_COLOR, self.TITLE_GRADIENT_END_COLOR)


theme = _NeonTheme()
