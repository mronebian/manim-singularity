# Module: `manim_singularity.voiceover`

`voiceover` 包是 Manim 的听觉与字幕核心，提供 TTS 语音旁白、背景音乐、音效与字幕的完整方案。

---

## 架构总览

```mermaid
graph TB
    subgraph PUBLIC["对外接口"]
        VO[VoiceOver]
    end

    subgraph CORE["内部核心"]
        AC[AudioCore]
        VM[VoiceManager]
        CTX[AudioContext]
        SUB[SubtitleSystem]
    end

    subgraph EXT["功能扩展"]
        BGM[BGMController]
        SFX[SFXContext]
    end

    subgraph BACKEND["TTS 后端"]
        LOCAL[本地 IndexTTS 服务<br/>local / ssh 一次性批处理]
        EDGE[edge-tts 在线<br/>legacy edge 音色名]
        CACHE[本地 WAV 缓存]
    end

    VO --> CTX
    VO --> VM
    VO --> BGM
    VO --> SFX

    CTX --> AC
    CTX --> SUB

    VM --> LOCAL
    VM -. legacy/edge .-> EDGE
    VM --> CACHE

    AC -->|scene.add_sound| MANIM[(Manim Scene)]
```

---

## 文件结构

```
manim_singularity/
  voiceover/
    __init__.py       # 导出 VoiceOver
    voiceover.py      # VoiceOver（唯一入口）
    core.py           # AudioCore（音频提交）
    subtitles.py      # SubtitleSystem（字幕渲染）
    manager.py        # VoiceManager（TTS+缓存+后端选择）
    presets.py        # 音色预设注册表（voice id→preset/lang）
    synclib.py        # 缓存键 / AST 收集 / local-ssh 批处理
    warm_cli.py       # vo-warm CLI（渲染前预生成）
    context.py        # AudioContext（with 块）
    bgm.py            # BGMController（背景音乐）
    sfx.py            # SFXContext（音效 with 块）
```

---

## 1. `VoiceOver` 类

### `__init__(scene, default_voice="zh-CN-XiaoxiaoNeural", show_subtitles=True, subtitle_kwargs=None)`

- **`scene`**: 当前 Manim `Scene` 实例。
- **`default_voice`**: 默认音色。preset id（`brand`/`brand-clone`/`v2-clone`）→ 本地；
  其它（legacy edge 名）→ 该句走 edge。默认 `brand-clone`。
- **`show_subtitles`**: 是否显示字幕。
- **`subtitle_kwargs`**: 传递给 `SubtitleSystem` 的参数（详见 SubtitleSystem）。

实例化后自动创建子控制器：`vo.bgm`（`BGMController`）

---

### `say_blocking(text, voice=None, offset=0.0, tts_text=None) -> float`

阻塞式解说。播放音频 + 字幕，读完后才继续执行。

| 参数 | 说明 |
|------|------|
| `text` | 字幕显示的文本 |
| `voice` | 临时覆盖音色 |
| `offset` | 播放前延迟（秒） |
| `tts_text` | 实际朗读文本（留空则读 `text`） |

**返回**: 音频时长（秒）。

```python
vo.say_blocking("大家好")
vo.say_blocking("AI", tts_text="人工智能")
```

---

### `context(text, voice=None, offset=0.0, tts_text=None) -> AudioContext`

返回 `with` 块上下文管理器，实现音画自动同步：动画时长 < 语音时长自动补齐等待，> 语音时长正常执行不截断。

```python
with vo.context("画一个完美的圆形"):
    circle = Circle(color=RED)
    self.play(Create(circle), run_time=1.0)
```

---

### `play_with_audio(*animations, text, voice=None, tts_text=None, **kwargs)`

将 `self.play()` 的 `run_time` 锁定为语音时长：

```python
vo.play_with_audio(Create(box), text="这是一个正方形")
```

---

### `sfx(path, volume=1.0, time_offset=0.0) -> SFXContext`

音效的 `with` 块上下文管理器。自动转 WAV，音量通过 FFmpeg 压入文件。

```python
with vo.sfx("explosion.wav", volume=0.8):
    self.play(Flash(center))
```

---

## 2. `AudioCore` 类

统一音频提交层。封装 `scene.add_sound()`，强制绕过 `skip_animations`。

```python
class AudioCore:
    def add_sound(self, path, **kwargs)
```

- `time_offset`: 相对于当前场景时间的偏移（秒），负值表过去时间点。
- `gain`: 音量增益。

---

## 3. `SubtitleSystem` 类

全参数化字幕引擎。通过 `VoiceOver(subtitle_kwargs={...})` 传入。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `font_size` | 32 | 字号 |
| `font` | None | 字体 |
| `color` | None | 单色（与 `gradient` 互斥） |
| `t2c` | None | 逐字着色字典 |
| `gradient` | `("#00E5FF","#0077FF")` | 渐变双色 |
| `position` | `DOWN` | 字幕位置 |
| `buff` | 0.5 | 边距 |
| `entrance_animation` | `Write` | 入场动画类型 |
| `entrance_run_time` | None | 入场时长（None 自动计算 `min(0.6, duration*0.3)`） |
| `exit_animation` | `FadeOut` | 离场动画类型 |
| `exit_run_time` | 0.3 | 离场时长 |
| `exit_shift` | `DOWN * 0.3` | 离场位移方向 |
| `weight` | `BOLD` | 字重 |
| `line_spacing` | 1.2 | 行距 |

```python
vo2 = VoiceOver(self, subtitle_kwargs={
    "font_size": 40,
    "color": "#FFAA00",
    "entrance_run_time": 0.3,
    "exit_shift": DOWN * 0.5,
})
vo2.say_blocking("定制字幕效果")
```

---

