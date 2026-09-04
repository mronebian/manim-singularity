"""VoiceOver 主接口类。

Main VoiceOver interface class.

提供 TTS 语音旁白、背景音乐、音效和字幕的统一入口。
默认在构造时自动预热当前场景的缺失语音（VO_AUTO_WARM=0 关闭）。

后端选择（auto/local/edge）：逐句 backend= > VoiceOver(backend=) > 环境 VO_BACKEND
> auto 启发（preset 音色→本地；legacy edge 音色名→edge）。
"""
import inspect
import os
import sys
import time
from typing import Any, Dict, Optional

from manim_singularity.compat import Scene, logger

from .bgm import BGMController
from .context import AudioContext
from .core import AudioCore
from .manager import VoiceManager
from .presets import normalize_backend
from .sfx import SFXContext, apply_volume, ensure_wav, probe_duration
from .subtitles import SubtitleSystem
from .synclib import scan_scene, warm


def _scene_source_file(scene: Scene) -> Optional[str]:
    """尽力定位当前渲染的场景源码文件。

    Best-effort resolve of the currently rendered scene source file.
    """
    try:
        mod = inspect.getmodule(type(scene))
        if mod and getattr(mod, "__file__", None):
            path = os.path.abspath(mod.__file__)
            if path.lower().endswith(".py"):
                return path
    except Exception:
        pass
    # 回退：manim CLI 的第二个位置参数通常是场景文件
    for arg in sys.argv[1:]:
        if arg.lower().endswith(".py") and os.path.isfile(arg):
            return os.path.abspath(arg)
    return None


class VoiceOver:
    """语音旁白主接口。

    VoiceOver main interface.

    整合 TTS 生成、音频提交、字幕显示和背景音乐控制。
    使用方式：在 Scene.construct 中实例化后调用 say_blocking / context / play_with_audio。

    Attributes:
        bgm: BGMController 实例，用于控制背景音乐。
    """

    def __init__(
        self,
        scene: Scene,
        default_voice: str = "brand-clone",
        show_subtitles: bool = True,
        subtitle_kwargs: Optional[Dict[str, Any]] = None,
        backend: str = "",
    ) -> None:
        """初始化 VoiceOver。

        Initialize VoiceOver.

        Args:
            scene: 当前 Manim Scene 实例。
            default_voice: 默认音色。preset id（brand/brand-clone/v2-clone）→ 本地；
                其它字符串（legacy edge 音色名）→ 该句走 edge。
            show_subtitles: 是否显示字幕。
            subtitle_kwargs: 传递给 SubtitleSystem 的参数字典。
            backend: 默认引擎 auto/local/edge。空时读环境变量 VO_BACKEND，再缺省 auto。
        """
        self.scene = scene
        self.default_voice = default_voice
        self.show_subtitles = show_subtitles
        self.backend = normalize_backend(backend or os.environ.get("VO_BACKEND", ""))
        self.manager = VoiceManager(backend=self.backend)
        self.audio_core = AudioCore(scene)

        sk = subtitle_kwargs or {}
        self.subtitle_system = SubtitleSystem(scene, **sk)

        self.bgm = BGMController(scene, self.audio_core)

        self._auto_warm()

    def _auto_warm(self) -> None:
        """渲染前自动预热当前场景缺失的本地段语音（默认开启）。

        Auto-warm missing local narration before rendering.

        - 语义对齐旧版"编译即自动拉取"，但只预热本地（IndexTTS）段；
          edge 段渲染时由逐句实时合成（老行为，在线快）。
        - VO_AUTO_WARM=0 关闭；backend=edge（强制全 edge）跳过。
        - 任何异常只告警，不打断渲染。
        """
        if self.manager.backend == "edge":
            return
        if os.environ.get("VO_AUTO_WARM", "1") in ("0", "false", "False"):
            return
        src = _scene_source_file(self.scene)
        if not src:
            logger.warning("VoiceOver: 无法定位场景源码，跳过自动预热")
            return
        start = time.monotonic()
        try:
            tasks, edge_n = scan_scene(src, override_backend=self.manager.backend)
            logger.info(f"🎙 自动预热：定位 {os.path.basename(src)}（backend={self.manager.backend}）")
            extra = f"，edge {edge_n} 段渲染时逐句在线合成" if edge_n else ""
            logger.info(f"🎙 自动预热：扫描到本地 {len(tasks)} 段{extra}")

            def _prog(msg: str) -> None:
                logger.info(f"🎙 {msg}")

            if tasks:
                hit, generated = warm(tasks, self.manager.cache_dir, on_progress=_prog)
                logger.info(
                    f"🎙 自动预热完成：命中 {hit} | 新生成 {generated}"
                    f"（用时 {time.monotonic() - start:.1f}s）"
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"VoiceOver 自动预热失败（不影响渲染）: {e}")

    def say_blocking(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> float:
        """阻塞式语音旁白。

        Blocking voiceover narration.

        播放音频和字幕，读完后才继续执行。

        Args:
            text: 字幕显示的文本。
            voice: 临时覆盖默认音色，为 None 时使用 default_voice。
            offset: 播放前延迟（秒）。
            tts_text: 实际朗读文本。为 None 时朗读 text。
            backend: 逐句引擎覆盖 auto/local/edge（None → 用 VoiceOver 默认）。

        Returns:
            音频时长（秒）。
        """
        with self.context(text, voice=voice, offset=offset, tts_text=tts_text,
                          backend=backend) as audio:
            pass
        return audio["duration"]

    def context(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> AudioContext:
        """返回音画同步上下文管理器。

        Return an audio-visual sync context manager.

        在 with 块内播放音频和字幕，自动补齐时长。
        动画时长 < 语音时长 → 等待补齐。
        动画时长 > 语音时长 → 不截断，正常执行。

        Args:
            text: 字幕显示的文本。
            voice: 临时覆盖音色。
            offset: 播放前延迟（秒）。
            tts_text: 实际朗读文本。
            backend: 逐句引擎覆盖 auto/local/edge（None → 用 VoiceOver 默认）。

        Returns:
            AudioContext 上下文管理器。
        """
        target_voice = voice or self.default_voice
        data = self.manager.get_audio_data_sync(
            text, target_voice, tts_text=tts_text, backend=backend
        )

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
        backend: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """播放动画并将 run_time 锁定为语音时长。

        Play animations with run_time locked to audio duration.

        Args:
            *animations: 要播放的动画。
            text: 字幕文本。
            voice: 临时覆盖音色。
            tts_text: 实际朗读文本。
            backend: 逐句引擎覆盖 auto/local/edge（None → 用 VoiceOver 默认）。
            **kwargs: 传递给 scene.play 的额外参数。
        """
        with self.context(text, voice=voice, tts_text=tts_text, backend=backend) as audio:
            kwargs.setdefault("run_time", audio["duration"])
            self.scene.play(*animations, **kwargs)

    def sfx(self, path: str, volume: float = 1.0, time_offset: float = 0.0) -> SFXContext:
        """创建音效上下文管理器。

        Create a sound effect context manager.

        Args:
            path: 音效文件路径（非 WAV 自动转码）。
            volume: 音量倍数，1.0 为原始音量。
            time_offset: 播放延迟（秒）。

        Returns:
            SFXContext 上下文管理器。
        """
        wav = ensure_wav(path)
        if volume != 1.0:
            wav = apply_volume(wav, volume)
        duration = probe_duration(wav)
        return SFXContext(self.scene, self.audio_core, wav, duration, time_offset)
