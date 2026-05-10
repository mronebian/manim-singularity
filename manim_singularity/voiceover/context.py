from typing import Any, Dict, Optional

from manim import Scene, Text

from .core import AudioCore
from .subtitles import SubtitleSystem


class AudioContext:
    def __init__(
        self,
        scene: Scene,
        audio_core: AudioCore,
        subtitle_system: SubtitleSystem,
        audio_data: Dict[str, Any],
        text: str,
        offset: float = 0.0,
        show_subtitles: bool = False,
    ) -> None:
        self.scene = scene
        self.audio_core = audio_core
        self.subtitle_system = subtitle_system
        self.audio_data = audio_data
        self.text = text
        self.offset = offset
        self.show_subtitles = show_subtitles

        self.start_time: float = 0.0
        self.duration: float = audio_data["duration"]
        self.subtitle_mob: Optional[Text] = None

    def __enter__(self) -> Dict[str, Any]:
        self.audio_core.add_sound(
            self.audio_data["path"], time_offset=self.offset
        )
        self.start_time = self.scene.renderer.time

        if self.show_subtitles and self.text:
            self.subtitle_mob = self.subtitle_system.create_subtitle(self.text)
            self.subtitle_system.add_to_scene(self.subtitle_mob)
            self.subtitle_system.play_entrance(self.subtitle_mob, self.duration)

        return self.audio_data

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            return False

        elapsed_time = self.scene.renderer.time - self.start_time
        fade_time = self.subtitle_system.exit_run_time if self.subtitle_mob is not None else 0.0
        remaining_time = (self.duration + self.offset) - elapsed_time - fade_time

        if remaining_time > 0.01:
            self.scene.wait(remaining_time)

        if self.subtitle_mob is not None:
            self.subtitle_system.play_exit(self.subtitle_mob)
            self.subtitle_system.remove_from_scene(self.subtitle_mob)

        return False
