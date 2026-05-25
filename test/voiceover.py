# test/voiceover.py
import sys
from pathlib import Path

# 添加上级目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 改为绝对导入
from manim_singularity.voiceover import VoiceOver
from manim import Scene


class SceneWithVoiceover(Scene):
    def construct(self):
        vo = VoiceOver(self)
        with vo.context("hi"):
            self.wait(1)
