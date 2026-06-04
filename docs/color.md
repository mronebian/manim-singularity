# Module: `manim_singularity.color` — ChromaVault

颜色数据库系统，用于持续收藏颜色并灵活组合成不同视觉主题。

**设计理念**：颜色只有一个来源——SQLite 数据库。无内置 seed/fallback，数据库由你手动管理。使用 `chroma init` 创建数据库后通过 CLI 操作。

**零依赖**：`ColorDB` 和 `ColorRecord` 仅用 Python 标准库，`chroma` CLI 和 `color` 颜色库不需要安装 manim。

---

## 架构总览

```mermaid
graph TB
    subgraph USER["用户层"]
        CODE[Manim 脚本]
        CLI[chroma 命令]
    end

    subgraph API["对外接口"]
        CI["color/__init__.py<br/>color.TITLE_COLOR<br/>color.title_gradient()"]
        TOP["manim_singularity/__init__.py<br/>from manim_singularity import color, theme"]
    end

    subgraph CORE["核心层"]
        NT["neon_theme.py<br/>_NeonTheme 单例<br/>_cache + use() + reload()"]
        DB["_db.py<br/>ColorDB<br/>ColorRecord<br/>hex→rgb→hsl→luminance"]
        NT_CACHE["_cache 读缓存"]
        LSP["_theme_names.py<br/>Auto-generated Literal<br/>→ LSP 补全 theme.use()"]
    end

    subgraph MANIM["Manim 适配层"]
        TE["theme/engine.py<br/>Theme 烘焙引擎<br/>17 个显式 ManimColor 属性"]
    end

    subgraph STORE["持久化"]
        SQL[(assets/colors.db<br/>SQLite 5 张表)]
    end

    CODE -->|theme.PRIMARY_FILL_COLOR| CI
    CODE -->|from manim_singularity import theme| TOP
    CLI -->|chroma add list search stats| DB

    TOP -.->|__getattr__ 懒加载| CI
    CI -.->|__getattr__ 委托| NT
    CI -.->|Theme 需 manim| TE

    NT -->|_load 查询| DB
    NT ---> NT_CACHE
    NT -->|use() 参数类型| LSP

    CLI -->|create-theme / delete-theme| DB
    DB -->|建表 增删查| SQL
    CLI -.->|同步主题名| LSP
```

### 调用流程

```
首次使用（数据库已有 Neon 主题）：
  theme.PRIMARY_FILL_COLOR
    → __getattr__ → _NeonTheme.__getattr__
    → _cache 未命中 → _load() 从 DB 加载 "Neon" 主题
    → _cache["PRIMARY_FILL_COLOR"] = "#00E5FF"
    → 返回 "#00E5FF"

第二次：
  _cache 直接命中 → 不碰数据库

切换主题：
  theme.use("Nature")
    → 清空 _cache
    → 设置 _name = "Nature"
    → _load() 从 DB 加载 "Nature" 主题

数据库无当前主题时 → 抛出 AttributeError

theme.reload() → 清空 _cache → 重新 _load()
```

---

## 快速开始

```python
from manim_singularity import theme

circle.set_color(theme.PRIMARY_FILL_COLOR)
title.set_color_by_gradient(*theme.title_gradient())
body.set_color(theme.BODY_TEXT_COLOR)

# 支持多主题切换（LSP 自动补全主题名）
theme.use("Neon")
theme.use("Nature")
```

---

## 1. `color` 颜色库（全局单例，推荐方式）

### 场景色

| 属性 | 默认色值 | 用途 | 对应 Manim 对象 |
|------|---------|------|----------------|
| `color.SCENE_BACKGROUND_COLOR` | `#0D1117` | 场景背景色 | `camera.background_color` |
| `color.SCENE_FLASH_COLOR` | `#FFFFFF` | Flash 闪烁色 | `Flash(color=...)` |

### 网格色

