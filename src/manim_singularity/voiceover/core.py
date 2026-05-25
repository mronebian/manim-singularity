import os

from manim import Scene, config


def get_cache_dir() -> str:
    return os.path.abspath(
        os.path.join(str(config.get_dir("media_dir")), "voice")
    )


class AudioCore:
    def __init__(self, scene: Scene) -> None:
        self.scene = scene

    def add_sound(self, path: str, **kwargs) -> None:
        original_skip = self.scene.renderer.skip_animations
        self.scene.renderer.skip_animations = False
        self.scene.add_sound(path, **kwargs)
        self.scene.renderer.skip_animations = original_skip
