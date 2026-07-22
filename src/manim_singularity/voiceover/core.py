"""音频核心模块。

Audio core module.

提供音频文件缓存目录和底层音频提交功能。
"""
import os

from manim_singularity.compat import Scene, get_media_dir, get_skip_animations, set_skip_animations, add_sound as _add_sound


def get_cache_dir() -> str:
    """获取语音缓存目录路径。

    Get the voice cache directory path.

    Returns:
        以 media_dir 为基础的子目录 "voice" 的绝对路径。
    """
    return os.path.abspath(
        os.path.join(get_media_dir(), "voice")
    )


class AudioCore:
    """统一音频提交层。

    Unified audio submission layer.

    封装 scene.add_sound，强制绕过 skip_animations 确保音频始终播放。
    """

    def __init__(self, scene: Scene) -> None:
        """初始化音频核心。

        Initialize the audio core.

        Args:
            scene: 当前 Manim Scene 实例。
        """
        self.scene = scene

    def add_sound(self, path: str, **kwargs: float) -> None:
        """提交音频到场景。

        Submit audio to the scene.

        临时关闭 skip_animations，确保音频在渲染时始终被播放。

        Args:
            path: 音频文件路径。
            **kwargs: 传递给 scene.add_sound 的额外参数，
                如 time_offset（相对于当前场景时间的偏移）、gain（音量增益）。
        """
        original_skip = get_skip_animations(self.scene)
        set_skip_animations(self.scene, False)
        _add_sound(self.scene, path, **kwargs)
        set_skip_animations(self.scene, original_skip)
