"""TTS 语音管理模块。

TTS voice management module.

提供语音合成、音频缓存和时长探测功能。
使用 edge-tts 生成语音，FFmpeg 转码为 WAV 格式。
"""
import asyncio
import contextlib
import hashlib
import os
import subprocess
import wave
from typing import Any, Dict, Optional

import edge_tts
from manim_singularity.compat import logger

from .core import get_cache_dir


class VoiceManager:
    """TTS 语音管理器。

    TTS voice manager.

    基于 edge-tts 生成语音，通过 FFmpeg 转码为 44.1kHz WAV 格式。
    基于朗读文本 + 音色的 MD5 hash 做磁盘缓存，避免重复生成。
    支持字幕文字与朗读文字分离（tts_text）。
    """

    def __init__(self, cache_dir: str = "") -> None:
        """初始化语音管理器。

        Initialize the voice manager.

        Args:
            cache_dir: 缓存目录路径。为空时使用默认路径 (media_dir/voice)。
        """
        if not cache_dir:
            cache_dir = get_cache_dir()
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
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

        基于朗读文本和音色生成 MD5 缓存键。
        若缓存命中则直接读取，否则调用 edge-tts 生成后转码。

        Args:
            text: 字幕显示的文本。
            voice: Edge-TTS 音色名。
            tts_text: 实际朗读文本。为 None 时朗读 text。

        Returns:
            {"path": WAV 文件路径, "duration": 时长（秒）, "hash": MD5 hash}。
        """
        speak_text = tts_text or text
        payload = f"{speak_text}||{voice}".encode("utf-8")
        h = hashlib.md5(payload).hexdigest()

        final_wav_path = os.path.join(self.cache_dir, f"{h}.wav")
        temp_mp3_path = os.path.join(self.cache_dir, f"{h}_temp.mp3")

        display_text = text if len(text) <= 20 else text[:17] + "..."

        if h in self._cache:
            return self._cache[h]

        if not os.path.exists(final_wav_path):
            logger.info(f"🎤 正在生成 TTS 并转码: '{display_text}'")

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
            except Exception as e:
                logger.error(f"FFmpeg 转码失败 (请检查是否安装 ffmpeg): {e}")
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
