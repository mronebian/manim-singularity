import hashlib
import os
import subprocess

from manim import Scene, logger

from .core import AudioCore, get_cache_dir


_cache_dir = get_cache_dir()


def ensure_wav(path: str) -> str:
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
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


class SFXContext:
    def __init__(
        self,
        scene: Scene,
        audio_core: AudioCore,
        path: str,
        duration: float,
        time_offset: float = 0.0,
    ) -> None:
        self.scene = scene
        self.audio_core = audio_core
        self.path = path
        self.duration = duration
        self.time_offset = time_offset
        self.start_time: float = 0.0

    def __enter__(self) -> "SFXContext":
        self.audio_core.add_sound(self.path, time_offset=self.time_offset)
        self.start_time = self.scene.renderer.time
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            return False
        elapsed = self.scene.renderer.time - self.start_time
        remaining = self.duration - elapsed
        if remaining > 0.01:
            self.scene.wait(remaining)
        return False