## 4. `VoiceManager` 类

TTS 音频生成 + 本地缓存。每段旁白 = 一个缓存 wav。

**后端选择**（`auto` / `local` / `edge`，优先级：逐句 `backend=` > `VoiceOver(backend=)`
> `VO_BACKEND` > auto 启发）：

| voice 值 | auto 启发结果 |
|---|---|
| 本地 preset id（`brand`/`brand-clone`/`v2-clone`）或空 | local（arch/IndexTTS） |
| 其它字符串（legacy edge 音色名） | **edge**（在线 edge-tts，老行为） |

- **流程**: 缓存 miss 时按选定后端生成：
  - `local`：调 `synclib.ensure_task` → local（arch 上 `uv run` 直接合成）或
    ssh（拉起 arch → 传 manifest → 批量合成 → rsync 回传），服务端统一归一化为
    44.1kHz 单声道 PCM WAV。
  - `edge`：edge-tts 生成 MP3 → FFmpeg 转码（legacy 音色名 / 显式 backend=edge）。
- **缓存**:
  - 本地：基于朗读文本 + preset:lang:vCACHE_VERSION 生成 MD5 文件名
    （预生成 `vo-warm` 与运行时共用 `synclib.cache_name`；换品牌参考音后
    `presets.CACHE_VERSION` +1 即可让旧缓存自动失效）。
  - edge：`MD5(speak||voice)`（沿用旧 edge 时代命名，老缓存可直接复用）。
- **tts_text**: 支持字幕文字与朗读文字分离。

### 渲染前自动预热（默认，恢复 edge-tts 时代的"编译即拉取"）

`VoiceOver.__init__` 自动 AST 扫描当前场景 → 缺失的**本地段**整片批量生成（一次模型
加载），之后逐句缓存命中；**edge 段**渲染时逐句实时在线合成（老行为）。无需手动步骤：

```bash
manim -ql Code/euler.py EulerFull        # 构造开始即自动批量补齐；重渲染零网络
VO_AUTO_WARM=0 manim ...                  # 关闭自动预热，改用手动：
vo-warm Code/euler.py                     # arch 本机手动预生成（只预热本地段）
vo-warm Code/euler.py --conn ssh:archlinux # Mac → arch 手动预生成
```

### 音色预设

| voice id | 引擎 | 参考音 | 说明 |
|----------|------|--------|------|
| `brand` | IndexTTS-2.5 | 无 | 无参考快速合成 |
| `brand-clone` | IndexTTS-2.5 | 固定参考（`examples/voice_02.wav`，替换文件即换音色，记得 CACHE_VERSION+1） | 默认，品牌音稳定可复现 |
| `v2-clone` | IndexTTS-2 | 固定参考 | 旧版克隆引擎 |
| `zh-CN-*` / `en-US-*` 等 legacy edge 名 | edge-tts | — | 走 edge，音色即该 edge 音色 |

preset 注册表固定两处：`voiceover/presets.py`（客户端：preset id/语言/后端判定）与
`tts/tools/vo_synth_batch.py`（服务端：引擎/路径）。legacy edge 音色名不再映射本地，
而是真走 edge-tts（可用显式 `backend="local"` 强制本地化）。

---

## 5. `AudioContext` 类

由 `VoiceOver.context()` 返回，内部调用 `AudioCore` 和 `SubtitleSystem`。

- `__enter__`: `AudioCore.add_sound()` 提交音频 → `SubtitleSystem` 创建字幕并入场
- `__exit__`: 补齐剩余时间 → 字幕离场 → 从固定帧移除

---

## 6. `BGMController` 类

背景音乐管理。通过 `vo.bgm` 访问。

| 方法 | 说明 |
|------|------|
| `add(path, loop=False, volume=1.0)` | 添加背景音乐（自动转 WAV） |
| `play()` | 开始或继续播放 |
| `pause()` | 暂停 |
| `stop()` | 停止 |
| `commit()` | 结算所有片段，提交到 scene（必须在 construct() 结束前调用） |

采用**分段记录，延迟提交**方案：play/pause 期间仅记录时间线，commit() 用 FFmpeg 裁切每段后统一提交。

```python
vo.bgm.add("background.mp3", loop=True, volume=0.5)
vo.bgm.play()
# ... scenes ...
vo.bgm.pause()
vo.bgm.play()
# ... scenes ...
vo.bgm.commit()
```

---

## 7. `SFXContext` 类

音效 `with` 块上下文管理器。通过 `vo.sfx()` 创建。

```python
with vo.sfx("explosion.wav", volume=0.8):
    self.play(Flash(center))
```

`with` 块内动画先结束则自动等待音效播完，音效先结束则不阻塞动画。

---

## 完整示例

```python
from manim_singularity import VoiceOver
from manim import *

class DemoScene(Scene):
    def construct(self):
        vo = VoiceOver(self)

        # 语音 + 字幕
        vo.say_blocking("大家好")
        vo.say_blocking("AI", tts_text="人工智能")

        # 音画同步
        with vo.context("画一个圆"):
            self.play(Create(Circle()), run_time=1.0)

        # 锁定时长
        vo.play_with_audio(Create(Square()), text="正方形")

        # 背景音乐
        vo.bgm.add("bgm.mp3", loop=True, volume=0.5)
        vo.bgm.play()
        vo.bgm.commit()

        # 音效 with 块
        with vo.sfx("explosion.wav", volume=0.8):
            self.play(Flash(center))

        # 定制字幕
        vo2 = VoiceOver(self, subtitle_kwargs={
            "font_size": 40,
            "color": "#FFAA00",
            "entrance_run_time": 0.3,
            "exit_shift": DOWN * 0.5,
        })
        vo2.say_blocking("定制字幕效果")
```
