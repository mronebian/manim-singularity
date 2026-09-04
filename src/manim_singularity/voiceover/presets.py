"""音色预设注册表（客户端侧）。

Voice preset registry (client side).

voice id → {engine, lang, ref} 的语义在服务端 vo_synth_batch.py 的 PRESETS
固定一版；本表只需要维护：语言推导、缓存键所需的信息，以及旧 edge-tts
音色名的兼容映射。两边 preset id 必须保持一致。
"""

#: 默认品牌音（含固定参考音频，音色稳定、可复现）。
DEFAULT_PRESET = "brand-clone"

#: 服务端支持的 preset id（用于校验与缓存键）。
PRESET_IDS = ("brand", "brand-clone", "v2-clone")

#: preset id → 默认语言。
PRESET_LANG = {
    "brand": "ZH",
    "brand-clone": "ZH",
    "v2-clone": "ZH",
}

#: 旧 edge-tts 音色名前缀 → (preset id, 语言)。仅兜底用（场景已改为新 id）。
LEGACY_PREFIX = {
    "zh-CN": ("brand-clone", "ZH"),
    "zh-TW": ("brand-clone", "ZH"),
    "zh-HK": ("brand-clone", "ZH"),
    "en-US": ("brand-clone", "EN"),
    "en-GB": ("brand-clone", "EN"),
    "ja-JP": ("brand-clone", "JA"),
}


def resolve_voice(voice: str) -> tuple[str, str]:
    """把 voice 字符串解析为 (preset_id, lang)。

    Resolve a voice string into (preset_id, lang).

    - 已知 preset id → 直接用其默认语言
    - 旧 edge 音色名（zh-CN-* 等）→ 兼容映射到品牌音 preset + 推导语言
    - 其它未知值 → 回退到默认 preset（语言按默认）
    """
    if not voice:
        preset = DEFAULT_PRESET
    elif voice in PRESET_LANG:
        preset = voice
    else:
        for prefix, (mapped, _lang) in LEGACY_PREFIX.items():
            if voice.startswith(prefix):
                return mapped, _lang
        preset = DEFAULT_PRESET
    return preset, PRESET_LANG[preset]