| 属性 | 默认色值 | 用途 | 对应 Manim 对象 |
|------|---------|------|----------------|
| `color.GRID_LINE_COLOR` | `#1A2639` | 网格线色 | `NumberPlane` 背景线 |
| `color.GRID_AXIS_COLOR` | `#FFFFFF` | 坐标轴线色 | `Axes` 坐标轴 |

### 图形填充色

| 属性 | 默认色值 | 用途 | 对应 Manim 对象 |
|------|---------|------|----------------|
| `color.PRIMARY_FILL_COLOR` | `#00E5FF` | 主要图形填充 | 坐标轴、图标点色 |
| `color.ACCENT_FILL_COLOR` | `#FFD700` | 高亮填充色 | 图标动画 |
| `color.ORBIT_STROKE_COLOR` | `#79C0FF` | 轨道描边色 | `Ellipse` 轨道圈 |
| `color.RING_STROKE_COLOR` | `#58A6FF` | 光环描边色 | `Circle` 光环 |
| `color.ICON_FILL_COLOR` | `#FFFFFF` | 图标填充色 | `SVGMobject` |

### 文字色

| 属性 | 默认色值 | 用途 | 对应 Manim 对象 |
|------|---------|------|----------------|
| `color.TITLE_COLOR` | `#00E5FF` | 标题文字色 + 渐变起点 | `Text` 标题 |
| `color.TITLE_GRADIENT_END_COLOR` | `#0077FF` | 标题渐变终点 | `.set_color_by_gradient` |
| `color.INFINITY_COLOR` | `#9B6FBD` | 无穷符号色 / Flash | `MathTex(\infty)` |
| `color.TAGLINE_COLOR` | `#7D3C98` | 标语/副标题色 | 标语 `Text` |
| `color.DECORATIVE_LINE_COLOR` | `#6C3483` | 装饰线色 | `Line` 装饰线 |
| `color.BODY_TEXT_COLOR` | `#E6E6E6` | 正文/公式色 | `MathTex`、正文 |
| `color.MUTED_TEXT_COLOR` | `#8B949E` | 弱化文字色 | 评论、备注 |

### 语义色

| 属性 | 默认色值 | 用途 |
|------|---------|------|
| `color.SUCCESS_COLOR` | `#00FF88` | 成功/正向色 |
| `color.DANGER_COLOR` | `#FF6B6B` | 危险/错误色 |
| `color.WARNING_COLOR` | `#FFD700` | 警告色 |
| `color.INFORMATION_COLOR` | `#58A6FF` | 信息色 |

### 基础色

| 属性 | 默认色值 | 用途 |
|------|---------|------|
| `color.WHITE_COLOR` | `#FFFFFF` | 纯白 |
| `color.BLACK_COLOR` | `#000000` | 纯黑 |

### 便捷方法

```python
theme.title_gradient()      # → ("#00E5FF", "#0077FF") = (TITLE_COLOR, TITLE_GRADIENT_END_COLOR)
theme.reload()              # → 清空缓存重新加载当前主题
theme.use("Neon")           # → 切换到指定主题（LSP 会自动补全数据库中的主题名）
theme.theme_name            # → "Neon"（返回当前主题名）
```

### 使用示例

```python
from manim import Scene, Text, Circle, MathTex, NumberPlane, Flash
from manim_singularity import theme

# 场景
scene.camera.background_color = theme.SCENE_BACKGROUND_COLOR

# 网格
grid = NumberPlane(background_line_style={"stroke_color": theme.GRID_LINE_COLOR})

# 图形
circle = Circle(color=theme.PRIMARY_FILL_COLOR)
orbit = Ellipse(color=theme.ORBIT_STROKE_COLOR)
ring = Circle(color=theme.RING_STROKE_COLOR)
icon = SVGMobject("path.svg").set_fill(theme.ICON_FILL_COLOR)

# 文字
title = Text("标题").set_color_by_gradient(*theme.title_gradient())
infinity = MathTex(r"\infty", color=theme.INFINITY_COLOR)
tagline = Text("Infinity", color=theme.TAGLINE_COLOR)
body = Text("正文", color=theme.BODY_TEXT_COLOR)
muted = Text("备注", color=theme.MUTED_TEXT_COLOR)

# 语义
success = Text("成功", color=theme.SUCCESS_COLOR)
danger = Text("错误", color=theme.DANGER_COLOR)

# 特效
Flash(ORIGIN, color=theme.SCENE_FLASH_COLOR)

# 切换整套配色
theme.use("Neon")
theme.use("Nature")
```

