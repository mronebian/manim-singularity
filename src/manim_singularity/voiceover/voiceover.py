from typing import Any, Dict, Optional

from manim import Scene

from .bgm import BGMController
from .context import AudioContext
from .core import AudioCore
from .manager import VoiceManager
from .sfx import SFXContext, apply_volume, ensure_wav, probe_duration
from .subtitles import SubtitleSystem


class VoiceOver:
    def __init__(
        self,
        scene: Scene,
        default_voice: str = "zh-CN-XiaoxiaoNeural",
        show_subtitles: bool = True,
        subtitle_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scene = scene
        self.default_voice = default_voice
        self.show_subtitles = show_subtitles
        self.manager = VoiceManager()
        self.audio_core = AudioCore(scene)

        sk = subtitle_kwargs or {}
        self.subtitle_system = SubtitleSystem(scene, **sk)

        self.bgm = BGMController(scene, self.audio_core)

    def say_blocking(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
    ) -> float:
        with self.context(text, voice=voice, offset=offset, tts_text=tts_text) as audio:
            pass
        return audio["duration"]

    def context(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
    ) -> AudioContext:
        target_voice = voice or self.default_voice
        data = self.manager.get_audio_data_sync(text, target_voice, tts_text=tts_text)

        return AudioContext(
            scene=self.scene,
            audio_core=self.audio_core,
            subtitle_system=self.subtitle_system,
            audio_data=data,
            text=text,
            offset=offset,
            show_subtitles=self.show_subtitles,
        )

    def play_with_audio(
        self,
        *animations: Any,
        text: str,
        voice: Optional[str] = None,
        tts_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        with self.context(text, voice=voice, tts_text=tts_text) as audio:
            kwargs.setdefault("run_time", audio["duration"])
            self.scene.play(*animations, **kwargs)

    def sfx(self, path: str, volume: float = 1.0, time_offset: float = 0.0) -> SFXContext:
        wav = ensure_wav(path)
        if volume != 1.0:
            wav = apply_volume(wav, volume)
        duration = probe_duration(wav)
        return SFXContext(self.scene, self.audio_core, wav, duration, time_offset)
