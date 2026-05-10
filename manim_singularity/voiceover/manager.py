import asyncio
import contextlib
import hashlib
import os
import subprocess
import wave
from typing import Any, Dict, Optional

import edge_tts
from manim import logger

from .core import get_cache_dir


class VoiceManager:
    def __init__(self, cache_dir: str = "") -> None:
        if not cache_dir:
            cache_dir = get_cache_dir()
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_audio_duration(self, file_path: str) -> float:
        with contextlib.closing(wave.open(file_path, "r")) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)

    def get_audio_data_sync(
        self, text: str, voice: str, tts_text: Optional[str] = None
    ) -> Dict[str, Any]:
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
