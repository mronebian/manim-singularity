import os, sys
from typing import Optional

_USING_MANIMGL = "manimlib" in sys.modules

if _USING_MANIMGL:
    from manimlib import *
    from manimlib.animation.composition import LaggedStart
    from manimlib.animation.transform import ReplacementTransform
    from manimlib.animation.indication import Flash
    from manimlib.animation.creation import Write
    from manimlib.mobject.svg.svg_mobject import SVGMobject as _SVGMobject
    import manimlib.utils.rate_functions as _rf

    class SVGMobject(_SVGMobject):
        """Wrap ManimGL SVGMobject to match ManimCE-style chained API."""
        pass

    GRAY = GREY

    rate_functions = _rf
    rate_functions.ease_out_elastic = _rf.smooth
    rate_functions.ease_out_back = _rf.smooth
    rate_functions.ease_in_back = _rf.smooth
else:
    from manim import *

from .color import theme


# ==========================================
# 1. 奇点 IP 片头转场库
# ==========================================
class SingularityIP:
    """奇点 IP 片头转场引擎。

    Singularity IP intro animation engine.

    播放标准化的开场动画（轨道展开 → 核心绽放 → 变形离场）。
    支持将核心图形动态变形成正片标题并蓄力飞出。
    """

    def __init__(self, scene: Scene) -> None:
        """初始化片头引擎。

        Initialize the intro engine.

        Args:
            scene: 当前 Manim Scene 实例，动画直接作用于该场景。
        """
        self.scene = scene

    def play_intro(
        self,
        target_title: Optional[Mobject] = None,
        *,
        keep_final: bool = False,
    ) -> Optional[Mobject]:
        """播放完整片头动画序列。

        Play the full intro animation sequence.

        动画流程：三轨道展开 → 无穷符号绽放 → 细节元素浮现 → 变形/离场。
        若传入 target_title，片头几何体将在尾声变形成目标标题，
        执行"下沉蓄力 → 向上飞出"的转场特效。

        Args:
            target_title: 目标标题对象。传入后片头几何体将变形为该标题。
            keep_final: 仅在 target_title 为 None 时生效。
                True 保留 Logo 在画面中央，False 自动飞出。

        Returns:
            最终留在画面上的 Mobject，可用于后续动画接力。
        """
        # ---------- 1. 轨道起手 ----------
        orbit_color = theme.ORBIT_STROKE_COLOR
        orbit1 = Ellipse(width=3.5, height=1.2, color=orbit_color, stroke_width=2)
        orbit2 = Ellipse(width=3.5, height=1.2, color=orbit_color, stroke_width=2).rotate(PI / 3)
        orbit3 = Ellipse(width=3.5, height=1.2, color=orbit_color, stroke_width=2).rotate(-PI / 3)

        self.scene.play(
            Create(orbit1),
            Create(orbit2),
            Create(orbit3),
            run_time=0.8,
            rate_func=smooth,
        )
        self.scene.wait(0.1)

        # ---------- 2. 核心绽放 ----------
        infinity = MathTex(r"\infty", font_size=120, color=theme.INFINITY_COLOR)
        infinity.z_index = 4
        infinity.scale(0.1)

        outer_ring = Circle(radius=2.2, color=theme.RING_STROKE_COLOR, stroke_width=4)
        inner_ring = Circle(radius=2.0, color=theme.RING_STROKE_COLOR, stroke_width=1.5)

        name_text = Text("奇  点", font_size=38, color="#C39BD3").set_color_by_gradient(
            "#FFFFFF", "#C39BD3", "#9B59B6"
        )
        name_text.next_to(outer_ring, DOWN, buff=0.3)

        tagline = Text("Infinity", font_size=16, color=theme.TAGLINE_COLOR).next_to(
            name_text, DOWN, buff=0.15
        )

        line_l = Line(
            LEFT * 0.9, LEFT * 0.15, stroke_width=1.2, color=theme.DECORATIVE_LINE_COLOR
        ).next_to(tagline, LEFT, buff=0.12)
        line_r = Line(
            RIGHT * 0.15, RIGHT * 0.9, stroke_width=1.2, color=theme.DECORATIVE_LINE_COLOR
        ).next_to(tagline, RIGHT, buff=0.12)

        self.scene.play(
            infinity.animate.scale(10),
            Flash(ORIGIN, color=theme.INFINITY_COLOR, line_length=0.6, num_lines=12),
            Create(VGroup(outer_ring, inner_ring)),
            FadeIn(name_text, shift=UP * 0.2),
            FadeIn(tagline, shift=UP * 0.2),
            Create(line_l),
            Create(line_r),
            run_time=1.0,
            lag_ratio=0.15,
            rate_func=smooth,
        )
        self.scene.wait(0.6)

        # ---------- 3. 丝滑化身正片标题，并蓄力离场 ----------
        final_mob = None

        if target_title is not None:
            noise_group = VGroup(name_text, tagline, line_l, line_r)
            core_geo = VGroup(outer_ring, inner_ring, orbit1, orbit2, orbit3, infinity)

            self.scene.play(
                FadeOut(noise_group, scale=0.8),
                ReplacementTransform(core_geo, target_title, path_arc=PI / 3),
                run_time=1.2,
                rate_func=smooth,
            )
            self.scene.wait(1.0)
            self.scene.play(
                target_title.animate.shift(DOWN * 0.4).scale(0.95),
                run_time=0.3,
                rate_func=smooth,
            )
            self.scene.play(
                target_title.animate.shift(UP * 6).set_opacity(0),
                run_time=0.5,
                rate_func=rush_into,
            )
            self.scene.remove(target_title)

        elif not keep_final:
            full_logo = VGroup(
                outer_ring,
                inner_ring,
                orbit1,
                orbit2,
                orbit3,
                infinity,
                name_text,
                tagline,
                line_l,
                line_r,
            )
            self.scene.play(
                full_logo.animate.shift(DOWN * 0.4).scale(0.95),
                run_time=0.3,
                rate_func=smooth,
            )
            self.scene.play(
                full_logo.animate.shift(UP * 6).set_opacity(0),
                run_time=0.5,
                rate_func=rush_into,
            )
            self.scene.remove(full_logo)
        else:
            final_mob = VGroup(
                outer_ring,
                inner_ring,
                orbit1,
                orbit2,
                orbit3,
                infinity,
                name_text,
                tagline,
                line_l,
                line_r,
            )

        return final_mob


