from typing import Any, Callable, Optional, Tuple

from manim import BOLD, DOWN, FadeOut, Scene, Text, Write


class SubtitleSystem:
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
        entrance_animation: Callable = Write,
        entrance_run_time: Optional[float] = None,
        exit_animation: Callable = FadeOut,
        exit_run_time: float = 0.3,
        exit_shift: Any = DOWN * 0.3,
        weight: str = BOLD,
        line_spacing: float = 1.2,
        add_fixed_in_frame: bool = True,
    ) -> None:
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

    def create_subtitle(self, text: str) -> Text:
        kwargs = {
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "weight": self.weight,
        }
        if self.font is not None:
            kwargs["font"] = self.font

        mob = Text(text, **kwargs).to_edge(self.position, buff=self.buff)
        mob._is_subtitle = True

        if self.t2c is not None:
            mob.set_color_by_t2c(self.t2c)
        elif self.color is not None:
            mob.set_color(self.color)
        elif self.gradient is not None:
            mob.set_color_by_gradient(*self.gradient)

        return mob

    def play_entrance(self, subtitle: Text, duration: float) -> float:
        if self.entrance_run_time is not None:
            run_time = self.entrance_run_time
        else:
            run_time = min(0.6, duration * 0.3)
        self.scene.play(self.entrance_animation(subtitle), run_time=run_time)
        return run_time

    def play_exit(self, subtitle: Text) -> float:
        self.scene.play(
            self.exit_animation(subtitle, shift=self.exit_shift),
            run_time=self.exit_run_time,
        )
        return self.exit_run_time

    def add_to_scene(self, mob: Text) -> None:
        if self.add_fixed_in_frame and hasattr(self.scene, "add_fixed_in_frame_mobjects"):
            self.scene.add_fixed_in_frame_mobjects(mob)

    def remove_from_scene(self, mob: Text) -> None:
        if self.add_fixed_in_frame and hasattr(self.scene, "remove_fixed_in_frame_mobjects"):
            self.scene.remove_fixed_in_frame_mobjects(mob)
