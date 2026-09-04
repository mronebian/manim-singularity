"""音色 / 后端选择注册表（客户端侧）。

Voice & backend registry (client side).

语义：
- voice 只选"音色身份"：
    * 本地 preset id（brand / brand-clone / v2-clone）或空 → 本地 IndexTTS（arch）
    * 其它字符串（旧 edge-tts 音色名，如 zh-CN-XiaoxiaoNeural）→ edge-tts 在线合成
- backend 只选"引擎"（auto/local/edge），与 voice 互不干扰：
    优先级 逐句 backend= > VoiceOver(backend=) > 环境 VO_BACKEND > auto 启发

引擎语义与 preset 的服务端实现固定于 tts 仓库 tools/vo_synth_batch.py；本表只维护
客户端所需：preset id、默认语言、缓存版本、判定函数。
"""
from __future__ import annotations

#: 默认品牌音（含固定参考音频，音色稳定、可复现）。
DEFAULT_PRESET = "brand-clone"

#: 缓存键版本。更换服务端 REF_AUDIO（品牌参考音）后 +1，让旧缓存自动失效。
CACHE_VERSION = 1

#: 服务端支持的本地 preset id。
PRESET_IDS = ("brand", "brand-clone", "v2-clone")

#: preset id → 默认语言。
PRESET_LANG = {
    "brand": "ZH",
    "brand-clone": "ZH",
    "v2-clone": "ZH",
}

#: 可用后端。
BACKENDS = ("auto", "local", "edge")

DEFAULT_LANG = "ZH"


def is_preset(voice: str) -> bool:
    """voice 是否为本地 IndexTTS preset id。"""
    return voice in PRESET_IDS


def preset_lang(voice: str) -> str:
    """preset 默认语言（非 preset 返回 DEFAULT_LANG）。"""
    return PRESET_LANG.get(voice, DEFAULT_LANG)


def default_preset_lang() -> tuple[str, str]:
    """默认 (preset, lang)。"""
    return DEFAULT_PRESET, DEFAULT_LANG


def normalize_backend(backend: str) -> str:
    """把 backend 归一化为 auto/local/edge 之一。"""
    b = (backend or "").strip().lower()
    return b if b in BACKENDS else "auto"
