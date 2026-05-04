import os
import hashlib
import asyncio
import threading
import wave
import contextlib
import subprocess
from typing import Optional, Dict, Any

# 引入 Manim 官方库及组件
from manim import (
    Scene,
    Text,
    DOWN,
    logger,
    FadeOut,
    Write,
    BOLD,
)
import edge_tts


def run_async_safely(coro: Any) -> Any:
    """在独立线程中运行异步任务，防止与事件循环冲突。"""
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
    """管理 TTS 音频生成：edge-tts (MP3) -> FFmpeg (WAV) -> 本地缓存。"""

    def __init__(self, cache_dir: str = ".voice_cache") -> None:
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_audio_duration(self, file_path: str) -> float:
        """使用原生 wave 库获取标准 WAV 文件时长。"""
        with contextlib.closing(wave.open(file_path, "r")) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
            return duration

    def get_audio_data_sync(self, text: str, voice: str) -> Dict[str, Any]:
        """同步获取音频数据，确保最终产出为标准 WAV。"""
        payload = f"{text}||{voice}".encode("utf-8")
        h = hashlib.md5(payload).hexdigest()

        final_wav_path = os.path.join(self.cache_dir, f"{h}.wav")
        temp_mp3_path = os.path.join(self.cache_dir, f"{h}_temp.mp3")

        display_text = text if len(text) <= 20 else text[:17] + "..."

        if h in self._cache:
            return self._cache[h]

        if not os.path.exists(final_wav_path):
            logger.info(f"🎤 正在生成 TTS 并转码: '{display_text}'")

            # 1. 生成 edge-tts 的原始 MP3 文件
            async def _generate() -> None:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_mp3_path)

            run_async_safely(_generate())

            # 2. 调用 FFmpeg 强制转换为标准的 WAV (PCM s16le, 44.1kHz)
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        temp_mp3_path,
                        "-acodec",
                        "pcm_s16le",
                        "-ar",
                        "44100",
                        final_wav_path,
                    ],
                    check=True,
                    capture_output=True,
                )
            except Exception as e:
                logger.error(f"FFmpeg 转码失败 (请检查 Arch 是否安装 ffmpeg): {e}")
                raise e
            finally:
                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)

            logger.info(f"✅ WAV 转码完毕 -> {h}.wav")
        else:
            logger.info(f"⚡ 读取 WAV 缓存: '{display_text}'")

        duration = self.get_audio_duration(final_wav_path)
        result = {"path": final_wav_path, "duration": duration, "hash": h}
        self._cache[h] = result
        return result


class AudioContext:
    """音频与字幕的上下文管理器。"""

    def __init__(
        self,
        scene: Scene,
        voice_over: "VoiceOver",
        audio_data: Dict[str, Any],
        text: str,
        offset: float = 0.0,
        show_subtitles: bool = False,
        subtitle_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scene = scene
        self.voice_over = voice_over
        self.audio_data = audio_data
        self.text = text
        self.offset = offset
        self.show_subtitles = show_subtitles
        self.subtitle_kwargs = subtitle_kwargs or {}

        self.start_time: float = 0.0
        self.duration: float = audio_data["duration"]
        self.subtitle_mob: Optional[Text] = None

    def __enter__(self) -> Dict[str, Any]:
        self.voice_over._force_add_sound(
            self.audio_data["path"], time_offset=self.offset
        )
        self.start_time = self.scene.renderer.time

        if self.show_subtitles and self.text:
            # 针对物理展示优化：默认加粗且颜色更亮眼
            kwargs = {"font_size": 32, "line_spacing": 1.2, "weight": BOLD}
            kwargs.update(self.subtitle_kwargs)
            self.subtitle_mob = Text(self.text, **kwargs).to_edge(DOWN, buff=0.5)
            self.subtitle_mob._is_subtitle = True

            if (
                "color" not in self.subtitle_kwargs
                and "t2c" not in self.subtitle_kwargs
            ):
                # 默认蓝绿色渐变，很有科技感
                self.subtitle_mob.set_color_by_gradient("#00E5FF", "#0077FF")

            if hasattr(self.scene, "add_fixed_in_frame_mobjects"):
                self.scene.add_fixed_in_frame_mobjects(self.subtitle_mob)

            write_time = min(0.6, self.duration * 0.3)
            self.scene.play(Write(self.subtitle_mob), run_time=write_time)

        return self.audio_data

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            return False

        elapsed_time = self.scene.renderer.time - self.start_time
        fade_time = 0.3 if self.subtitle_mob is not None else 0.0
        remaining_time = (self.duration + self.offset) - elapsed_time - fade_time

        if remaining_time > 0.01:
            self.scene.wait(remaining_time)

        if self.subtitle_mob is not None:
            self.scene.play(
                FadeOut(self.subtitle_mob, shift=DOWN * 0.3), run_time=fade_time
            )
        if hasattr(self.scene, "remove_fixed_in_frame_mobjects"):
            self.scene.remove_fixed_in_frame_mobjects(self.subtitle_mob)
        return False


class VoiceOver:
    """Manim 语音合成扩展类。"""

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

    def _force_add_sound(self, path: str, **kwargs: Any) -> None:
        """确保即使在 --preview 模式跳过动画时也能正常注册音频。"""
        original_skip = self.scene.renderer.skip_animations
        self.scene.renderer.skip_animations = False
        self.scene.add_sound(path, **kwargs)
        self.scene.renderer.skip_animations = original_skip

    def say_blocking(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
    ) -> float:
        """纯语音播放，不执行额外动画。"""
        with self.context(text, voice=voice, offset=offset):
            pass
        return list(self.manager._cache.values())[-1]["duration"]

    def context(
        self,
        text: str,
        voice: Optional[str] = None,
        offset: float = 0.0,
    ) -> AudioContext:
        """使用 with 语句在音频持续时间内同步动画。"""
        target_voice = voice or self.default_voice
        data = self.manager.get_audio_data_sync(text, target_voice)

        return AudioContext(
            self.scene,
            self,
            data,
            text=text,
            offset=offset,
            show_subtitles=self.show_subtitles,
            subtitle_kwargs=self.subtitle_kwargs,
        )

    def play_with_audio(
        self,
        *animations: Any,
        text: str,
        voice: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        核心便捷方法：同时执行动画和配音。
        自动将动画的 run_time 设为音频时长。
        """
        with self.context(text, voice=voice) as audio:
            # 自动调整 run_time 以匹配语音
            kwargs.setdefault("run_time", audio["duration"])
            self.scene.play(*animations, **kwargs)
