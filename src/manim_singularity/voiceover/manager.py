"""TTS 语音管理模块。

TTS voice management module.

提供语音合成、音频缓存和时长探测功能。
默认使用本地 IndexTTS 服务（synclib：local/ssh 一次性批处理），
生成后统一为 44.1kHz WAV（服务端已归一化）。保留 edge-tts 作为
VO_BACKEND=edge 时的回退引擎。
"""
import contextlib
import os
import wave
from typing import Any, Dict, Optional

from manim_singularity.compat import logger

from .core import get_cache_dir
from .presets import resolve_voice
from .synclib import cache_name, ensure_task


class VoiceManager:
    """TTS 语音管理器。

    TTS voice manager.

    每段旁白 = 一个磁盘 wav，文件名 = MD5(speak_text||preset:lang)。
    生成方：
    - VO_BACKEND=local（默认）→ synclib.ensure_task（local/ssh 批处理，模型在 arch）
    - VO_BACKEND=edge → edge-tts 在线合成 + FFmpeg 转码（回退用）
    支持字幕文字与朗读文字分离（tts_text）。
    """

    def __init__(self, cache_dir: str = "", backend: str = "") -> None:
        """初始化语音管理器。

        Initialize the voice manager.

        Args:
            cache_dir: 缓存目录路径。为空时使用默认路径 (media_dir/voice)。
            backend: "local" | "edge"。为空时读环境变量 VO_BACKEND，默认 local。
        """
        if not cache_dir:
            cache_dir = get_cache_dir()
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.backend = backend or os.environ.get("VO_BACKEND", "local")
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_audio_duration(self, file_path: str) -> float:
        """获取 WAV 音频文件时长。

        Get the duration of a WAV audio file.

        Args:
            file_path: WAV 文件路径。

        Returns:
            音频时长（秒）。
        """
        with contextlib.closing(wave.open(file_path, "r")) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)

    def get_audio_data_sync(
        self, text: str, voice: str, tts_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步获取语音数据（生成或读取缓存）。

        Synchronously get audio data (generate or read from cache).

        Args:
            text: 字幕显示的文本。
            voice: 音色（preset id 或旧 edge 音色名，见 presets.resolve_voice）。
            tts_text: 实际朗读文本。为 None 时朗读 text。

        Returns:
            {"path": WAV 文件路径, "duration": 时长（秒）, "hash": 缓存键}。
        """
        speak_text = tts_text or text
        preset, lang = resolve_voice(voice)
        h = cache_name(speak_text, preset, lang).rsplit(".", 1)[0]
        final_wav_path = os.path.join(self.cache_dir, f"{h}.wav")

        display_text = text if len(text) <= 20 else text[:17] + "..."

        if h in self._cache:
            return self._cache[h]

        if not os.path.exists(final_wav_path):
            logger.info(f"🎤 本地 TTS 生成中 ({preset}:{lang}): '{display_text}'")
            task = {
                "out": os.path.basename(final_wav_path),
                "text": speak_text,
                "preset": preset,
                "lang": lang,
            }
            if self.backend == "edge":
                self._generate_edge(speak_text, voice, final_wav_path)
            else:
                ensure_task(task, self.cache_dir)
            if not os.path.isfile(final_wav_path):
                raise RuntimeError(
                    f"TTS 生成失败: '{display_text}'\n"
                    f"  请先在场景所在目录运行预生成: vo-warm <scene.py> "
                    f"(缺失: {os.path.basename(final_wav_path)})"
                )
        else:
            logger.info(f"⚡ 读取 WAV 缓存: '{display_text}'")

        duration = self.get_audio_duration(final_wav_path)
        result = {"path": final_wav_path, "duration": duration, "hash": h}
        self._cache[h] = result
        return result

    def _generate_edge(self, speak_text: str, voice: str, final_wav_path: str) -> None:
        """edge-tts 回退合成（VO_BACKEND=edge）。依赖 edge-tts + ffmpeg。

        Fallback edge-tts synthesis (VO_BACKEND=edge). Needs edge-tts + ffmpeg.
        """
        import asyncio
        import hashlib
        import subprocess

        import edge_tts  # noqa: PLC0415

        h = hashlib.md5(speak_text.encode("utf-8")).hexdigest()
        temp_mp3_path = os.path.join(self.cache_dir, f"{h}_temp.mp3")

        async def _generate() -> None:
            communicate = edge_tts.Communicate(speak_text, voice)
            await communicate.save(temp_mp3_path)

        asyncio.run(_generate())
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", temp_mp3_path,
                 "-acodec", "pcm_s16le", "-ar", "44100", final_wav_path],
                check=True, capture_output=True,
            )
        finally:
            if os.path.exists(temp_mp3_path):
                os.remove(temp_mp3_path)
