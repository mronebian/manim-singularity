# 从当前目录的 voiceover.py 文件中引入配音相关的类
from .voiceover import VoiceOver, AudioContext, VoiceManager

# 从当前目录的 theme.py 文件中引入主题相关的类
from .theme import NeonTheme, SingularityIP, EllipseBase

# __all__ 告诉 Python，当别人运行 `from manim_singularity import *` 时，
# 只能导入下面列表里的这些名字（保护内部私有代码不被暴露）
__all__ = [
    "VoiceOver",
    "AudioContext",
    "VoiceManager",
    "NeonTheme",
    "SingularityIP",
    "EllipseBase",
]