### 角色与 Manim 对象对照

| 角色名（DB） | 属性 | 作用对象 |
|-------------|------|---------|
| `scene_background` | `SCENE_BACKGROUND_COLOR` | `Scene.camera.background_color` |
| `scene_flash` | `SCENE_FLASH_COLOR` | `Flash` |
| `grid_line` | `GRID_LINE_COLOR` | `NumberPlane` 背景线 |
| `grid_axis` | `GRID_AXIS_COLOR` | `Axes` 坐标轴 |
| `primary_fill` | `PRIMARY_FILL_COLOR` | 圆、坐标轴 final、图标点亮 |
| `accent_fill` | `ACCENT_FILL_COLOR` | 图标高亮点亮 |
| `orbit_stroke` | `ORBIT_STROKE_COLOR` | `Ellipse` 轨道 |
| `ring_stroke` | `RING_STROKE_COLOR` | `Circle` 光环 |
| `icon_fill` | `ICON_FILL_COLOR` | `SVGMobject` 图标填充 |
| `title` | `TITLE_COLOR` | `Text` 标题 |
| `title_gradient_end` | `TITLE_GRADIENT_END_COLOR` | `set_color_by_gradient` 终点 |
| `infinity` | `INFINITY_COLOR` | `MathTex(\infty)` + `Flash` |
| `tagline` | `TAGLINE_COLOR` | 标语 `Text` |
| `decorative_line` | `DECORATIVE_LINE_COLOR` | `Line` 装饰线 |
| `body_text` | `BODY_TEXT_COLOR` | `MathTex` 公式、正文 |
| `muted_text` | `MUTED_TEXT_COLOR` | 弱化文字 |
| `success` | `SUCCESS_COLOR` | 正向语义 |
| `danger` | `DANGER_COLOR` | 危险语义 |
| `warning` | `WARNING_COLOR` | 警告语义 |
| `information` | `INFORMATION_COLOR` | 信息语义 |
| `white` | `WHITE_COLOR` | 基础白 |
| `black` | `BLACK_COLOR` | 基础黑 |

---

## 2. `ColorDB` — 数据库核心

SQLite 数据库，默认位置 `<项目根>/assets/colors.db`。

### 构造

```python
from manim_singularity import ColorDB
db = ColorDB()
db = ColorDB("/path/to/custom.db")
```

### 颜色增删查

```python
cid = db.add("primary_fill", "#00E5FF", tags=["强调", "青色系"])
rec = db.get_by_name("primary_fill")
rec.name           # "primary_fill"
rec.hex_code       # "#00E5FF"
rec.rgb            # (0, 229, 255)
rec.hsl            # (186.1, 100.0, 50.0)
rec.wcag_luminance # 0.6326

db.get_by_hex("#00E5FF")
db.all()
db.count()
db.add_tag_to_color("primary_fill", "已使用")
```

### 标签搜索

```python
db.search_by_tags(["强调", "青色系"], match_all=True)
db.search_by_tags(["强调", "青色系"], match_all=False)
```

### 色相搜索

```python
db.search_by_hue_range(180, 220)
db.search_similar("#00E5FF", tolerance=15)
```

### 主题管理

```python
db.create_theme("赛博蓝夜")
db.set_theme_color("赛博蓝夜", "primary_fill", "primary_fill")
db.set_theme_color("赛博蓝夜", "background", "background")

theme_data = db.get_theme("赛博蓝夜")
db.list_themes()
db.close()
```

---

