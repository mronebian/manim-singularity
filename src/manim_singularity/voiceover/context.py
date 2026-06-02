"""音画同步上下文管理器。

Audio-visual sync context manager.

在 with 块内自动同步音频播放、字幕显示和动画时长。
"""
from typing import Any, Dict, Optional

from manim import Scene, Text

from .core import AudioCore
from .subtitles import SubtitleSystem


class AudioContext:
    """音画同步上下文管理器。

    Audio-visual sync context manager.

    由 VoiceOver.context() 返回，内部调用 AudioCore 和 SubtitleSystem。
    - __enter__: 提交音频到场景，创建字幕并播放入场动画。
    - __exit__: 补齐剩余时间，字幕离场并从固定帧移除。
    """

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
        """初始化音频上下文。

        Initialize the audio context.

        Args:
            scene: 当前 Manim Scene 实例。
            audio_core: AudioCore 实例。
            subtitle_system: SubtitleSystem 实例。
            audio_data: 语音数据字典（含 path/duration/hash）。
            text: 字幕文本。
            offset: 播放前延迟（秒）。
            show_subtitles: 是否显示字幕。
        """
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
        """进入上下文：提交音频并显示字幕。

        Enter the context: submit audio and display subtitles.

        Returns:
            音频数据字典 {"path", "duration", "hash"}。
        """
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
        """退出上下文：补齐时长并移除字幕。

        Exit the context: wait for remaining time and remove subtitles.

        Args:
            exc_type: 异常类型。
            exc_val: 异常值。
            exc_tb: 异常回溯。

        Returns:
            False，不吞异常。
        """
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
