"""背景音乐模块。

Background music module.

提供背景音乐的添加、播放、暂停、停止和提交功能。
采用分段记录、延迟提交的策略，最终通过 FFmpeg 裁切后统一提交到场景。
"""
import hashlib
import os
import subprocess
from typing import Any, Dict, List, Optional

from manim_singularity.compat import Scene, logger, get_scene_time

from .core import AudioCore, get_cache_dir


class BGMTrack:
    """背景音乐轨道。

    Background music track.

    Attributes:
        path: WAV 音频文件路径。
        loop: 是否循环播放。
        volume: 音量倍数。
    """

    def __init__(self, path: str, loop: bool = False, volume: float = 1.0) -> None:
        self.path = path
        self.loop = loop
        self.volume = volume


class BGMController:
    """背景音乐控制器。

    Background music controller.

    采用分段记录、延迟提交策略：
    - play/pause 期间仅记录时间线片段
    - commit() 时用 FFmpeg 裁切每段后统一提交到 scene
    """

    def __init__(self, scene: Scene, audio_core: AudioCore) -> None:
        """初始化背景音乐控制器。

        Initialize the BGM controller.

        Args:
            scene: 当前 Manim Scene 实例。
            audio_core: AudioCore 实例。
        """
        self.scene = scene
        self.audio_core = audio_core
        self._cache_dir = get_cache_dir()
        os.makedirs(self._cache_dir, exist_ok=True)

        self._track: Optional[BGMTrack] = None
        self._bgm_duration: float = 0.0

        self._state: str = "stopped"
        self._audio_offset: float = 0.0
        self._play_start_scene_time: float = 0.0

        self._segments: List[Dict] = []

    def add(self, path: str, loop: bool = False, volume: float = 1.0) -> None:
        """添加背景音乐。

        Add a background music track.

        非 WAV 格式自动转码并缓存。

        Args:
            path: 音频文件路径。
            loop: 是否循环播放。
            volume: 音量倍数，1.0 为原始音量。
        """
        wav_path = self._ensure_wav(path)
        self._track = BGMTrack(wav_path, loop=loop, volume=volume)
        self._bgm_duration = self._probe_duration(wav_path)
        self.stop()
        self._segments.clear()

    def play(self) -> None:
        """开始或继续播放。

        Start or resume playback.

        若已在播放状态则无操作。
        """
        if self._track is None or self._state == "playing":
            return
        self._play_start_scene_time = get_scene_time(self.scene)
        self._state = "playing"

    def pause(self) -> None:
        """暂停播放。

        Pause playback.

        记录当前播放片段到 segments 列表。
        """
        if self._state != "playing":
            return
        current_time = get_scene_time(self.scene)
        duration = current_time - self._play_start_scene_time

        if duration > 0:
            self._segments.append(
                {
                    "track": self._track,
                    "scene_start": self._play_start_scene_time,
                    "duration": duration,
                    "audio_offset": self._audio_offset,
                }
            )

        self._audio_offset += duration
        if not self._track.loop:
            self._audio_offset = min(self._audio_offset, self._bgm_duration)
        self._state = "paused"

    def stop(self) -> None:
        """停止播放并重置偏移。

        Stop playback and reset offset.
        """
        if self._state == "playing":
            self.pause()
        self._audio_offset = 0.0
        self._state = "stopped"

    def commit(self) -> None:
        """结算所有片段并提交到场景。

        Commit all recorded segments to the scene.

        必须在 construct() 结束前调用。
        用 FFmpeg 裁切每段音频后通过 audio_core 提交。
        """
        if self._track is None:
            return
        if self._state == "playing":
            self.pause()
            self._state = "stopped"

        for seg in self._segments:
            track: BGMTrack = seg["track"]
            scene_start: float = seg["scene_start"]
            duration: float = seg["duration"]
            audio_offset: float = seg["audio_offset"]

            if not track.loop and audio_offset >= self._bgm_duration:
                continue
            if not track.loop and (audio_offset + duration) > self._bgm_duration:
                duration = self._bgm_duration - audio_offset
            if duration <= 0:
                continue

            trimmed_path = self._trim_segment(
                track.path, audio_offset, duration, track.loop, track.volume
            )
            self.audio_core.add_sound(
                trimmed_path,
                time_offset=scene_start - get_scene_time(self.scene),
            )
        self._segments.clear()

    def _ensure_wav(self, path: str) -> str:
        """将非 WAV 音频转换为 WAV 格式。

        Convert non-WAV audio to WAV format.

        Args:
            path: 源音频路径。

        Returns:
            WAV 文件路径。
        """
        if path.lower().endswith(".wav"):
            return path
        abs_path = os.path.abspath(path)
        path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
        name = os.path.splitext(os.path.basename(path))[0]
        wav_path = os.path.join(self._cache_dir, f"bgm_{name}_{path_hash}.wav")
        if not os.path.exists(wav_path):
            logger.info(f"🔄 转换 BGM 到 WAV: {os.path.basename(path)}")
            subprocess.run(
                ["ffmpeg", "-y", "-i", path, "-acodec", "pcm_s16le", "-ar", "44100", wav_path],
                check=True, capture_output=True,
            )
        return wav_path

    def _probe_duration(self, path: str) -> float:
        """探测音频时长。

        Probe audio file duration.

        Args:
            path: 音频文件路径。

        Returns:
            时长（秒）。
        """
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            check=True, capture_output=True, text=True,
        )
        return float(result.stdout.strip())

    def _trim_segment(
        self, src: str, offset: float, duration: float, loop: bool, volume: float = 1.0
    ) -> str:
        """裁切并调整音量的音频片段。

        Trim and adjust volume for an audio segment.

        Args:
            src: 源 WAV 文件路径。
            offset: 开始偏移（秒）。
            duration: 片段时长（秒）。
            loop: 是否循环。
            volume: 音量倍数。

        Returns:
            裁切后的 WAV 文件路径。
        """
        key = f"trim_{offset}_{duration}_{loop}_{volume}_{src}"
        h = hashlib.md5(key.encode()).hexdigest()[:12]
        out_path = os.path.join(self._cache_dir, f"{h}.wav")

        if not os.path.exists(out_path):
            cmd = ["ffmpeg", "-y"]
            if loop:
                cmd.extend(["-stream_loop", "-1"])
            cmd.extend(["-i", src])
            cmd.extend(["-ss", str(offset), "-t", str(duration),
                        "-filter:a", f"volume={volume}",
                        "-c:a", "pcm_s16le", out_path])
            subprocess.run(cmd, check=True, capture_output=True)

        return out_path
