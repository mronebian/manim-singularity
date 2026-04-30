# Module: `manim_singularity.voiceover`

`voiceover` 模块是本库的听觉与字幕核心。它基于微软 `edge-tts` 引擎，为 Manim 提供了高品质的 AI 旁白功能。其内置了完善的本地缓存机制、精确的音画同步算法以及带有“打字机”出场与渐隐下沉特效的字幕系统。

---

## 1. `VoiceOver` 类

**描述**：语音合成与字幕扩展的核心组件。在你的场景中实例化该类后，即可调用各种语音同步方法。

### `__init__(self, scene: Scene, default_voice="zh-CN-XiaoxiaoNeural", show_subtitles=True, subtitle_kwargs=None)`
- **`scene`**: 当前正在渲染的 Manim `Scene` 实例。
- **`default_voice`** (`str`): 默认使用的 Edge-TTS 音色（如 `"zh-CN-YunxiNeural"` 为男声，`"zh-CN-XiaoxiaoNeural"` 为女声）。
- **`show_subtitles`** (`bool`): 是否在画面底部显示字幕。默认开启。
- **`subtitle_kwargs`** (`dict`): 传递给底层 `Text` 对象的格式化参数（如 `font`, `font_size`, `color` 等）。默认带有青蓝色渐变与加粗效果。

---

### `say_blocking(self, text: str, voice=None, offset=0.0, tts_text=None) -> float`
**描述**：阻塞式解说。系统将播放音频并同步显示字幕，直到整句话朗读完毕后才继续执行下一行代码。在此期间画面动画处于暂停状态。

**参数 (Parameters):**
- **`text`** (`str`): 需要显示在字幕上的文本。
- **`voice`** (`str`, 可选): 临时覆盖全局默认音色。
- **`offset`** (`float`, 默认: `0.0`): 语音播放前的延迟时间（秒）。
- **`tts_text`** (`str`, 可选): 实际发送给 TTS 引擎朗读的文本。若不填，则直接朗读 `text`。（适用于字幕写缩写，但配音读全称的场景）。

**返回值 (Returns):**
- `float`: 当前音频的实际总时长（秒）。

**使用示例:**
```python
vo = VoiceOver(self)
# 画面静止，纯解说与字幕特效
vo.say_blocking("大家好，欢迎来到奇点实验室。")
vo.say_blocking("AI", tts_text="人工智能") # 字幕显示 AI，声音读作"人工智能"
```

---

### `context(self, text: str, voice=None, offset=0.0, tts_text=None) -> AudioContext`
**描述**：返回一个用于 `with` 语句的上下文管理器。它是实现**音画无缝同步**的核心魔法。
在该代码块内执行的动画，系统会自动计算时长：
- 若动画时长 **<** 语音时长，系统将自动使用空白占位符补齐剩余时间，等待语音播完。
- 若动画时长 **>** 语音时长，系统将正常执行完动画，保证逻辑不断裂。

**使用示例:**
```python
# 一边解说，一边画圆。即便画圆只需 1 秒，系统也会自动等这句话读完再执行后续代码。
with vo.context("首先，我们在屏幕中央绘制一个完美的圆形。"):
    circle = Circle(color=RED)
    self.play(Create(circle), run_time=1.0)
```

---

### `play_with_audio(self, *args, text: str, voice=None, tts_text=None, **kwargs)`
**描述**：快捷方法。强制将单次 `self.play()` 动画的 `run_time` 锁定为语音的精确时长，使其完美同步结束。

**使用示例:**
```python
box = Square()
# 这个方块的创建速度，将精确等于这句话的朗读时间
vo.play_with_audio(Create(box), text="这是一个正方形。")
```

---

### `force_audio_muxing(self)`
**描述**：**防截断安全锁**。强制打断 Manim 结尾的整体缓存，确保最后一句语音能够被 FFmpeg 完整混流而不被截断。
⚠️ **强烈建议**：在 `Scene.construct()` 方法的最后一行调用此方法。

**使用示例:**
```python
class MyScene(Scene):
    def construct(self):
        vo = VoiceOver(self)
        vo.say_blocking("我们下期再见！")
        
        # 放在代码的绝对末尾
        vo.force_audio_muxing()
```

---

## 2. 内部支撑组件 (Internal Components)

### `AudioContext` 类
由 `VoiceOver.context()` 实例化并返回。
- 负责在 `__enter__` 时播放音频，并触发字幕的 `Write` 出场动画。
- 负责在 `__exit__` 时计算时长差，通过透明 `DecimalNumber` 消耗冗余时间以修复 Manim 缓存 BUG，并执行字幕的 `FadeOut` 下沉离场动画。

### `VoiceManager` 类
负责音频底层管理。
- **本地缓存机制**: 生成的音频会基于 `text + voice` 生成 MD5 哈希值，并保存在项目根目录的 `.voice_cache/` 文件夹中。二次运行相同的文本将直接读取本地 MP3，实现秒级渲染。
- **兼容性设计**: 内部使用 `run_async_safely` 在独立线程中调度 `edge-tts` 的异步方法，完美兼容 Jupyter Notebook 等复杂事件循环环境。