# ==========================================
# 3. 几何网格场景基类
# ==========================================
class EllipseBase:
    """科幻网格场景工具类。

    Sci-fi grid scene utility class.

    提供网格创建、波浪展开、内爆消除等动画，
    以及标题/公式快速生成功能。
    内部自动使用 color 颜色库设置主题背景色。

    使用方式：
        el = EllipseBase(self)
        el.animate_grid_growth()

    Attributes:
        scene: 绑定的 Manim Scene 实例。
        grid: 自动创建的 NumberPlane 网格对象。
    """

    def __init__(self, scene: Scene) -> None:
        """初始化网格场景。

        Initialize the grid scene.

        自动设置背景色为 theme.SCENE_BACKGROUND_COLOR，
        创建一个标准 NumberPlane 网格。

        Args:
            scene: 当前 Manim Scene 实例。
        """
        self.scene = scene

        # 自动设置背景色
        self.scene.camera.background_color = theme.SCENE_BACKGROUND_COLOR

        # 创建网格
        self.grid = NumberPlane(
            x_range=[-10, 10, 1],
            y_range=[-6, 6, 1],
            background_line_style={
                "stroke_color": theme.WHITE_COLOR,
                "stroke_width": 2.0,
                "stroke_opacity": 0.6,
            },
        )
        self.grid.z_index = -1
        self.grid.axes.z_index = -1
        for line in self.grid.background_lines:
            line.z_index = -1

    def animate_grid_growth(self) -> None:
        """播放网格波浪式展开动画。

        Play the wave-style grid expansion animation.

        动画流程：
          1. 坐标轴从中心爆发渐显（1.0s）
          2. 坐标轴变为主题色（0.6s）
          3. 网格线逐条从中心波浪式扫描展开（3.0s）
          4. 全屏白色冲击波闪烁（0.5s）

        总时长约 5.6 秒。
        """

        # --- 步骤 1：坐标轴强化爆发 ---
        axes = self.grid.axes
        axes.set_stroke(width=4, color=WHITE, opacity=0)

        self.scene.play(
            axes.animate.set_stroke(opacity=1),
            GrowFromCenter(axes),
            run_time=1.0,
            rate_func=rush_from,
        )
        self.scene.play(
            axes.animate.set_stroke(
                width=2, color=theme.PRIMARY_FILL_COLOR, opacity=0.8
            ),
            run_time=0.6,
        )

        # --- 步骤 2：网格线提取 ---
        all_lines = self.grid.background_lines
        v_lines, h_lines = [], []

        for line in all_lines:
            start, end = line.get_start(), line.get_end()
            if np.isclose(start[0], end[0]) and abs(start[0]) > 0.1:
                v_lines.append(line)
            elif np.isclose(start[1], end[1]) and abs(start[1]) > 0.1:
                h_lines.append(line)

        v_lines.sort(key=lambda l: abs(l.get_start()[0]))
        h_lines.sort(key=lambda l: abs(l.get_start()[1]))

        def get_line_anim(lines):
            anims = []
            for l in lines:
                l.set_stroke(color=WHITE, opacity=0.8, width=2.5)
                grow = GrowFromCenter(l, run_time=0.4, rate_func=smooth)
                fade = l.animate(run_time=0.5).set_stroke(
                    color=theme.GRID_LINE_COLOR, opacity=0.7, width=1.5
                )
                anims.append(Succession(grow, fade))
            return anims

        # --- 步骤 3：波浪式扫描展开 ---
        self.scene.play(
            LaggedStart(*get_line_anim(v_lines), lag_ratio=0.06),
            LaggedStart(*get_line_anim(h_lines), lag_ratio=0.06),
            run_time=3.0,
        )

        # --- 步骤 4：视觉冲击波 ---
        flash_rect = FullScreenRectangle(
            fill_opacity=0.1, fill_color=WHITE, stroke_width=0
        )
        self.scene.play(
            FadeIn(flash_rect, run_time=0.1), FadeOut(flash_rect, run_time=0.4)
        )
        self.scene.add(self.grid)
        self.scene.wait(0.5)

    def animate_grid_removal(self) -> None:
        """播放网格内爆消除动画。

        Play the implosion-style grid removal animation.

        动画流程：
          1. 背景辅助线黯然淡出（0.8s）
          2. 坐标轴向中心极速收缩（0.6s）
          3. 从场景彻底移除网格实体

        总时长约 1.6 秒。
        """

        # 1. 让背景辅助线黯淡并消失
        self.scene.play(FadeOut(self.grid.background_lines), run_time=0.8)

        # 2. 让主坐标轴从四周往中心极速收缩（逆向展开）
        self.scene.play(Uncreate(self.grid.axes), run_time=0.6, rate_func=smooth)

        # 3. 彻底从场景中移除实体
        self.scene.remove(self.grid)
        self.scene.wait(0.2)

    def get_header(self, title_str: str, formula_str: str) -> VGroup:
        """生成顶部标题与公式的组合。

        Generate a header with title and formula.

        自动着色：标题使用 color.title_gradient() 渐变色，
         公式使用 theme.BODY_TEXT_COLOR。

        Args:
            title_str: 标题文本。
            formula_str: LaTeX 公式字符串。

        Returns:
            自动居中的 (标题 + 公式) 垂直组合。
        """
        title = Text(title_str, weight=BOLD, font_size=40).set_color_by_gradient(
            *theme.title_gradient()
        )
        formula = MathTex(formula_str, color=theme.BODY_TEXT_COLOR)
        return VGroup(title, formula).arrange(DOWN, buff=0.4).move_to(ORIGIN)

    def c2p(self, *args, **kwargs) -> np.ndarray:
        """将逻辑坐标转换为场景像素坐标。

        Convert logical coordinates to scene pixel coordinates.

        代理到 self.grid.c2p，方便在场景中定位。

        Args:
            *args: 坐标参数，同 NumberPlane.c2p。
            **kwargs: 关键字参数，同 NumberPlane.c2p。

        Returns:
            场景中的像素坐标数组。
        """
        return self.grid.c2p(*args, **kwargs)


