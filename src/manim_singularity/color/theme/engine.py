"""主题烘焙引擎。

Theme baking engine.
"""
from typing import Optional

from manim import ManimColor

from .._db import ColorDB

_REQUIRED_ROLES = [
    "scene_background", "scene_flash",
    "grid_line", "grid_axis",
    "primary_fill", "accent_fill",
    "orbit_stroke", "ring_stroke", "icon_fill",
    "title", "title_gradient_end",
    "infinity", "tagline", "decorative_line",
    "body_text", "muted_text",
    "success", "danger", "warning", "information",
    "white", "black",
]


class Theme:
    """主题烘焙引擎。

    Theme baking engine.

    缺少必需角色时构造抛出 ValueError。
    """

    # ── 场景 ──
    SCENE_BACKGROUND_COLOR: ManimColor
    SCENE_FLASH_COLOR: ManimColor

    # ── 网格 ──
    GRID_LINE_COLOR: ManimColor
    GRID_AXIS_COLOR: ManimColor

    # ── 图形 ──
    PRIMARY_FILL_COLOR: ManimColor
    ACCENT_FILL_COLOR: ManimColor
    ORBIT_STROKE_COLOR: ManimColor
    RING_STROKE_COLOR: ManimColor
    ICON_FILL_COLOR: ManimColor

    # ── 文字 ──
    TITLE_COLOR: ManimColor
    TITLE_GRADIENT_END_COLOR: ManimColor
    INFINITY_COLOR: ManimColor
    TAGLINE_COLOR: ManimColor
    DECORATIVE_LINE_COLOR: ManimColor
    BODY_TEXT_COLOR: ManimColor
    MUTED_TEXT_COLOR: ManimColor

    # ── 语义 ──
    SUCCESS_COLOR: ManimColor
    DANGER_COLOR: ManimColor
    WARNING_COLOR: ManimColor
    INFORMATION_COLOR: ManimColor

    # ── 基础 ──
    WHITE_COLOR: ManimColor
    BLACK_COLOR: ManimColor

    def __init__(self, db: ColorDB, name: str) -> None:
        data = db.get_theme(name)
        if not data:
            raise ValueError(f"Theme '{name}' not found in database")

        for role, record in data.items():
            attr = self._role_to_attr(role)
            setattr(self, attr, record.to_manim_color())

        missing = [
            r for r in _REQUIRED_ROLES
            if not hasattr(self, self._role_to_attr(r))
        ]
        if missing:
            raise ValueError(
                f"Theme '{name}' is missing required roles: {missing}"
            )

    @staticmethod
    def _role_to_attr(role: str) -> str:
        return role.upper() + "_COLOR"

    def all(self) -> dict[str, ManimColor]:
        return {r: getattr(self, self._role_to_attr(r)) for r in _REQUIRED_ROLES}
