# Module: `manim_singularity.theme`

`theme` 模块提供了奇点 IP 的核心视觉资产，包含预设片头转场引擎（`SingularityIP`）、标准化的科幻网格场景基类（`EllipseBase`）以及片尾三连卡片（`EndingCard`）。

**主题颜色系统由 `manim_singularity.color`（ChromaVault）统一管理**，详见 [`docs/color.md`](color.md)。

所有组件（`SingularityIP`、`EllipseBase`、`EndingCard`）内部使用全局 `theme` 单例，调用 `theme.use("Nature")` 即可切换整套配色。

---

## 1. `SingularityIP` 类

**描述**：厂牌级片头转场引擎。负责生成标准化的开场动画，并支持将核心图形动态平滑地转换为当前视频的正片标题。

### `__init__(self, scene: Scene)`

- **`scene`**: 当前正在渲染的 Manim `Scene` 实例，动画将直接作用于该场景。

### `play_intro(self, target_title=None, *, keep_final=False) -> Optional[Mobject]`

播放完整的片头动画序列（轨道展开 -> 核心闪烁 -> 细节绽放 -> 变形离场）。

**参数 (Parameters):**

- **`target_title`** (`Optional[Mobject]`, 默认: `None`): 目标标题对象。若传入，片头几何体将在尾声变形成该对象，并执行下沉蓄力后向上飞出的转场特效。
- **`keep_final`** (`bool`, 默认: `False`): 仅在 `target_title` 为 `None` 时生效。若设为 `True`，片头 Logo 将保留在画面中央不退出；若设为 `False`，Logo 将自动飞出画面淡出。

**返回值 (Returns):**

- 返回转场结束时留在画面上（或刚刚淡出）的最终 `Mobject`（即 `target_title` 或 Logo 组合），可用于后续的动画接力。

### 使用示例

```python
from manim import Scene, Text
from manim_singularity import SingularityIP, theme

class IntroExample(Scene):
    def construct(self):
        ip = SingularityIP(self)

        # 定义本集专属标题
        chapter_title = Text("第一期：线性代数本质").set_color_by_gradient(
            *theme.title_gradient()
        )

        # 播放片头并自动变身飞出
        ip.play_intro(target_title=chapter_title)
```

---

## 2. `EllipseBase` 类

**描述**：标准科幻网格场景基类，继承自 Manim 的 `ThreeDScene`。任何需要绘制网格、函数的数学演示场景，均应直接继承此类而非基础 `Scene`。

该基类在其生命周期的 `setup()` 阶段，会自动将背景设为 `theme.SCENE_BACKGROUND_COLOR`，并实例化一个标准坐标平面 `self.grid`。

### 属性 (Attributes)

- **`self.grid`** (`NumberPlane`): 覆盖全屏的底层坐标系。你可以直接调用 `self.grid.plot()` 或 `self.grid.c2p()` 进行函数与坐标点绘制。

### `animate_grid_growth(self)`

**描述**：播放网格系统的初始化动画。包含主轴爆发、背景网格线提取及波浪式雷达扫描展开，并在结尾伴随全屏高光冲击波。

- **动画时长**: 约 `5.6` 秒。
- **状态变更**: 执行完毕后，`self.grid` 将正式被添加到场景中。

### `animate_grid_removal(self)`

**描述**：播放网格系统的销毁动画。背景辅助线先行黯淡隐去，随后主轴向中心极速收缩（内爆），用于在视频高潮阶段剥离坐标系束缚。

- **动画时长**: 约 `1.6` 秒。
- **状态变更**: 执行完毕后，`self.grid` 将从场景中被彻底移除（`remove`）。

### `get_header(self, title_str: str, formula_str: str) -> VGroup`

**描述**：快速生成符合规范的顶部说明栏（主标题 + 副公式）。

**参数 (Parameters):**

- **`title_str`** (`str`): 主标题文本。
- **`formula_str`** (`str`): LaTeX 公式字符串。

**返回值 (Returns):**

- `VGroup`: 经过自动排版与着色的组合对象，默认居中于 `ORIGIN`，可使用 `.to_edge(UP)` 移动至屏幕顶部。

### 使用示例

```python
from manim import *
from manim_singularity import EllipseBase

class GridExample(EllipseBase):
    def construct(self):
        # 1. 酷炫展开坐标网格
        self.animate_grid_growth()

        # 2. 生成顶部说明栏并显示
        header = self.get_header("二次函数", "y = x^2").to_edge(UP)
        self.play(Write(header))

        # 3. 使用基类自带的 self.grid 绘制函数曲线
        parabola = self.grid.plot(lambda x: x**2, color=YELLOW)
        self.play(Create(parabola))

        # 4. 剥离网格，使曲线悬浮
        self.animate_grid_removal()

        # 5. 后续处理（例：放大曲线）
        self.play(parabola.animate.scale(1.5))
```

---

## 3. `EndingCard` 类

**描述**：奇点 IP 片尾三连卡片（点赞、投币、收藏图标）。

支持三种场景变换模式（汇聚 A / 变形 B / 分配 C）、图标逐一点亮动画以及文字心跳效果。从 `assets/svg/` 加载 SVG 图标，不存在时自动使用圆形回退。

### `__init__(self, scene, exclude_mobjects=None)`

- `scene`: 当前 Manim Scene。
- `exclude_mobjects`: 变换中要排除的物件列表。

### `play_ending(self, mode="A")`

播放完整片尾动画：场景变换 → 图标点亮 → 文字心跳。

- `mode`: `"A"` 汇聚、`"B"` 变形、`"C"` 分配。
