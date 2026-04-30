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
            final_mob = target_title

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
class EllipseBase(ThreeDScene):
    """
    科幻网格场景基类。
    继承此类的 Scene 将自动获得深色背景和酷炫的网格展开/消除动画。
    """

    def setup(self):
        # 强制设置背景色
        self.camera.background_color = NeonTheme.BG_COLOR

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

        self.play(
            axes.animate.set_stroke(opacity=1),
            GrowFromCenter(axes),
            run_time=1.0,
            rate_func=rush_from,
        )
        self.play(
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
        self.play(
            LaggedStart(*get_line_anim(v_lines), lag_ratio=0.06),
            LaggedStart(*get_line_anim(h_lines), lag_ratio=0.06),
            run_time=3.0,
        )

        # --- 步骤 4：视觉冲击波 ---
        flash_rect = FullScreenRectangle(
            fill_opacity=0.1, fill_color=WHITE, stroke_width=0
        )
        self.play(FadeIn(flash_rect, run_time=0.1), FadeOut(flash_rect, run_time=0.4))
        self.add(self.grid)
        self.wait(0.5)

    def animate_grid_removal(self):
        """播放网格科幻内爆消除动画"""

        # 1. 让背景辅助线黯淡并消失
        self.play(FadeOut(self.grid.background_lines), run_time=0.8)

        # 2. 让主坐标轴从四周往中心极速收缩（逆向展开）
        self.play(Uncreate(self.grid.axes), run_time=0.6, rate_func=smooth)

        # 3. 彻底从场景中移除实体
        self.remove(self.grid)
        self.wait(0.2)

    def get_header(self, title_str: str, formula_str: str) -> VGroup:
        """快速生成统一风格的标题与公式头"""
        title = Text(title_str, weight=BOLD, font_size=40).set_color_by_gradient(
            *NeonTheme.COLOR_TITLE
        )
        formula = MathTex(formula_str, color=NeonTheme.TEXT)
        return VGroup(title, formula).arrange(DOWN, buff=0.4).move_to(ORIGIN)