# ==========================================
# 4. 片尾一键三连卡片
# ==========================================


class EndingCard:
    """奇点 IP 片尾三连卡片。

    Singularity IP ending card with three icons.

    提供三种场景变换模式（汇聚/变形/分配），
    图标逐一点亮动画，以及文字心跳效果。
    支持 SVG 图标和纯几何回退。

    使用方式：
        card = EndingCard(self)
        card.play_ending(mode="A")
    """

    _SVG_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "svg")

    def __init__(self, scene: Scene, exclude_mobjects: Optional[list] = None) -> None:
        """初始化片尾卡片。

        Initialize the ending card.

        Args:
            scene: 当前 Manim Scene 实例。
            exclude_mobjects: 需要排除在变换之外的 mobject 列表。
        """
        self.scene = scene
        self.exclude_mobjects = exclude_mobjects if exclude_mobjects is not None else []
        self.left_threshold = -2.5
        self.right_threshold = 2.5

    # ── 兼容性包装方法 ──
    def _safe_set_glow(self, mob, value):
        if hasattr(mob.__class__, "set_glow"):
            mob.set_glow(value)
        return mob

    # ── 内部工具方法 ──────────────────────────────

    def _load_icon(self, name: str) -> SVGMobject:
        svg_path = os.path.join(self._SVG_DIR, f"{name}.svg")
        if not os.path.exists(svg_path):
            icon = (
                Circle(radius=0.6)
                .set_fill(WHITE, opacity=1)
                .set_stroke(WHITE, opacity=0)
            )
        else:
            icon = (
                SVGMobject(svg_path)
                .scale(1.2)
                .set_fill(WHITE, opacity=1)
                .set_stroke(WHITE, opacity=0)
            )
        return self._safe_set_glow(icon, 0.3)

    def _build_icons(self) -> VGroup:
        good = self._load_icon("good")
        coin = self._load_icon("coin")
        favo = self._load_icon("favo")
        icons = VGroup(good, coin, favo)
        icons.arrange(RIGHT, buff=1.5).move_to(ORIGIN).shift(UP)
        return icons

    def _collect_mobjects(self):
        excluded_types = (NumberPlane, Axes, ThreeDAxes)
        return [
            m for m in self.scene.mobjects
            if not isinstance(m, excluded_types) and m not in self.exclude_mobjects
        ]

    # ── 公共入口 ──────────────────────────────────

    def play_ending(self, mode: str = "A") -> None:
        """播放完整的片尾动画。

        Play the full ending animation.

        动画流程：场景变换（Phase 1）→ 图标点亮（Phase 2）→ 文字心跳（Phase 3）。

        Args:
            mode: 场景变换模式，可选 "A"（汇聚）、"B"（变形）、"C"（分配）。
        """
        icons = self._build_icons()
        mode = mode.upper()

        if mode == "A":
            self._mode_converge(icons)
        elif mode == "B":
            self._mode_morph(icons)
        elif mode == "C":
            self._mode_assign(icons)

        self._icon_activation(icons)
        self._show_text_and_settle(icons)

    # ── Phase 1: 三种场景变换 ─────────────────────

    def _mode_converge(self, icons: VGroup):
        targets = [icon.get_center() for icon in icons]
        mobs = self._collect_mobjects()

        if mobs:
            self.scene.play(
                *[m.animate.scale(0).move_to(ORIGIN).set_opacity(0) for m in mobs],
                run_time=0.8,
                rate_func=smooth,
            )
            self.scene.remove(*mobs)

        self.scene.play(
            Flash(ORIGIN, color=WHITE, line_length=0.8, num_lines=16),
            run_time=0.3,
        )

        ghosts = [icon.copy().move_to(ORIGIN).scale(0) for icon in icons]
        for icon, pos in zip(icons, targets):
            icon.move_to(pos)

        self.scene.play(
            LaggedStart(
                *[
                    ReplacementTransform(
                        g, icon, rate_func=rate_functions.ease_out_elastic
                    )
                    for g, icon in zip(ghosts, icons)
                ],
                lag_ratio=0.15,
            ),
            run_time=1.5,
        )

    def _mode_morph(self, icons: VGroup):
        mobs = self._collect_mobjects()
        if not mobs:
            self._mode_converge(icons)
            return

        left, mid, right = [], [], []
        for m in mobs:
            x = m.get_center()[0]
            if x < self.left_threshold:
                left.append(m)
            elif x > self.right_threshold:
                right.append(m)
            else:
                mid.append(m)

        self._transform_groups([left, mid, right], icons)

    def _mode_assign(self, icons: VGroup):
        mobs = self._collect_mobjects()
        if not mobs:
            self._mode_converge(icons)
            return

        mobs.sort(key=lambda m: m.get_center()[0])
        n = len(mobs)

        if n == 1:
            groups = [[], mobs, []]
        elif n == 2:
            groups = [[mobs[0]], [], [mobs[1]]]
        else:
            q, r = divmod(n, 3)
            groups = []
            start = 0
            for i in range(3):
                size = q + (1 if i < r else 0)
                groups.append(mobs[start:start + size])
                start += size

        self._transform_groups(groups, icons)

    def _transform_groups(self, groups: list, icons: VGroup):
        animations = []
        for group, icon in zip(groups, icons):
            if group:
                vmobs = [m for m in group if isinstance(m, VMobject)]
                non_vmobs = [m for m in group if not isinstance(m, VMobject)]

                if vmobs:
                    animations.append(ReplacementTransform(VGroup(*vmobs), icon))
                else:
                    animations.append(FadeIn(icon, scale=0.5))

                if non_vmobs:
                    animations.append(FadeOut(Group(*non_vmobs)))
            else:
                animations.append(FadeIn(icon, scale=0.5))

        if animations:
            self.scene.play(*animations, run_time=1.2, rate_func=smooth)

    # ── Phase 2: 图标逐一点亮 ────────────────────

    def _icon_activation(self, icons: VGroup):
        palette = [theme.PRIMARY_FILL_COLOR, theme.SUCCESS_COLOR, theme.ACCENT_FILL_COLOR]

        for icon, clr in zip(icons, palette):
            self.scene.wait(0.08)

            self.scene.play(
                icon.animate.set_fill(clr, opacity=1).scale(1.35),
                run_time=0.28,
                rate_func=rate_functions.ease_out_elastic,
            )
            self._safe_set_glow(icon, 1.0)

            self.scene.play(
                icon.animate.scale(1 / 1.35 * 0.95),
                run_time=0.12,
                rate_func=smooth,
            )
            self._safe_set_glow(icon, 0.5)

            self.scene.play(
                icon.animate.scale(1 / 0.95),
                run_time=0.10,
                rate_func=smooth,
            )
            self._safe_set_glow(icon, 0.3)

    # ── Phase 3: 文字 + 心跳 ──────────────────────

    def _show_text_and_settle(self, icons: VGroup):
        text = Text("一键三连", font_size=50, color=WHITE, weight=BOLD)
        text.next_to(icons, DOWN, buff=0.8)

        comment = Text(
            "如果有什么想法，欢迎在评论区留言",
            font_size=26,
            color=GRAY,
        )
        comment.next_to(text, DOWN, buff=0.3)

        self.scene.play(Write(text), run_time=0.6)
        self.scene.play(Write(comment), run_time=0.5)

        palette = [theme.PRIMARY_FILL_COLOR, theme.SUCCESS_COLOR, theme.ACCENT_FILL_COLOR]

        self.scene.play(
            *[
                icon.animate.scale(1.2).set_fill(clr, opacity=1)
                for icon, clr in zip(icons, palette)
            ],
            text.animate.scale(1.05).set_color(palette[0]),
            run_time=0.3,
            rate_func=rate_functions.ease_out_back,
        )

        self.scene.play(
            *[icon.animate.scale(1 / 1.2) for icon in icons],
            text.animate.scale(1 / 1.05),
            run_time=0.3,
            rate_func=rate_functions.ease_in_back,
        )

        for icon in icons:
            self._safe_set_glow(icon, 0.6)

        self.scene.play(
            *[icon.animate.scale(1.05) for icon in icons],
            run_time=0.8,
            rate_func=there_and_back,
        )

        for icon in icons:
            self._safe_set_glow(icon, 0.3)

        self.scene.wait(1)
