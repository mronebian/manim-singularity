import hashlib
import os
import subprocess
from typing import Optional, List, Dict

from manim import Scene, logger

from .core import AudioCore, get_cache_dir


class BGMTrack:
    def __init__(self, path: str, loop: bool = False, volume: float = 1.0) -> None:
        self.path = path
        self.loop = loop
        self.volume = volume


class BGMController:
    def __init__(self, scene: Scene, audio_core: AudioCore) -> None:
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
        wav_path = self._ensure_wav(path)
        self._track = BGMTrack(wav_path, loop=loop, volume=volume)
        self._bgm_duration = self._probe_duration(wav_path)
        self.stop()
        self._segments.clear()

    def play(self) -> None:
        if self._track is None or self._state == "playing":
            return
        self._play_start_scene_time = self.scene.renderer.time
        self._state = "playing"

    def pause(self) -> None:
        if self._state != "playing":
            return
        current_time = self.scene.renderer.time
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
        if self._state == "playing":
            self.pause()
        self._audio_offset = 0.0
        self._state = "stopped"

    def commit(self) -> None:
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
                time_offset=scene_start - self.scene.renderer.time,
            )

        self._segments.clear()

    def _ensure_wav(self, path: str) -> str:
        if path.lower().endswith(".wav"):
            return path
        abs_path = os.path.abspath(path)
        path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
        name = os.path.splitext(os.path.basename(path))[0]
        wav_path = os.path.join(self._cache_dir, f"bgm_{name}_{path_hash}.wav")
        if not os.path.exists(wav_path):
            logger.info(f"🔄 转换 BGM 到 WAV: {os.path.basename(path)}")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    path,
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "44100",
                    wav_path,
                ],
                check=True,
                capture_output=True,
            )
        return wav_path

    def _probe_duration(self, path: str) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    def _trim_segment(
        self, src: str, offset: float, duration: float, loop: bool, volume: float = 1.0
    ) -> str:
        key = f"trim_{offset}_{duration}_{loop}_{volume}_{src}"
        h = hashlib.md5(key.encode()).hexdigest()[:12]
        out_path = os.path.join(self._cache_dir, f"{h}.wav")

        if not os.path.exists(out_path):
            cmd = ["ffmpeg", "-y"]

            if loop:
                cmd.extend(["-stream_loop", "-1"])

            cmd.extend(["-i", src])
            cmd.extend(
                [
                    "-ss",
                    str(offset),
                    "-t",
                    str(duration),
                    "-filter:a",
                    f"volume={volume}",
                    "-c:a",
                    "pcm_s16le",
                    out_path,
                ]
            )

            subprocess.run(cmd, check=True, capture_output=True)

        return out_path
