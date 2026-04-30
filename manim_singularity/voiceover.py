import os
import hashlib
import asyncio
import threading
import random
from typing import Optional, Dict, Any

from mutagen.mp3 import MP3

# 引入 Manim 官方库及组件 (新增了 Write, FadeOut, BOLD, UP 等必需组件)
from manim import (
    Scene,
    Text,
    DOWN,
    UP,
    logger,
    DecimalNumber,
    FadeIn,
    FadeOut,
    Write,
    BOLD,
)
import edge_tts


def run_async_safely(coro: Any) -> Any:
    """在独立线程中运行异步任务，防止与 Jupyter 或现有的事件循环冲突。"""
    result = []
    exception = []

    def worker() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result.append(loop.run_until_complete(coro))
        except Exception as e:
            exception.append(e)
        finally:
            loop.close()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    if exception:
        raise exception[0]
    return result[0]


class VoiceManager:
    """管理 TTS 音频的生成与本地缓存。"""

    def __init__(self, cache_dir: str = ".voice_cache") -> None:
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_audio_data_sync(self, text: str, voice: str) -> Dict[str, Any]:
        """同步获取音频数据。若缓存不存在，则调用 edge-tts 生成。"""
        payload = f"{text}||{voice}".encode("utf-8")
        h = hashlib.md5(payload).hexdigest()
        audio_path = os.path.join(self.cache_dir, f"{h}.mp3")

        display_text = text if len(text) <= 20 else text[:17] + "..."

        if h in self._cache:
            return self._cache[h]

        if not os.path.exists(audio_path):
            logger.info(f"🎤 正在生成 TTS 语音: '{display_text}' (Voice: {voice})")

            async def _generate() -> None:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(audio_path)

            run_async_safely(_generate())
            logger.info(f"✅ 语音生成完毕 -> {h}.mp3")
        else:
            logger.info(f"⚡ 读取 TTS 缓存: '{display_text}'")

        audio_info = MP3(audio_path)
        duration = float(audio_info.info.length)

        result = {"path": audio_path, "duration": duration, "hash": h}
        self._cache[h] = result
        return result


