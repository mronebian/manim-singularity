"""可切换的主题全局单例。

Switchable theme singleton.

颜色只从数据库加载，不内置任何 seed/fallback。
使用 chroma init 创建数据库后，手动添加颜色并绑定角色。
参考: chroma add / chroma create-theme / chroma set-role
"""
from typing import Optional

from ._db import ColorDB
from ._theme_names import ThemeName


class _NeonTheme:
    """颜色缓存单例，驱动 color.X 语法。

    Color cache singleton that powers the color.X syntax.

    默认加载 "Neon" 主题，可通过 use(name) 切换到其他主题。
    数据库无指定主题时 _cache 保持空，
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

    def __init__(self, name: str = "Neon") -> None:
        self._db: Optional[ColorDB] = None
        self._name: str = name
        self._cache: dict[str, str] = {}
        self._load()

    @property
    def theme_name(self) -> str:
        """返回当前加载的主题名称。"""
        return self._name

    def _load(self) -> None:
        """连接数据库并加载当前主题到缓存。

        Connect to the database and cache the current theme.
        """
        try:
            self._db = ColorDB()
            theme_data = self._db.get_theme(self._name)
            if theme_data:
                for role_lower, record in theme_data.items():
                    self._cache[role_lower.upper() + "_COLOR"] = record.hex_code
        except Exception:
            self._db = None

    def use(self, name: ThemeName) -> None:
        """切换到指定主题，清空缓存并重新加载。

        Switch to a different theme, clearing cache and reloading.

        Args:
            name: 数据库中的主题名称。
        """
        self._cache.clear()
        self._name = name
        self._load()

    def reload(self) -> None:
        """清空缓存并重新从数据库加载当前主题。

        Clear the cache and reload the current theme from the database.
        """
        self._cache.clear()
        self._load()

    def __getattr__(self, role: str) -> str:
        if role in self._cache:
            return self._cache[role]
        raise AttributeError(
            f"'NeonTheme' has no color role '{role}' — "
            f"make sure '{self._name}' theme exists in DB with all required roles.\n"
            f"Available: {', '.join(sorted(self._cache)) if self._cache else '(empty)'}"
        )

    def title_gradient(self) -> tuple[str, str]:
        """返回标题渐变色二元组 (TITLE_COLOR, TITLE_GRADIENT_END_COLOR)。

        Return the title gradient color pair.
        """
        return (self.TITLE_COLOR, self.TITLE_GRADIENT_END_COLOR)


theme = _NeonTheme()
