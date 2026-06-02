"""manim_singularity — 奇点 IP 视觉资产包。

manim_singularity — Singularity IP visual asset package.

设计策略（LSP 兼容 + CLI 零 manim）：
  - ColorDB / ColorRecord / color 子包：静态导入，零 manim 依赖
  - VoiceOver / Theme / SingularityIP 等：__getattr__ 懒加载
  - TYPE_CHECKING 块用 import X as X 语法，确保 Pyright 识别为公开 API
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .voiceover import VoiceOver as VoiceOver
    from .theme import (
        SingularityIP as SingularityIP,
        EllipseBase as EllipseBase,
        EndingCard as EndingCard,
    )
    from .color import (
        ColorDB as ColorDB,
        ColorRecord as ColorRecord,
        Theme as Theme,
        theme as theme,
    )

# 置顶 __all__，在 __getattr__ 之前定义，避免 Pyright 被 __getattr__ 拦截
__all__ = [
    "VoiceOver",
    "ColorDB",
    "ColorRecord",
    "Theme",
    "theme",
    "SingularityIP",
    "EllipseBase",
    "EndingCard",
]

# ── 零 manim 依赖，静态导入 ──
from . import color
from .color import ColorDB, ColorRecord


def __getattr__(name: str):
    """懒加载代理：按需导入子模块，避免 manim 依赖污染。

    Lazy loading proxy: import submodules on demand to keep CLI zero-manim.

    Args:
        name: 导出的属性名。

    Returns:
        请求的子模块或类实例。

    Raises:
        AttributeError: 未知的导出名。
    """
    if name == "VoiceOver":
        from .voiceover import VoiceOver
        return VoiceOver
    if name in ("SingularityIP", "EllipseBase", "EndingCard"):
        from .theme import SingularityIP, EllipseBase, EndingCard
        return locals()[name]
    if name == "Theme":
        from .color import Theme
        return Theme
    if name == "theme":
        return getattr(__import__("manim_singularity.color", fromlist=[name]), name)
    raise AttributeError(f"module 'manim_singularity' has no attribute {name!r}")
