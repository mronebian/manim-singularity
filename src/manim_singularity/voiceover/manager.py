"""TTS 语音管理模块。

TTS voice management module.

后端按"逐句 backend= > VoiceOver(backend=) > 环境 VO_BACKEND > auto 启发"选择：
- local：本地 IndexTTS（synclib：local/ssh 一次性批处理；缓存键带 CACHE_VERSION）
- edge：edge-tts 在线合成 + FFmpeg 转码（缓存键沿用旧 edge 时代命名，老缓存可复用）
voice 只选音色（preset id→local；legacy edge 名→edge），backend 只选引擎。
"""
import contextlib
import os
import wave
from typing import Any, Dict, Optional

from manim_singularity.compat import logger

from .core import get_cache_dir
from .presets import (
    DEFAULT_PRESET,
    is_preset,
    normalize_backend,
    preset_lang,
)
from .synclib import cache_name, edge_cache_name, ensure_task


class VoiceManager:
    """TTS 语音管理器。

    TTS voice manager.

    每段旁白 = 一个磁盘 wav。
    - local：MD5(speak||preset:lang:vCACHE_VERSION)（见 synclib）
    - edge：MD5(speak||voice)（旧 edge 命名）
    支持字幕文字与朗读文字分离（tts_text）。
    """

    def __init__(self, cache_dir: str = "", backend: str = "") -> None:
        """初始化语音管理器。

        Initialize the voice manager.

        Args:
            cache_dir: 缓存目录路径。为空时使用默认路径 (media_dir/voice)。
            backend: "auto" | "local" | "edge"。为空时读环境变量 VO_BACKEND，默认 auto。
        """
        if not cache_dir:
            cache_dir = get_cache_dir()
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.backend = normalize_backend(backend or os.environ.get("VO_BACKEND", ""))
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
        self, text: str, voice: str, tts_text: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步获取语音数据（生成或读取缓存）。

        Synchronously get audio data (generate or read from cache).

        Args:
            text: 字幕显示的文本。
            voice: 音色（preset id → local；其它/legacy edge 名 → edge，见 auto 规则）。
            tts_text: 实际朗读文本。为 None 时朗读 text。
            backend: 逐句覆盖后端 (auto/local/edge)。为 None 时用 self.backend。

        Returns:
            {"path": WAV 文件路径, "duration": 时长（秒）, "hash": 缓存键}。
        """
        speak_text = tts_text or text
        eff = normalize_backend(backend or self.backend)
        display_text = text if len(text) <= 20 else text[:17] + "..."

        # --- 决定走 local 还是 edge ---
        if eff == "edge":
            if not voice or is_preset(voice):
                raise RuntimeError(
                    f"VO_BACKEND/backend=edge 需要指定 edge-tts 音色名，"
                    f"但得到 voice={voice!r}；edge 不支持本地 preset id。"
                )
            is_local, preset, lang, edge_name = False, None, None, voice
        elif eff == "local":
            if voice and not is_preset(voice):
                logger.info(f"本地后端：忽略非本地音色名 {voice!r}，使用默认品牌音")
            preset = voice if is_preset(voice) else DEFAULT_PRESET
            lang = preset_lang(preset)
            is_local, edge_name = True, None
        else:  # auto：preset → local；legacy/其它名 → edge
            if voice and not is_preset(voice):
                is_local, preset, lang, edge_name = False, None, None, voice
            else:
                preset = voice if is_preset(voice) else DEFAULT_PRESET
                lang = preset_lang(preset)
                is_local, edge_name = True, None

        if is_local:
            h = cache_name(speak_text, preset, lang).rsplit(".", 1)[0]
            final_wav_path = os.path.join(self.cache_dir, f"{h}.wav")
            task = {
                "out": os.path.basename(final_wav_path),
                "text": speak_text,
                "preset": preset,
                "lang": lang,
            }
            if h not in self._cache and not os.path.isfile(final_wav_path):
                logger.info(f"🎤 本地 TTS 生成中 ({preset}:{lang}): '{display_text}'")
                ensure_task(task, self.cache_dir)
                if not os.path.isfile(final_wav_path):
                    raise RuntimeError(
                        f"TTS 生成失败: '{display_text}'\n"
                        f"  请确认 tts 服务可用，或先运行: vo-warm <scene.py> "
                        f"(缺失: {os.path.basename(final_wav_path)})"
                    )
            elif os.path.isfile(final_wav_path) and h not in self._cache:
                logger.info(f"⚡ 读取 WAV 缓存: '{display_text}'")
        else:
            h = edge_cache_name(speak_text, edge_name).rsplit(".", 1)[0]
            final_wav_path = os.path.join(self.cache_dir, f"{h}.wav")
            if h not in self._cache and not os.path.isfile(final_wav_path):
                logger.info(f"🌐 edge-tts 在线合成 ({edge_name}): '{display_text}'")
                self._generate_edge(speak_text, edge_name, final_wav_path)
            elif os.path.isfile(final_wav_path) and h not in self._cache:
                logger.info(f"⚡ 读取 WAV 缓存: '{display_text}'")

        duration = self.get_audio_duration(final_wav_path)
        result = {"path": final_wav_path, "duration": duration, "hash": h}
        self._cache[h] = result
        return result

    def _generate_edge(self, speak_text: str, voice_name: str, final_wav_path: str) -> None:
        """edge-tts 在线合成 + FFmpeg 转码（legacy edge 音色名）。依赖网络与 ffmpeg。"""
        import asyncio
        import hashlib
        import subprocess

        import edge_tts  # noqa: PLC0415

        h = hashlib.md5(speak_text.encode("utf-8")).hexdigest()
        temp_mp3_path = os.path.join(self.cache_dir, f"{h}_temp.mp3")

        async def _generate() -> None:
            communicate = edge_tts.Communicate(speak_text, voice_name)
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
