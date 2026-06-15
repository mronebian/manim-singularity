"""ChromaVault — 颜色数据库系统。

ChromaVault — Color database system.
"""
from ._db import ColorDB, ColorRecord
from .neon_theme import theme as _theme

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

theme = _theme


def __getattr__(name: str):
    if name == "Theme":
        from ._baker import Theme
        return Theme
    return getattr(_theme, name)


__all__ = [
    "ColorDB",
    "ColorRecord",
    "Theme",
    "theme",
]
