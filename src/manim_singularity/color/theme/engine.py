from typing import Optional

from manim import ManimColor

from ..core.database import ColorDB

_REQUIRED_ROLES = [
    "background", "surface", "grid_line", "grid_axis",
    "primary_fill", "secondary_fill", "accent_fill",
    "title", "title_gradient_end", "text", "text_muted",
    "success", "danger", "warning", "information",
    "white", "black",
]


class Theme:
    """
    主题烘焙引擎。将 ColorDB 中一个主题的所有角色颜色烘焙为 ManimColor 对象。
    属性名表明用途，所有主题遵循同一套 17 个角色。

    用法：
        theme = Theme(db, "赛博蓝夜")
        mobject.set_color(theme.PRIMARY_FILL_COLOR)
    """

    BACKGROUND_COLOR: ManimColor
    SURFACE_COLOR: ManimColor
    GRID_LINE_COLOR: ManimColor
    GRID_AXIS_COLOR: ManimColor
    PRIMARY_FILL_COLOR: ManimColor
    SECONDARY_FILL_COLOR: ManimColor
    ACCENT_FILL_COLOR: ManimColor
    TITLE_COLOR: ManimColor
    TITLE_GRADIENT_END_COLOR: ManimColor
    TEXT_COLOR: ManimColor
    TEXT_MUTED_COLOR: ManimColor
    SUCCESS_COLOR: ManimColor
    DANGER_COLOR: ManimColor
    WARNING_COLOR: ManimColor
    INFORMATION_COLOR: ManimColor
    WHITE_COLOR: ManimColor
    BLACK_COLOR: ManimColor

    def __init__(self, db: ColorDB, name: str):
        data = db.get_theme(name)
        if not data:
            raise ValueError(f"Theme '{name}' not found in database")

        for role, record in data.items():
            attr = self._role_to_attr(role)
            setattr(self, attr, record.to_manim_color())

        missing = [r for r in _REQUIRED_ROLES if not hasattr(self, self._role_to_attr(r))]
        if missing:
            raise ValueError(
                f"Theme '{name}' is missing required roles: {missing}"
            )

    @staticmethod
    def _role_to_attr(role: str) -> str:
        """db 角色名 → 属性名：primary_fill → PRIMARY_FILL_COLOR"""
        return role.upper() + "_COLOR"

    def all(self) -> dict[str, ManimColor]:
        return {r: getattr(self, self._role_to_attr(r)) for r in _REQUIRED_ROLES}
