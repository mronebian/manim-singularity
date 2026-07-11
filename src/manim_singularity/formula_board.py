"""公式推导板：左侧存档板 + 右侧演示区，各自独立可展示。

Formula derivation board: left archive panel + right demo area,
each independently displayable.
"""
from __future__ import annotations

import numpy as np
from manim import *
from typing import Callable, Optional

from .color import theme as _theme


class FormulaBoard:
    """公式推导板控制器。

    Formula derivation board controller.

    左右两板各自独立，可单独创建/销毁。
    颜色、尺寸、排版、动画时间全部可配置。
    场景层自行控制 VoiceOver 和步骤编排。

    使用方式：

        fb = FormulaBoard(self)
        fb.create_left_board()
        fb.create_demo_area()
        fb.create_divider()
        with vo.context("..."):
            fb.show(r"\\frac{d}{dx} a^x = ...")
            fb.archive()
        fb.conclude(r"\\frac{d}{dx} e^x = e^x")
        fb.dissolve()
    """

    def __init__(
        self,
        scene: Scene,
        *,
        # ── 布局尺寸 ──
        board_width_ratio: float = 0.45,
        board_height_ratio: float = 0.75,
        board_buff: float = 0.3,
        board_shift_x: float = 0.0,
        board_shift_y: float = 0.5,

        # ── 标题文字 ──
        board_title_text: str = "\u63a8\u5bfc\u8fc7\u7a0b",
        demo_title_text: str = "\u53d8\u6362\u6f14\u793a",
        board_title_size: float = 28,
        demo_title_size: float = 28,

        # ── 颜色接口 ──
        board_stroke_color: Optional[str] = None,
        board_fill_color: Optional[str] = None,
        board_fill_opacity: float = 0.3,
        demo_stroke_color: Optional[str] = None,
        demo_fill_color: Optional[str] = None,
        demo_fill_opacity: float = 0.3,
        divider_color: Optional[str] = None,
        divider_opacity: float = 0.5,
        board_title_color: Optional[str] = None,
        demo_title_color: Optional[str] = None,
        formula_color: Optional[str] = None,
        formula_gradient: Optional[tuple] = None,

        # ── 排版间距 ──
        title_board_gap: float = 0.15,
        board_title_gap: float = 0.6,
        slot_spacing: float = 0.85,
        arc_angle: float = -PI / 8,
        formula_font_size: float = 36,

        # ── 动画时间 ──
        layout_run_time: float = 1.2,
        show_run_time: float = 0.8,
        transform_run_time: float = 1.2,
        archive_run_time: float = 0.5,

        # ── 动画策略 ──
        archive_animation: str = "arc_fly",
        conclude_emphasis: str = "circumscribe",

        # ── 生命周期钩子 ──
        on_before_show: Optional[Callable] = None,
        on_after_show: Optional[Callable] = None,
        on_before_transform: Optional[Callable] = None,
        on_after_transform: Optional[Callable] = None,
        on_before_archive: Optional[Callable] = None,
        on_after_archive: Optional[Callable] = None,
        on_before_conclude: Optional[Callable] = None,
        on_after_conclude: Optional[Callable] = None,
    ) -> None:
        self.scene = scene

        # ── 布局尺寸 ──
        self._board_width_ratio = board_width_ratio
        self._board_height_ratio = board_height_ratio
        self._board_buff = board_buff
        self._board_shift = np.array([board_shift_x, board_shift_y, 0])

        # ── 标题文字 ──
        self._board_title_text = board_title_text
        self._demo_title_text = demo_title_text
        self._board_title_size = board_title_size
        self._demo_title_size = demo_title_size

        # ── 颜色 ──
        self._board_stroke_color = (
            board_stroke_color if board_stroke_color is not None
            else _theme.PRIMARY_FILL_COLOR
        )
        self._board_fill_color = (
            board_fill_color if board_fill_color is not None
            else _theme.MUTED_TEXT_COLOR
        )
        self._board_fill_opacity = board_fill_opacity
        self._demo_stroke_color = (
            demo_stroke_color if demo_stroke_color is not None
            else _theme.MUTED_TEXT_COLOR
        )
        self._demo_fill_color = (
            demo_fill_color if demo_fill_color is not None
            else BLACK
        )
        self._demo_fill_opacity = demo_fill_opacity
        self._divider_color = (
            divider_color if divider_color is not None
            else _theme.MUTED_TEXT_COLOR
        )
        self._divider_opacity = divider_opacity
        self._board_title_color = (
            board_title_color if board_title_color is not None
            else _theme.PRIMARY_FILL_COLOR
        )
        self._demo_title_color = (
            demo_title_color if demo_title_color is not None
            else _theme.WARNING_COLOR
        )
        self._formula_color = (
            formula_color if formula_color is not None
            else _theme.WARNING_COLOR
        )
        self._formula_gradient = formula_gradient

        # ── 排版 ──
        self._title_board_gap = title_board_gap
        self._board_title_gap = board_title_gap
        self._slot_spacing = slot_spacing
        self._arc_angle = arc_angle
        self._formula_font_size = formula_font_size

        # ── 动画时间 ──
        self._layout_run_time = layout_run_time
        self._show_run_time = show_run_time
        self._transform_run_time = transform_run_time
        self._archive_run_time = archive_run_time

        # ── 动画策略 ──
        self._archive_animation = archive_animation
        self._conclude_emphasis = conclude_emphasis

        # ── 生命周期钩子 ──
        self._on_before_show = on_before_show
        self._on_after_show = on_after_show
        self._on_before_transform = on_before_transform
        self._on_after_transform = on_after_transform
        self._on_before_archive = on_before_archive
        self._on_after_archive = on_after_archive
        self._on_before_conclude = on_before_conclude
        self._on_after_conclude = on_after_conclude

        # ── 内部状态 ──
        self._board: Optional[Rectangle] = None
        self._demo: Optional[Rectangle] = None
        self._divider: Optional[Line] = None
        self._board_title: Optional[Text] = None
        self._demo_title: Optional[Text] = None
        self._slots: list[Mobject] = []
        self._current: Optional[MathTex] = None

    # ==============================================================
    # 属性
    # ==============================================================

    @property
    def current(self) -> Optional[MathTex]:
        """演示区当前公式（可写）。"""
        return self._current

    @current.setter
    def current(self, mob: Optional[MathTex]) -> None:
        self._current = mob

    @property
    def slot_count(self) -> int:
        """已存档公式数量。"""
        return len(self._slots)

    @property
    def slots(self) -> list[Mobject]:
        """存档公式列表（返回副本）。"""
        return list(self._slots)

    @property
    def board(self) -> Optional[Rectangle]:
        """左侧推导板矩形。"""
        return self._board

    @property
    def demo(self) -> Optional[Rectangle]:
        """右侧演示区矩形。"""
        return self._demo

    @property
    def divider(self) -> Optional[Line]:
        """中部分隔线。"""
        return self._divider

    @property
    def board_title(self) -> Optional[Text]:
        """左侧标题。"""
        return self._board_title

    @property
    def demo_title(self) -> Optional[Text]:
        """右侧标题。"""
        return self._demo_title

    @property
    def board_created(self) -> bool:
        """左侧板是否已创建。"""
        return self._board is not None

    @property
    def demo_created(self) -> bool:
        """演示区是否已创建。"""
        return self._demo is not None

    # ==============================================================
    # 布局创建
    # ==============================================================

    def create_left_board(self, *, centered: bool = False) -> None:
        """创建左侧推导板及其标题。

        Create the left archive panel and its title.

        Args:
            centered: True 时面板居中，False 时靠左对齐。
        """
        self._cleanup_left_internal()

        self._board = Rectangle(
            width=config.frame_width * self._board_width_ratio,
            height=config.frame_height * self._board_height_ratio,
            fill_color=self._board_fill_color,
            fill_opacity=0,
            stroke_color=self._board_stroke_color,
            stroke_width=2,
        )
        if centered:
            self._board.move_to(ORIGIN).shift(self._board_shift)
        else:
            self._board.to_edge(LEFT, buff=self._board_buff).shift(self._board_shift)

        self._board_title = Text(
            self._board_title_text,
            font_size=self._board_title_size,
            color=self._board_title_color,
        )
        self._board_title.next_to(self._board, UP, buff=self._title_board_gap)

        self.scene.play(
            Create(self._board),
            Write(self._board_title),
            run_time=self._layout_run_time,
        )
        self.scene.play(
            self._board.animate.set_fill(opacity=self._board_fill_opacity),
            run_time=0.8,
        )

    def create_demo_area(self, *, centered: bool = False) -> None:
        """创建右侧演示区及其标题。

        Create the right demo area and its title.

        Args:
            centered: True 时面板居中，False 时靠右对齐。
        """
        self._cleanup_demo_internal()

        self._demo = Rectangle(
            width=config.frame_width * self._board_width_ratio,
            height=config.frame_height * self._board_height_ratio,
            fill_color=self._demo_fill_color,
            fill_opacity=0,
            stroke_color=self._demo_stroke_color,
            stroke_width=1,
        )
        if centered:
            self._demo.move_to(ORIGIN).shift(self._board_shift)
        else:
            self._demo.to_edge(RIGHT, buff=self._board_buff).shift(self._board_shift)

        self._demo_title = Text(
            self._demo_title_text,
            font_size=self._demo_title_size,
            color=self._demo_title_color,
        )
        self._demo_title.next_to(self._demo, UP, buff=self._title_board_gap)

        self.scene.play(
            Create(self._demo),
            Write(self._demo_title),
            run_time=self._layout_run_time,
        )
        self.scene.play(
            self._demo.animate.set_fill(opacity=self._demo_fill_opacity),
            run_time=0.8,
        )

    def create_divider(self) -> None:
        """创建左右板之间的分隔线（两板都存在时才生效）。

        Create the divider line between the two panels.
        Only effective when both panels exist.
        """
        if self._board is None or self._demo is None:
            return

        if self._divider is not None:
            self.scene.remove(self._divider)
            self._divider = None

        self._divider = Line(
            start=UP * (config.frame_height * 0.3),
            end=DOWN * (config.frame_height * 0.3),
            color=self._divider_color,
            stroke_width=1,
            stroke_opacity=self._divider_opacity,
        )
        self.scene.play(Create(self._divider), run_time=0.5)

    def create_all(self) -> None:
        """同时创建左右面板和分隔线（创建动画合并为一次 play）。

        等同于依次调用 create_left_board() + create_demo_area() + create_divider()，
        但所有 Create/Write 动画合并播放，节省总时长。
        """
        self._cleanup_left_internal()
        self._cleanup_demo_internal()

        if self._divider is not None:
            self.scene.remove(self._divider)
            self._divider = None

        # ── 左侧板 ──
        self._board = Rectangle(
            width=config.frame_width * self._board_width_ratio,
            height=config.frame_height * self._board_height_ratio,
            fill_color=self._board_fill_color,
            fill_opacity=0,
            stroke_color=self._board_stroke_color,
            stroke_width=2,
        )
        self._board.to_edge(LEFT, buff=self._board_buff).shift(self._board_shift)

        self._board_title = Text(
            self._board_title_text,
            font_size=self._board_title_size,
            color=self._board_title_color,
        )
        self._board_title.next_to(self._board, UP, buff=self._title_board_gap)

        # ── 右侧演示区 ──
        self._demo = Rectangle(
            width=config.frame_width * self._board_width_ratio,
            height=config.frame_height * self._board_height_ratio,
            fill_color=self._demo_fill_color,
            fill_opacity=0,
            stroke_color=self._demo_stroke_color,
            stroke_width=1,
        )
        self._demo.to_edge(RIGHT, buff=self._board_buff).shift(self._board_shift)

        self._demo_title = Text(
            self._demo_title_text,
            font_size=self._demo_title_size,
            color=self._demo_title_color,
        )
        self._demo_title.next_to(self._demo, UP, buff=self._title_board_gap)

        # ── 分隔线 ──
        self._divider = Line(
            start=UP * (config.frame_height * 0.3),
            end=DOWN * (config.frame_height * 0.3),
            color=self._divider_color,
            stroke_width=1,
            stroke_opacity=self._divider_opacity,
        )

        # 一次性播放创建动画
        self.scene.play(
            Create(self._board),
            Write(self._board_title),
            Create(self._demo),
            Write(self._demo_title),
            Create(self._divider),
            run_time=self._layout_run_time,
        )

        # 填充动画
        self.scene.play(
            self._board.animate.set_fill(opacity=self._board_fill_opacity),
            self._demo.animate.set_fill(opacity=self._demo_fill_opacity),
            run_time=0.8,
        )

    # ==============================================================
    # 销毁
    # ==============================================================

    def destroy_left_board(self) -> None:
        """销毁左侧推导板、标题及所有存档公式。"""
        mobs = []
        if self._board is not None:
            mobs.append(self._board)
        if self._board_title is not None:
            mobs.append(self._board_title)
        mobs.extend(self._slots)

        if mobs:
            self.scene.play(*[FadeOut(m, run_time=0.3) for m in mobs])

        self._cleanup_left_internal()

    def destroy_demo_area(self) -> None:
        """销毁右侧演示区、标题及当前公式。"""
        mobs = []
        if self._demo is not None:
            mobs.append(self._demo)
        if self._demo_title is not None:
            mobs.append(self._demo_title)
        if self._current is not None:
            mobs.append(self._current)

        if mobs:
            self.scene.play(*[FadeOut(m, run_time=0.3) for m in mobs])

        self._cleanup_demo_internal()

    def destroy_divider(self) -> None:
        """销毁分隔线。"""
        if self._divider is not None:
            self.scene.play(FadeOut(self._divider, run_time=0.2))
            self.scene.remove(self._divider)
            self._divider = None

    def dissolve(self) -> None:
        """一次性淡出所有元素并重置状态。"""
        mobs = []
        if self._board is not None:
            mobs.append(self._board)
        if self._board_title is not None:
            mobs.append(self._board_title)
        if self._demo is not None:
            mobs.append(self._demo)
        if self._demo_title is not None:
            mobs.append(self._demo_title)
        if self._divider is not None:
            mobs.append(self._divider)
        if self._current is not None:
            mobs.append(self._current)
        mobs.extend(self._slots)

        if mobs:
            self.scene.play(*[FadeOut(m, run_time=0.25) for m in mobs])

        self._board = None
        self._demo = None
        self._divider = None
        self._board_title = None
        self._demo_title = None
        self._slots = []
        self._current = None

    def reset(
        self,
        *,
        board_title: Optional[str] = None,
        demo_title: Optional[str] = None,
    ) -> None:
        """重置推导内容，保留 UI 面板。

        Reset derivation content while keeping the UI panels.

        Args:
            board_title: 新左侧标题，None 保持不变。
            demo_title: 新右侧标题，None 保持不变。
        """
        for s in self._slots:
            self.scene.remove(s)
        self._slots = []

        if self._current is not None:
            self.scene.remove(self._current)
            self._current = None

        if board_title is not None and self._board_title is not None:
            new_bt = Text(
                board_title,
                font_size=self._board_title_size,
                color=self._board_title_color,
            )
            new_bt.move_to(self._board_title)
            self.scene.play(
                ReplacementTransform(self._board_title, new_bt), run_time=0.4
            )
            self._board_title = new_bt
            self._board_title_text = board_title

        if demo_title is not None and self._demo_title is not None:
            new_dt = Text(
                demo_title,
                font_size=self._demo_title_size,
                color=self._demo_title_color,
            )
            new_dt.move_to(self._demo_title)
            self.scene.play(
                ReplacementTransform(self._demo_title, new_dt), run_time=0.4
            )
            self._demo_title = new_dt
            self._demo_title_text = demo_title

    # ==============================================================
    # 公式操作
    # ==============================================================

    def show(
        self,
        tex: str,
        *,
        font_size: Optional[float] = None,
        color: Optional[str] = None,
        gradient: Optional[tuple] = None,
        **kwargs,
    ) -> MathTex:
        """在演示区展示一个新公式。

        Display a new formula in the demo area.

        内部实现：创建 MathTex 后调用 self.show_mobject()。

        Args:
            tex: LaTeX 公式字符串。
            font_size: 字号，默认使用构造参数。
            color: 颜色，默认使用构造参数。
            gradient: 渐变色元组。

        Returns:
            创建的 MathTex，同时设置为 current。
        """
        font_size = font_size or self._formula_font_size
        color = color or self._formula_color

        mob = MathTex(tex, font_size=font_size, color=color, **kwargs)
        if gradient:
            mob.set_color_by_gradient(*gradient)
        elif self._formula_gradient:
            mob.set_color_by_gradient(*self._formula_gradient)

        self.show_mobject(
            mob,
            tex=tex,
            font_size=font_size,
            color=color,
        )
        return mob

    def show_mobject(
        self,
        mob: Mobject,
        *,
        run_time: Optional[float] = None,
        **hook_context,
    ) -> Mobject:
        """在演示区展示任意 Mobject。

        Display an arbitrary Mobject in the demo area.

        show() 的内部实现即调用此方法。
        支持非公式内容：图片、Text、SVG、3D 物体等。

        Args:
            mob: 任意 Mobject（必填）。
            run_time: 动画时长，默认 show_run_time。

        Returns:
            传入的 Mobject（同时设为 current）。
        """
        run_time = run_time or self._show_run_time

        center_area = self._demo if self._demo is not None else self._board
        if center_area is not None:
            mob.move_to(center_area.get_center())

        self._run_hook(self._on_before_show, mob, **hook_context)
        self.scene.play(Write(mob), run_time=run_time)
        self._current = mob
        self._run_hook(self._on_after_show, mob, **hook_context)
        return mob

    def transform(
        self,
        tex: str,
        *,
        font_size: Optional[float] = None,
        color: Optional[str] = None,
        gradient: Optional[tuple] = None,
        path_arc: float = 0,
        transform_mismatches: bool = True,
        **kwargs,
    ) -> MathTex:
        """从 current 公式 TransformMatchingTex 到新公式。

        Transform the current formula to a new one via TransformMatchingTex.

        current 为 None 时自动降级为 show()。

        Args:
            tex: 目标 LaTeX 字符串。
            font_size: 字号。
            color: 颜色。
            gradient: 渐变色。
            path_arc: 变换路径弧度。
            transform_mismatches: 是否变换不匹配的部分。

        Returns:
            新 MathTex，同时设置为 current。
        """
        if self._current is None:
            return self.show(
                tex,
                font_size=font_size,
                color=color,
                gradient=gradient,
                **kwargs,
            )

        font_size = font_size or self._formula_font_size
        color = color or self._formula_color

        next_mob = MathTex(tex, font_size=font_size, color=color, **kwargs)
        if gradient:
            next_mob.set_color_by_gradient(*gradient)
        elif self._formula_gradient:
            next_mob.set_color_by_gradient(*self._formula_gradient)

        center_area = self._demo if self._demo is not None else self._board
        if center_area is not None:
            next_mob.move_to(center_area.get_center())

        self._run_hook(
            self._on_before_transform, self._current,
            target_tex=tex, path_arc=path_arc,
        )
        self.scene.play(
            TransformMatchingTex(
                self._current,
                next_mob,
                path_arc=path_arc,
                transform_mismatches=transform_mismatches,
            ),
            run_time=self._transform_run_time,
        )
        self.scene.remove(self._current)
        self._current = next_mob
        self._run_hook(
            self._on_after_transform, next_mob,
            target_tex=tex, path_arc=path_arc,
        )
        return next_mob

    def archive(self, mob: Optional[Mobject] = None) -> Mobject:
        """克隆公式并飞入左侧推导板。

        Clone a formula and fly/fade/write it into the left archive panel.

        动画类型由构造参数 archive_animation 控制：
          - "arc_fly"（默认）：弧线飞行 + 缩放
          - "fade_in"：目标位置直接 FadeIn
          - "write_in"：目标位置 Write 动画

        Args:
            mob: 要存档的 mobject，默认 self.current。

        Returns:
            存档后的克隆体（已加入场景）。

        Raises:
            ValueError: 无 mobject 可存档（current 为 None 且未传入 mob）。
        """
        source = mob if mob is not None else self._current
        if source is None:
            raise ValueError(
                "No mobject to archive — provide a mobject or set current first"
            )

        clone = source.copy()
        clone.scale(0.75)

        slot_index = len(self._slots)
        if self._board_title is not None:
            start_y = self._board_title.get_bottom()[1] - self._board_title_gap
        elif self._board is not None:
            start_y = self._board.get_top()[1] - self._board_title_gap
        else:
            start_y = 0

        target_y = start_y - slot_index * self._slot_spacing
        target_x = (
            self._board.get_left()[0] + 0.4
            if self._board is not None
            else -config.frame_width * self._board_width_ratio / 2 + 0.4
        )

        clone.move_to([target_x, target_y, 0])
        if self._board is not None:
            clone.align_to(self._board, LEFT)
        clone.shift(RIGHT * 0.25)

        self._slots.append(clone)

        self._run_hook(
            self._on_before_archive, source,
            source_mob=source, slot_index=slot_index,
        )

        if self._archive_animation == "arc_fly":
            self.scene.play(
                MoveAlongPath(
                    clone,
                    ArcBetweenPoints(
                        source.get_center(),
                        clone.get_center(),
                        angle=self._arc_angle,
                    ),
                ),
                run_time=self._archive_run_time,
            )
        elif self._archive_animation == "fade_in":
            self.scene.play(FadeIn(clone, run_time=self._archive_run_time))
        elif self._archive_animation == "write_in":
            self.scene.play(Write(clone, run_time=self._archive_run_time))

        self._run_hook(
            self._on_after_archive, clone,
            source_mob=source, slot_index=slot_index,
        )
        return clone

    def conclude(
        self,
        tex: str,
        *,
        font_size: Optional[float] = None,
        color: Optional[str] = None,
        gradient: Optional[tuple] = None,
        circumscribe_color: str = YELLOW,
        circumscribe_run_time: float = 1.5,
        **kwargs,
    ) -> MathTex:
        """最终结论：变换 + 渐变 + 强调动画。

        Final conclusion: transform, apply gradient, and emphasis animation.

        强调动画类型由构造参数 conclude_emphasis 控制：
          - "circumscribe"（默认）：环绕描边强调
          - "indicate"：Indicate 缩放强调
          - "flash"：背景闪光强调

        默认渐变 (GOLD, YELLOW, ORANGE)。

        Args:
            tex: LaTeX 公式字符串。
            font_size: 字号（默认加 12pt）。
            color: 颜色。
            gradient: 渐变色，默认 (GOLD, YELLOW, ORANGE)。
            circumscribe_color: 强调边框颜色。
            circumscribe_run_time: 强调动画时长。

        Returns:
            结论 MathTex。
        """
        if gradient is None:
            gradient = (GOLD, YELLOW, ORANGE)
        if font_size is None:
            font_size = self._formula_font_size + 12

        if self._current is not None:
            self._run_hook(
                self._on_before_conclude, self._current,
                tex=tex, gradient=gradient,
            )

        mob = self.transform(
            tex,
            font_size=font_size,
            color=color,
            gradient=gradient,
            **kwargs,
        )

        if self._conclude_emphasis == "circumscribe":
            self.scene.play(
                Circumscribe(mob, color=circumscribe_color, time_width=1.5),
                run_time=circumscribe_run_time,
            )
        elif self._conclude_emphasis == "indicate":
            self.scene.play(
                Indicate(mob, color=circumscribe_color, scale_factor=1.2),
                run_time=circumscribe_run_time,
            )
        elif self._conclude_emphasis == "flash":
            flash_rect = FullScreenRectangle(
                fill_opacity=0.15, fill_color=circumscribe_color, stroke_width=0,
            )
            self.scene.play(
                FadeIn(flash_rect, run_time=0.15),
                FadeOut(flash_rect, run_time=circumscribe_run_time - 0.15),
            )

        self._run_hook(
            self._on_after_conclude, mob,
            tex=tex, gradient=gradient,
        )
        return mob

    def indicate(
        self,
        part,
        *,
        color: str = YELLOW,
        scale_factor: float = 1.1,
        run_time: float = 1.2,
    ) -> None:
        """高亮公式的某一部分。

        Highlight a part of the current formula.

        Args:
            part: Mobject 或 MathTex 子对象（如 fb.current[2:5]）。
            color: 高亮颜色。
            scale_factor: 放大倍数。
            run_time: 动画时长。

        Raises:
            ValueError: current 为 None 时抛出。
        """
        if self._current is None:
            raise ValueError(
                "请先调用 show() 或 transform() 创建公式"
            )
        self.scene.play(
            Indicate(part, color=color, scale_factor=scale_factor),
            run_time=run_time,
        )

    def clear_demo(self) -> None:
        """清除演示区的当前公式。"""
        if self._current is not None:
            self.scene.remove(self._current)
            self._current = None

    # ==============================================================
    # 内部辅助
    # ==============================================================

    def _run_hook(
        self,
        hook: Optional[Callable],
        mob: Mobject,
        **context,
    ) -> None:
        """执行生命周期钩子回调。

        Execute a lifecycle hook callback.

        如果回调返回 Mobject 或 list[Mobject]，自动调用 self.scene.play()。
        """
        if hook is None:
            return
        result = hook(mob, **context)
        if result is None:
            return
        items = result if isinstance(result, (list, tuple)) else [result]
        self.scene.play(*items)

    def _cleanup_left_internal(self) -> None:
        """静默清除左侧板相关元素（无动画）。"""
        if self._board is not None:
            self.scene.remove(self._board)
        if self._board_title is not None:
            self.scene.remove(self._board_title)
        for s in self._slots:
            self.scene.remove(s)
        self._board = None
        self._board_title = None
        self._slots = []

    def _cleanup_demo_internal(self) -> None:
        """静默清除演示区相关元素（无动画）。"""
        if self._demo is not None:
            self.scene.remove(self._demo)
        if self._demo_title is not None:
            self.scene.remove(self._demo_title)
        if self._current is not None:
            self.scene.remove(self._current)
        self._demo = None
        self._demo_title = None
        self._current = None
