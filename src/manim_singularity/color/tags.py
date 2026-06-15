"""标签分类枚举与标准标签常量。

Tag category enumeration and standard tag constants.

用于 color 数据库的颜色标签分类系统。
"""
from enum import Enum, auto


class TagCategory(Enum):
    """标签类别枚举，共 7 类"""
    HUE = auto()          # 色相（red / blue / green ...）
    LIGHTNESS = auto()     # 明度（dark / bright / ...）
    SATURATION = auto()    # 饱和度（muted / vivid / ...）
    MOOD = auto()          # 情感风格（tech / retro / nature ...）
    USAGE = auto()         # 用途（background / text / accent ...）
    SOURCE = auto()        # 来源（Neon / custom ...）
    CUSTOM = auto()        # 自定义（用户自由输入）


class StandardTags:
    """
    标准标签常量，每条为 (name, category) 元组。
    按类别分组，方便 IDE 补全和一致性引用。
    """

    # ── 色相组 ──
    HUE_RED = ("red", TagCategory.HUE)
    HUE_ORANGE = ("orange", TagCategory.HUE)
    HUE_YELLOW = ("yellow", TagCategory.HUE)
    HUE_GREEN = ("green", TagCategory.HUE)
    HUE_CYAN = ("cyan", TagCategory.HUE)
    HUE_BLUE = ("blue", TagCategory.HUE)
    HUE_PURPLE = ("purple", TagCategory.HUE)
    HUE_PINK = ("pink", TagCategory.HUE)
    HUE_NEUTRAL = ("neutral", TagCategory.HUE)

    # ── 明度组 ──
    LIGHT_DARKEST = ("darkest", TagCategory.LIGHTNESS)
    LIGHT_DARK = ("dark", TagCategory.LIGHTNESS)
    LIGHT_MEDIUM = ("medium", TagCategory.LIGHTNESS)
    LIGHT_BRIGHT = ("bright", TagCategory.LIGHTNESS)
    LIGHT_BRIGHTEST = ("brightest", TagCategory.LIGHTNESS)

    # ── 饱和度组 ──
    SAT_MUTED = ("muted", TagCategory.SATURATION)
    SAT_MODERATE = ("moderate", TagCategory.SATURATION)
    SAT_VIVID = ("vivid", TagCategory.SATURATION)

    # ── 情感组 ──
    MOOD_COLD = ("cold", TagCategory.MOOD)
    MOOD_WARM = ("warm", TagCategory.MOOD)
    MOOD_TECH = ("tech", TagCategory.MOOD)
    MOOD_RETRO = ("retro", TagCategory.MOOD)
    MOOD_NATURE = ("nature", TagCategory.MOOD)
    MOOD_SOFT = ("soft", TagCategory.MOOD)
    MOOD_AGGRESSIVE = ("aggressive", TagCategory.MOOD)
    MOOD_PROFESSIONAL = ("professional", TagCategory.MOOD)

    # ── 用途组 ──
    USE_BACKGROUND = ("background", TagCategory.USAGE)
    USE_SURFACE = ("surface", TagCategory.USAGE)
    USE_TEXT = ("text", TagCategory.USAGE)
    USE_ACCENT = ("accent", TagCategory.USAGE)
    USE_DATA = ("data", TagCategory.USAGE)
    USE_GLOW = ("glow", TagCategory.USAGE)
    USE_GRADIENT = ("gradient", TagCategory.USAGE)

    @classmethod
    def all(cls) -> list[tuple[str, TagCategory]]:
        """
        反射收集所有 (name, category) 标准标签。
        过滤条件：类型为 tuple，长度为 2，第二个元素是 TagCategory 实例。
        """
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, tuple) and len(v) == 2 and isinstance(v[1], TagCategory)
        ]
