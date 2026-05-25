"""
chroma_vault — 颜色数据库系统。
ColorDB / ColorRecord 零外部依赖；Theme 需要 manim。
"""
from ._db import ColorDB, ColorRecord
from .neon_theme import theme as _theme

# ── 类型注解（LSP 补全用，运行时由 __getattr__ 返回 _cache） ──
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

# 保留 theme 导出供内部 theme.py 使用（from .color import theme）
theme = _theme


def __getattr__(name):
    if name == "Theme":
        from .theme.engine import Theme
        return Theme
    # 委托给 theme 单例，使 color.PRIMARY_FILL_COLOR 等直接访问生效
    return getattr(_theme, name)


__all__ = [
    "ColorDB",
    "ColorRecord",
    "Theme",
    "theme",
]
