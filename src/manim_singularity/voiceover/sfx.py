"""音效模块。

Sound effects module.

提供音效文件格式转换、音量调整和时长探测功能。
"""
import hashlib
import os
import subprocess

from manim import Scene, logger

from .core import AudioCore, get_cache_dir

_cache_dir = get_cache_dir()


def ensure_wav(path: str) -> str:
    """确保音频文件为 WAV 格式。

    Ensure the audio file is in WAV format.

    非 WAV 文件通过 FFmpeg 自动转码并缓存。

    Args:
        path: 源音频文件路径。

    Returns:
        WAV 文件路径。
    """
    if path.lower().endswith(".wav"):
        return path
    os.makedirs(_cache_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    abs_path = os.path.abspath(path)
    path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
    wav_path = os.path.join(_cache_dir, f"sfx_{name}_{path_hash}.wav")
    if not os.path.exists(wav_path):
        logger.info(f"🔄 转换音效到 WAV: {os.path.basename(path)}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-acodec", "pcm_s16le", "-ar", "44100", wav_path],
            check=True, capture_output=True,
        )
    return wav_path


def apply_volume(path: str, volume: float) -> str:
    """调整音频文件音量。

    Adjust the volume of an audio file.

    通过 FFmpeg 的 volume filter 实现，结果缓存到磁盘。

    Args:
        path: 源 WAV 文件路径。
        volume: 音量倍数，1.0 为原始音量。

    Returns:
        调整音量后的 WAV 文件路径。
    """
    key = f"vol_{volume}_{os.path.abspath(path)}"
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    out = os.path.join(_cache_dir, f"{h}.wav")
    if not os.path.exists(out):
        subprocess.run(
            ["ffmpeg", "-y", "-i", path,
             "-filter:a", f"volume={volume}",
             "-c:a", "pcm_s16le", out],
            check=True, capture_output=True,
        )
    return out


def probe_duration(path: str) -> float:
    """探测音频文件时长。

    Probe the duration of an audio file.

    Args:
        path: 音频文件路径。

    Returns:
        音频时长（秒）。
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


class SFXContext:
    """音效上下文管理器。

    Sound effect context manager.

    在 with 块内播放音效，块结束后自动补齐剩余时长。
    """

    def __init__(
        self,
        scene: Scene,
        audio_core: AudioCore,
        path: str,
        duration: float,
        time_offset: float = 0.0,
    ) -> None:
        """初始化音效上下文。

        Initialize the SFX context.

        Args:
            scene: 当前 Manim Scene 实例。
            audio_core: AudioCore 实例。
            path: 音效 WAV 文件路径。
            duration: 音效时长（秒）。
            time_offset: 播放延迟（秒），负值表示过去时间点。
        """
        self.scene = scene
        self.audio_core = audio_core
        self.path = path
        self.duration = duration
        self.time_offset = time_offset
        self.start_time: float = 0.0

    def __enter__(self) -> "SFXContext":
        """进入上下文：提交音频并记录开始时间。

        Enter the context: submit audio and record start time.

        Returns:
            SFXContext 实例自身。
        """
        self.audio_core.add_sound(self.path, time_offset=self.time_offset)
        self.start_time = self.scene.renderer.time
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """退出上下文：若动画先结束则补齐音效剩余时长。

        Exit the context: wait for remaining audio if animation finishes early.

        Returns:
            False，不吞异常。
        """
        if exc_type is not None:
            return False
        elapsed = self.scene.renderer.time - self.start_time
        remaining = self.duration - elapsed
        if remaining > 0.01:
            self.scene.wait(remaining)
        return False