class AudioContext:
    """
    音频与字幕的上下文管理器。
    用于在 `with` 语句块中自动同步动画与语音时长，并管理字幕生命周期。
    """

    def __init__(
        self,
        scene: Scene,
        audio_data: Dict[str, Any],
        text: str,
        offset: float = 0.0,
        show_subtitles: bool = False,
        subtitle_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scene = scene
        self.audio_data = audio_data
        self.text = text
        self.offset = offset
        self.show_subtitles = show_subtitles
        self.subtitle_kwargs = subtitle_kwargs or {}

        self.start_time: float = 0.0
        self.duration: float = audio_data["duration"]
        self.subtitle_mob: Optional[Text] = None

    def __enter__(self) -> Dict[str, Any]:
        # 强制添加声音
        self.scene.add_sound(self.audio_data["path"], time_offset=self.offset)
        # 记录此时的声音开始时间（必须在播放出场动画前记录）
        self.start_time = self.scene.renderer.time

        if self.show_subtitles and self.text:
            # 优化字幕样式：稍微大一点、加粗
            kwargs = {"font_size": 28, "line_spacing": 1.2, "weight": BOLD}
            kwargs.update(self.subtitle_kwargs)
            self.subtitle_mob = Text(self.text, **kwargs).to_edge(DOWN, buff=0.5)

            # 添加赛博朋克渐变色（如果 kwargs 里没覆盖设定的话）
            if (
                "color" not in self.subtitle_kwargs
                and "t2c" not in self.subtitle_kwargs
            ):
                self.subtitle_mob.set_color_by_gradient("#00E5FF", "#0077FF")

            # 写字动画出场：控制在总音频长度的30%以内，且最长不超过0.6秒
            write_time = min(0.6, self.duration * 0.3)
            self.scene.play(Write(self.subtitle_mob), run_time=write_time)

            # 如果你的 Manim 环境支持发光特效，可以取消下面这行的注释
            # self.scene.play(self.subtitle_mob.animate.set_glow(0.3), run_time=0.2)

        return self.audio_data

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            return False

        elapsed_time = self.scene.renderer.time - self.start_time

        # 为退场动画预留 0.3 秒的时间
        fade_time = 0.3 if self.subtitle_mob is not None else 0.0
        remaining_time = (self.duration + self.offset) - elapsed_time - fade_time

        # 如果动画比语音短，等待补齐时间 (用隐形数字防止缓存BUG)
        if remaining_time > 0:
            dummy_tracker = DecimalNumber(random.random()).set_opacity(0)
            self.scene.add(dummy_tracker)
            self.scene.play(
                dummy_tracker.animate.set_value(random.random()),
                run_time=remaining_time,
            )
            self.scene.remove(dummy_tracker)

        # 移除字幕：优雅地下沉淡出
        if self.subtitle_mob is not None:
            self.scene.play(
                FadeOut(self.subtitle_mob, shift=DOWN * 0.3), run_time=fade_time
            )

        return False


class VoiceOver:
    """
    Manim 的语音合成扩展组件。
    提供阻塞播放、上下文同步、自动时长匹配三种模式，并内置炫酷动画字幕支持。
    """

    def __init__(
        self,
        scene: Scene,
        default_voice: str = "zh-CN-XiaoxiaoNeural",
        show_subtitles: bool = True,
        subtitle_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scene = scene
        self.default_voice = default_voice
        self.manager = VoiceManager()
        self.show_subtitles = show_subtitles
        self.subtitle_kwargs = subtitle_kwargs or {}

    def force_audio_muxing(self) -> None:
        """
        强制打断结尾的整体缓存，确保全量命中时 FFmpeg 依然进行音视频混流，
        同时附带缓冲等待以防最后一句语音被 FFmpeg 截断。
        """
        dummy = DecimalNumber(random.random()).set_opacity(0)
        self.scene.play(
            dummy.animate.set_value(random.random()), run_time=0.5  # 提供0.5秒缓冲保底
        )
        self.scene.remove(dummy)

    def say_blocking(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
    ) -> float:
        target_voice = voice or self.default_voice
        actual_spoken_text = tts_text if tts_text is not None else text
        data = self.manager.get_audio_data_sync(actual_spoken_text, target_voice)

        if offset > 0:
            self.scene.wait(offset)

        self.scene.add_sound(data["path"])

        subtitle_mob = None
        write_time = 0.0
        fade_time = 0.3 if (self.show_subtitles and text) else 0.0

        if self.show_subtitles and text:
            kwargs = {"font_size": 28, "weight": BOLD}
            kwargs.update(self.subtitle_kwargs)
            subtitle_mob = Text(text, **kwargs).to_edge(DOWN, buff=0.5)

            if (
                "color" not in self.subtitle_kwargs
                and "t2c" not in self.subtitle_kwargs
            ):
                subtitle_mob.set_color_by_gradient("#00E5FF", "#0077FF")

            write_time = min(0.6, data["duration"] * 0.3)
            self.scene.play(Write(subtitle_mob), run_time=write_time)

        # 补齐剩余音频时间
        remaining = data["duration"] - write_time - fade_time
        if remaining > 0:
            dummy_tracker = DecimalNumber(random.random()).set_opacity(0)
            self.scene.add(dummy_tracker)
            self.scene.play(
                dummy_tracker.animate.set_value(random.random()), run_time=remaining
            )
            self.scene.remove(dummy_tracker)

        # 优雅下沉淡出
        if subtitle_mob:
            self.scene.play(FadeOut(subtitle_mob, shift=DOWN * 0.3), run_time=fade_time)

        return data["duration"]

    def context(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
        tts_text: Optional[str] = None,
    ) -> AudioContext:
        target_voice = voice or self.default_voice
        actual_spoken_text = tts_text if tts_text is not None else text
        data = self.manager.get_audio_data_sync(actual_spoken_text, target_voice)

        return AudioContext(
            self.scene,
            data,
            text=text,
            offset=offset,
            show_subtitles=self.show_subtitles,
            subtitle_kwargs=self.subtitle_kwargs,
        )

    def play_with_audio(
        self,
        *args: Any,
        text: str,
        voice: Optional[str] = None,
        tts_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        with self.context(text, voice, tts_text=tts_text) as audio:
            kwargs["run_time"] = audio["duration"]
            self.scene.play(*args, **kwargs)