## 3. `ColorRecord` — 颜色数据类

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 自增主键 |
| `name` | `str` | 颜色名称（唯一） |
| `hex_code` | `str` | 色值 |
| `rgb` | `tuple` | RGB 0-255 |
| `hsl` | `tuple` | HSL (h°, s%, l%) |
| `wcag_luminance` | `float` | WCAG 2.0 相对亮度 |

```python
record.to_manim_color()  # → ManimColor
```

---

## 4. `Theme` — 主题烘焙引擎

将 `ColorDB` 主题烘焙为 `ManimColor`。**需要 manim**。

17 个标准化属性，命名与 `color` 颜色库一致：

```python
from manim_singularity import ColorDB, Theme

theme = Theme(db, "赛博蓝夜")

theme.SCENE_BACKGROUND_COLOR         # ManimColor

theme.BODY_TEXT_COLOR
theme.SUCCESS_COLOR

# 全部角色
theme.all()  # → {role: ManimColor}
```

缺少必需角色时构造抛出 `ValueError`。

---

## 5. CLI 命令行

**入口**：`chroma`（需 `pip install -e .` 注册）。零 manim 依赖。

### 初始化

```bash
chroma init                          # 创建默认数据库 assets/colors.db
chroma init --db-path ./my.db        # 创建自定义路径
```

### 自定义数据库路径

所有命令都支持 `--db-path` 参数，或设置 `CHROMA_VAULT_DB_PATH` 环境变量：

```bash
chroma --db-path ./my.db add background "#0D1117"
chroma --db-path ./my.db list

export CHROMA_VAULT_DB_PATH=./my.db
chroma add primary_fill "#00E5FF"
```

### 颜色操作

```bash
chroma add primary_fill "#00E5FF" --tags 强调 青色系
chroma list
chroma search 背景
chroma stats
```

### 主题操作

```bash
chroma create-theme "赛博蓝夜" --desc "暗色科技风"
chroma set-role "Neon" background background
chroma list-themes
```

> `create-theme` 和 `delete-theme` 执行后会自动更新 `_theme_names.py`，
> 使 `theme.use()` 获得 LSP 补全。新增主题后需重启语言服务器：
> - VSCode: `Developer: Reload Window`
> - Neovim: `:LspRestart`

### 删除操作

```bash
chroma delete my_red               # 删除颜色
chroma delete-theme "Neon"          # 删除主题
```

---

## 6. 标签系统

```python
from manim_singularity.color.core.tags import TagCategory, StandardTags

StandardTags.HUE_BLUE     # ("blue", TagCategory.HUE)
StandardTags.MOOD_TECH    # ("tech", TagCategory.MOOD)
StandardTags.all()        # → 全部标准标签
```

---

## 7. 首次设置指南

### 方式 A：分步操作

```bash
# 1. 创建数据库
chroma init

# 2. 添加颜色
chroma add background "#0D1117"
chroma add primary_fill "#00E5FF"

# 3. 创建主题并绑定角色
chroma create-theme "Neon"
chroma set-role "Neon" background background
chroma set-role "Neon" primary_fill primary_fill
# ... 全部 17 个角色
```

### 验证

```python
from manim_singularity import theme
print(theme.PRIMARY_FILL_COLOR)   # → #00E5FF
```

---

## 8. 迁移指南

| 旧 `NeonTheme.X` | 新 `color.X` |
|---|---|
| `BG_COLOR` | `SCENE_BACKGROUND_COLOR` |
| `COLOR_WHITE` | `WHITE_COLOR` |
| `COLOR_ELLIPSE` | `PRIMARY_FILL_COLOR` |
| `COLOR_GRID` | `GRID_LINE_COLOR` |
| `TEXT` | `BODY_TEXT_COLOR` |
| `*COLOR_TITLE` | `*title_gradient()` |

---

## 9. 数据库文件

默认位置：`<项目根>/assets/colors.db`（已 `.gitignore`）。
首次运行自动建库建表，颜色需手动添加。
