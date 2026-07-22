"""字幕系统。

Subtitle system.

全参数化字幕引擎，支持自定义字体、颜色、渐变、入场/退场动画。
"""

import re
from typing import Any, Callable, Optional, Tuple, Union

from manim_singularity.compat import (
    BOLD,
    DOWN,
    FadeIn,
    FadeOut,
    MathTex,
    RIGHT,
    Scene,
    Text,
    VGroup,
    IS_MANIM_GL,
    fix_in_frame,
    unfix_from_frame,
    set_color_by_t2c,
)


class SubtitleSystem:
    """字幕系统。

    Subtitle system.

    通过 VoiceOver 的 subtitle_kwargs 参数传入自定义配置。
    支持渐变、逐字着色、自定义入场/退场动画等。
    """

    def __init__(
        self,
        scene: Scene,
        *,
        font_size: int = 32,
        font: Optional[str] = None,
        color: Optional[str] = None,
        t2c: Optional[dict] = None,
        gradient: Tuple[str, str] = ("#00E5FF", "#0077FF"),
        position: Any = DOWN,
        buff: float = 0.5,
        entrance_animation: Callable = FadeIn,
        entrance_run_time: Optional[float] = None,
        exit_animation: Callable = FadeOut,
        exit_run_time: float = 0.3,
        exit_shift: Any = DOWN * 0.3,
        weight: str = BOLD,
        line_spacing: float = 1.2,
        add_fixed_in_frame: bool = True,
    ) -> None:
        """初始化字幕系统。

        Initialize the subtitle system.

        Args:
            scene: 当前 Manim Scene 实例。
            font_size: 字号。
            font: 字体名称。
            color: 单色（与 gradient 互斥）。
            t2c: 逐字着色字典。
            gradient: 渐变色元组（与 color 互斥）。
            position: 字幕位置。
            buff: 边距。
            entrance_animation: 入场动画类型。
            entrance_run_time: 入场动画时长。None 时自动计算为 min(0.6, duration*0.3)。
            exit_animation: 离场动画类型。
            exit_run_time: 离场动画时长。
            exit_shift: 离场位移方向。
            weight: 字重。
            line_spacing: 行距。
            add_fixed_in_frame: 是否添加到固定帧（3D 场景中保持在屏幕平面）。
        """
        self.scene = scene
        self.font_size = font_size
        self.font = font
        self.color = color
        self.t2c = t2c
        self.gradient = gradient
        self.position = position
        self.buff = buff
        self.entrance_animation = entrance_animation
        self.entrance_run_time = entrance_run_time
        self.exit_animation = exit_animation
        self.exit_run_time = exit_run_time
        self.exit_shift = exit_shift
        self.weight = weight
        self.line_spacing = line_spacing
        self.add_fixed_in_frame = add_fixed_in_frame

    def create_subtitle(self, text: str) -> Union[Text, MathTex, VGroup]:
        """创建字幕对象（自动识别内联 LaTeX）。

        Create a subtitle object (auto-detect inline LaTeX).

        支持内联 $...$ 公式：纯文本 → Text，
        纯公式 $...$ → MathTex，混合 $...$ 公式 + 文本 → VGroup。

        Supports inline $...$ formulas: pure text → Text,
        pure formula $...$ → MathTex, mixed → VGroup.

        Args:
            text: 字幕文本 / 可含内联 $...$ 公式的文本。

        Returns:
            已着色并定位的 Text、MathTex 或 VGroup 对象。
        """
        dollar_count = text.count("$")

        if dollar_count >= 2 and dollar_count % 2 == 0:
            segments = re.split(r"(\$[^$]*\$)", text)
            parts = []
            for i, seg in enumerate(segments):
                if not seg:
                    continue
                if i % 2 == 0:
                    kwargs = {
                        "font_size": self.font_size,
                        "weight": self.weight,
                    }
                    if not IS_MANIM_GL:
                        kwargs["line_spacing"] = self.line_spacing
                    if self.font is not None:
                        kwargs["font"] = self.font
                    mob = Text(seg, **kwargs)
                else:
                    tex = seg[1:-1]
                    mob = MathTex(tex, font_size=self.font_size + 10)
                mob._is_subtitle = True
                parts.append(mob)

            mob = VGroup(*parts).arrange(RIGHT, buff=0.12)
            mob._is_subtitle = True
            mob.to_edge(self.position, buff=self.buff)
        else:
            kwargs = {
                "font_size": self.font_size,
                "weight": self.weight,
            }
            if not IS_MANIM_GL:
                kwargs["line_spacing"] = self.line_spacing
            if self.font is not None:
                kwargs["font"] = self.font
            mob = Text(text, **kwargs).to_edge(self.position, buff=self.buff)
            mob._is_subtitle = True

        if self.t2c is not None:
            set_color_by_t2c(mob, self.t2c)
        elif self.color is not None:
            mob.set_color(self.color)
        elif self.gradient is not None:
            mob.set_color_by_gradient(*self.gradient)

        return mob

    def play_entrance(self, subtitle: Text, duration: float) -> float:
        """播放字幕入场动画。

        Play the subtitle entrance animation.

        Args:
            subtitle: 字幕 Text 对象。
            duration: 语音总时长（秒），用于自动计算入场时长。

        Returns:
            入场动画实际时长（秒）。
        """
        if self.entrance_run_time is not None:
            run_time = self.entrance_run_time
        else:
            run_time = min(0.6, duration * 0.3)
        self.scene.play(self.entrance_animation(subtitle), run_time=run_time)
        return run_time

    def play_exit(self, subtitle: Text) -> float:
        """播放字幕退场动画。

        Play the subtitle exit animation.

        Args:
            subtitle: 字幕 Text 对象。

        Returns:
            退场动画时长（秒）。
        """
        self.scene.play(
            self.exit_animation(subtitle, shift=self.exit_shift),
            run_time=self.exit_run_time,
        )
        return self.exit_run_time

    def add_to_scene(self, mob: Text) -> None:
        """将字幕对象添加到场景。

        Add a subtitle mobject to the scene.

        根据 add_fixed_in_frame 决定是否添加到固定帧。

        Args:
            mob: 字幕 Text 对象。
        """
        if self.add_fixed_in_frame:
            if IS_MANIM_GL:
                fix_in_frame(mob)
                self.scene.add(mob)
            else:
                self.scene.add(mob)

    def remove_from_scene(self, mob: Text) -> None:
        """从场景移除字幕对象。

        Remove a subtitle mobject from the scene.

        Args:
            mob: 字幕 Text 对象。
        """
        if self.add_fixed_in_frame:
            if IS_MANIM_GL:
                unfix_from_frame(mob)
                self.scene.remove(mob)
        else:
            self.scene.remove(mob)
