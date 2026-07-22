import importlib.util
import os
import sys

_ce = importlib.util.find_spec("manim")
_gl = importlib.util.find_spec("manimlib")


def _which():
    if 'manimlib' in sys.modules:
        return 'gl'
    if 'manim' in sys.modules:
        return 'ce'
    if _gl and not _ce:
        return 'gl'
    if _ce:
        return 'ce'
    raise ImportError("Neither ManimCE nor ManimGL found")


if _which() == 'gl':
    IS_MANIM_GL = True

    from manimlib import Scene
    from manimlib.mobject.svg.text_mobject import Text
    from manimlib.mobject.svg.tex_mobject import Tex
    from manimlib.mobject.types.vectorized_mobject import VGroup
    from manimlib.animation.fading import FadeIn, FadeOut
    from manimlib.constants import DOWN, RIGHT
    from manimlib.logger import log as logger

    MathTex = Tex
    BOLD = "bold"

    def get_media_dir():
        return str(os.path.join(os.getcwd(), "media"))

    def get_scene_time(scene):
        return scene.time

    def set_skip_animations(scene, v):
        scene.skip_animations = v

    def get_skip_animations(scene):
        return scene.skip_animations

    def add_sound(scene, path, time_offset=0, gain=None, gain_to_background=None):
        kwargs = {}
        if gain is not None:
            kwargs["gain"] = gain
        if gain_to_background is not None:
            kwargs["gain_to_background"] = gain_to_background
        scene.add_sound(path, time_offset=time_offset, **kwargs)

    def fix_in_frame(mob):
        mob.fix_in_frame()
        mob.z_index = 100

    def unfix_from_frame(mob):
        mob.unfix_from_frame()

    def set_color_by_t2c(mob, t2c):
        mob.set_color_by_tex_to_color_map(t2c)

else:
    IS_MANIM_GL = False

    from manim import Scene, Text, config, logger
    from manim import MathTex, VGroup, FadeIn, FadeOut
    from manim import DOWN, RIGHT
    BOLD = "bold"

    def get_media_dir():
        return str(config.get_dir("media_dir"))

    def get_scene_time(scene):
        return scene.renderer.time

    def set_skip_animations(scene, v):
        scene.renderer.skip_animations = v

    def get_skip_animations(scene):
        return scene.renderer.skip_animations

    def add_sound(scene, path, time_offset=0, gain=None, gain_to_background=None):
        scene.add_sound(path, time_offset=time_offset, gain=gain, gain_to_background=gain_to_background)

    def fix_in_frame(mob):
        pass

    def unfix_from_frame(mob):
        pass

    def set_color_by_t2c(mob, t2c):
        mob.set_color_by_t2c(t2c)
