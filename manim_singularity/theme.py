import os

from manim import *
from typing import Optional


# ==========================================
# 1. 全局主题配置库
# ==========================================
class NeonTheme:
    """奇点 IP 全局视觉主题配色"""

    BG_COLOR = "#0D1117"  # 深太空蓝背景
    COLOR_WHITE = "#FFFFFF"  # 纯白
    COLOR_ELLIPSE = "#00E5FF"  # 赛博蓝（用于主轨道和强调色）
    COLOR_GRID = "#1A2639"  # 暗蓝色（用于底层网格，防止喧宾夺主）
    COLOR_TITLE = ("#00E5FF", "#0077FF")  # 标题默认渐变色（青到蓝）
    TEXT = "#E6E6E6"  # 正文灰白色（比纯白更护眼）

    # B站片尾三连配色
    BILI_LIKE = "#FB7299"
    BILI_COIN = "#F5A623"
    BILI_FAVO = "#FFC107"
    # 非B站模式片尾配色
    ENDING_FALLBACK = ("#FF69B4", "#FF69B4", "#FF69B4")


# ==========================================
# 2. 奇点 IP 片头转场库
# ==========================================
class SingularityIP:
    """
    奇点 IP 动画资产管理库。
    【自然丝滑 + 蓄力飞出版】
    """

    def __init__(self, scene: Scene):
        self.scene = scene

    def play_intro(
        self,
        target_title: Optional[Mobject] = None,
        *,
        keep_final: bool = False,
    ) -> Optional[Mobject]:
        # ---------- 1. 轨道起手 ----------
        orbit1 = Ellipse(width=3.5, height=1.2, color="#79C0FF", stroke_width=2)
        orbit2 = Ellipse(width=3.5, height=1.2, color="#79C0FF", stroke_width=2).rotate(
            PI / 3
        )
        orbit3 = Ellipse(width=3.5, height=1.2, color="#79C0FF", stroke_width=2).rotate(
            -PI / 3
        )

        self.scene.play(
            Create(orbit1),
            Create(orbit2),
            Create(orbit3),
            run_time=0.8,
            rate_func=smooth,
        )
        self.scene.wait(0.1)

        # ---------- 2. 核心绽放 ----------
        infinity = MathTex(r"\infty", font_size=120, color="#9B6FBD")
        infinity.set_sheen(-0.3, DOWN).set_z_index(4).scale(0.1)

        outer_ring = Circle(radius=2.2, color="#58A6FF", stroke_width=4)
        inner_ring = Circle(radius=2.0, color="#58A6FF", stroke_width=1.5)

        name_text = Text("奇  点", font_size=38, color="#C39BD3").set_color_by_gradient(
            "#FFFFFF", "#C39BD3", "#9B59B6"
        )
        name_text.next_to(outer_ring, DOWN, buff=0.3)

        tagline = Text("Infinity", font_size=16, color="#7D3C98").next_to(
            name_text, DOWN, buff=0.15
        )

        line_l = Line(
            LEFT * 0.9, LEFT * 0.15, stroke_width=1.2, color="#6C3483"
        ).next_to(tagline, LEFT, buff=0.12)
        line_r = Line(
            RIGHT * 0.15, RIGHT * 0.9, stroke_width=1.2, color="#6C3483"
        ).next_to(tagline, RIGHT, buff=0.12)

        self.scene.play(
            infinity.animate.scale(10),
            Flash(ORIGIN, color="#9B6FBD", line_length=0.6, num_lines=12),
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
    """
    科幻网格场景工具类。
    提供网格创建、展开/消除动画、标题生成等功能。
    使用方式：el = EllipseBase(self)，然后调用 el.xxx()
    """

    def __init__(self, scene: Scene):
        """保存场景引用，创建网格"""
        self.scene = scene

        # 自动设置背景色
        self.scene.camera.background_color = NeonTheme.BG_COLOR

        # 创建网格
        self.grid = NumberPlane(
            x_range=[-10, 10, 1],
            y_range=[-6, 6, 1],
            background_line_style={
                "stroke_color": NeonTheme.COLOR_WHITE,
                "stroke_width": 2.0,
                "stroke_opacity": 0.6,
            },
        )

    def animate_grid_growth(self):
        """播放网格波浪式展开动画"""

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
                width=2, color=NeonTheme.COLOR_ELLIPSE, opacity=0.8
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
                    color=NeonTheme.COLOR_GRID, opacity=0.7, width=1.5
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

    def animate_grid_removal(self):
        """播放网格科幻内爆消除动画"""

        # 1. 让背景辅助线黯淡并消失
        self.scene.play(FadeOut(self.grid.background_lines), run_time=0.8)

        # 2. 让主坐标轴从四周往中心极速收缩（逆向展开）
        self.scene.play(Uncreate(self.grid.axes), run_time=0.6, rate_func=smooth)

        # 3. 彻底从场景中移除实体
        self.scene.remove(self.grid)
        self.scene.wait(0.2)

    def get_header(self, title_str: str, formula_str: str) -> VGroup:
        """快速生成统一风格的标题与公式头"""
        title = Text(title_str, weight=BOLD, font_size=40).set_color_by_gradient(
            *NeonTheme.COLOR_TITLE
        )
        formula = MathTex(formula_str, color=NeonTheme.TEXT)
        return VGroup(title, formula).arrange(DOWN, buff=0.4).move_to(ORIGIN)

    def c2p(self, *args, **kwargs):
        """代理方法：将坐标转换为场景坐标"""
        return self.grid.c2p(*args, **kwargs)


# ==========================================
# 4. 片尾一键三连卡片
# ==========================================


class EndingCard:
    """奇点 IP 片尾一键三连卡片（点赞、投币、收藏）"""

    _SVG_DIR = os.path.join(os.path.dirname(__file__), "..", "svg")

    def __init__(self, scene: Scene, exclude_mobjects: list = None):
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
        mobs = []
        for m in self.scene.mobjects:
            if isinstance(m, excluded_types):
                continue
            if m in self.exclude_mobjects:
                continue
            is_visible = True
            has_fill = hasattr(m, "fill_opacity")
            has_stroke = hasattr(m, "stroke_opacity")
            if has_fill or has_stroke:
                fill_op = getattr(m, "fill_opacity", 0)
                stroke_op = getattr(m, "stroke_opacity", 0)
                if (fill_op or 0) < 0.01 and (stroke_op or 0) < 0.01:
                    is_visible = False
            if is_visible:
                mobs.append(m)
        return mobs

    # ── 公共入口 ──────────────────────────────────

    def play_ending(self, mode: str = "A", bilibili_style: bool = True):
        icons = self._build_icons()
        mode = mode.upper()

        if mode == "A":
            self._mode_converge(icons)
        elif mode == "B":
            self._mode_morph(icons)
        elif mode == "C":
            self._mode_assign(icons)

        if bilibili_style:
            self._bilibili_activation(icons)

        self._show_text_and_settle(icons, bilibili_style)

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

    # ── Phase 2: B 站风格点亮 ────────────────────

    def _bilibili_activation(self, icons: VGroup):
        colors = [NeonTheme.BILI_LIKE, NeonTheme.BILI_COIN, NeonTheme.BILI_FAVO]

        for icon, color in zip(icons, colors):
            self.scene.wait(0.08)

            self.scene.play(
                icon.animate.set_fill(color, opacity=1).scale(1.35),
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

    def _show_text_and_settle(self, icons: VGroup, bilibili_style: bool):
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

        final_colors = (
            [NeonTheme.BILI_LIKE, NeonTheme.BILI_COIN, NeonTheme.BILI_FAVO]
            if bilibili_style
            else list(NeonTheme.ENDING_FALLBACK)
        )

        self.scene.play(
            *[
                icon.animate.scale(1.2).set_fill(color, opacity=1)
                for icon, color in zip(icons, final_colors)
            ],
            text.animate.scale(1.05).set_color(final_colors[0]),
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
