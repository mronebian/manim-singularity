import colorsys
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """将十六进制色值转换为 RGB 分量。

    Convert a hex color code to RGB components.

    Args:
        hex_code: 十六进制色值，可选前置 #，如 "#00E5FF" 或 "00E5FF"。

    Returns:
        (r, g, b) 元组，每个分量 0-255。
    """
    hex_code = hex_code.lstrip("#")
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """将 RGB 分量转换为 HSL。

    Convert RGB components to HSL.

    使用 colorsys.rgb_to_hls 计算。
    注意 colorsys 返回 (h, l, s)，本函数重排为 (h, s, l) 并量化为 ° 和 %。

    Args:
        r: 红色分量 0-255。
        g: 绿色分量 0-255。
        b: 蓝色分量 0-255。

    Returns:
        (h, s, l) 元组，h 为 0-360°，s 和 l 为 0-100%。
    """
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h * 360, s * 100, l * 100


def wcag_luminance(r: int, g: int, b: int) -> float:
    """计算 WCAG 2.0 相对亮度。

    Calculate WCAG 2.0 relative luminance.

    sRGB 线性化分段函数：
      - c ≤ 0.03928 时：线性 c / 12.92
      - 否则：((c + 0.055) / 1.055) ^ 2.4
    最终公式：0.2126R + 0.7152G + 0.0722B

    Args:
        r: 红色分量 0-255。
        g: 绿色分量 0-255。
        b: 蓝色分量 0-255。

    Returns:
        WCAG 2.0 相对亮度值，范围 0-1。
    """
    def linearize(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


@dataclass
class ColorRecord:
    """颜色记录数据类。

    Color record dataclass.

    存储一条颜色的所有预计算字段（RGB、HSL、WCAG 亮度）。
    提供便捷属性 rgb / hsl 以及 to_manim_color 方法。

    Attributes:
        id: 数据库自增主键。
        name: 颜色名称，在 colors 表中唯一。
        hex_code: 十六进制色值，含 # 前缀。
        rgb_r, rgb_g, rgb_b: RGB 分量 0-255。
        hsl_h, hsl_s, hsl_l: HSL 分量（h: 0-360°, s/l: 0-100%）。
        wcag_luminance: WCAG 2.0 相对亮度。
        source: 来源描述，可选。
        source_url: 来源链接，可选。
        notes: 备注，可选。
        created_date: 创建时间 ISO 格式字符串。
    """

    id: int
    name: str
    hex_code: str
    rgb_r: int
    rgb_g: int
    rgb_b: int
    hsl_h: float
    hsl_s: float
    hsl_l: float
    wcag_luminance: float
    source: Optional[str] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def rgb(self) -> tuple[int, int, int]:
        """返回 (r, g, b) 分量元组。

        Returns the (r, g, b) component tuple.

        Returns:
            (r, g, b) 元组，每个分量 0-255。
        """
        return (self.rgb_r, self.rgb_g, self.rgb_b)

    @property
    def hsl(self) -> tuple[float, float, float]:
        """返回 (h, s, l) 分量元组。

        Returns the (h, s, l) component tuple.

        Returns:
            (h, s, l) 元组，h: 0-360°, s/l: 0-100%。
        """
        return (self.hsl_h, self.hsl_s, self.hsl_l)

    def to_manim_color(self) -> "ManimColor":
        """将 hex_code 转换为 ManimColor 对象。

        Convert hex_code to a ManimColor object.

        使用懒导入避免 _db.py 直接依赖 manim。

        Returns:
            ManimColor 实例。
        """
        from manim import ManimColor

        return ManimColor(self.hex_code)


class ColorDB:
    """SQLite 颜色数据库核心。

    SQLite color database core.

    零外部依赖，仅用 Python 标准库（sqlite3 + colorsys）。
    管理 5 张表：colors、tags、color_tags、themes、theme_colors。

    默认数据库路径：<项目根>/assets/colors.db，可通过 db_path 参数自定义。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """初始化数据库连接。

        Initialize the database connection.

        路径优先级：参数 db_path > 环境变量 CHROMA_VAULT_DB_PATH > 项目默认路径。
        - 默认路径为 <项目根>/assets/colors.db
        - WAL 模式提升并发性能
        - 外键约束开启，支持级联删除

        Args:
            db_path: 自定义数据库路径。为 None 时使用默认路径。
        """
        if db_path is None:
            db_path = os.environ.get("CHROMA_VAULT_DB_PATH")
        if db_path is None:
            db_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "..",
                "assets",
            )
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "colors.db")
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        """创建 5 张数据库表和 6 个索引。

        Create 5 database tables and 6 indexes.

        表结构：
        - colors：颜色主表，name 唯一，含预计算字段
        - tags：标签目录，name 唯一
        - color_tags：颜色-标签对，多对多关联
        - themes：主题表
        - theme_colors：主题-颜色绑定，role 为角色名

        索引：hex_code、hsl_h、hsl_l、wcag_luminance、color_id、tag_id
        """
        with self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    hex_code TEXT NOT NULL,
                    rgb_r INTEGER, rgb_g INTEGER, rgb_b INTEGER,
                    hsl_h REAL, hsl_s REAL, hsl_l REAL,
                    wcag_luminance REAL,
                    source TEXT,
                    source_url TEXT,
                    notes TEXT,
                    created_date TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT
                );

                CREATE TABLE IF NOT EXISTS color_tags (
                    color_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (color_id, tag_id),
                    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_date TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS theme_colors (
                    theme_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    color_id INTEGER NOT NULL,
                    PRIMARY KEY (theme_id, role),
                    FOREIGN KEY (theme_id) REFERENCES themes(id) ON DELETE CASCADE,
                    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_colors_hex ON colors(hex_code);
                CREATE INDEX IF NOT EXISTS idx_colors_hsl_h ON colors(hsl_h);
                CREATE INDEX IF NOT EXISTS idx_colors_hsl_l ON colors(hsl_l);
                CREATE INDEX IF NOT EXISTS idx_colors_wcag ON colors(wcag_luminance);
                CREATE INDEX IF NOT EXISTS idx_color_tags_color ON color_tags(color_id);
                CREATE INDEX IF NOT EXISTS idx_color_tags_tag ON color_tags(tag_id);
            """)

    def _compute(self, hex_code: str) -> dict:
        """根据 hex 一次性计算所有颜色分量。

        Compute all color components from a hex code.

        结果包含 rgb_r/g/b、hsl_h/s/l、wcag_luminance，
        存入数据库的自计算字段，避免每次查询重复运算。

        Args:
            hex_code: 十六进制色值。

        Returns:
            包含 rgb_r/g/b、hsl_h/s/l、wcag_luminance 的字典。
        """
        r, g, b = hex_to_rgb(hex_code)
        h, s, l = rgb_to_hsl(r, g, b)
        lum = wcag_luminance(r, g, b)
        return {
            "rgb_r": r,
            "rgb_g": g,
            "rgb_b": b,
            "hsl_h": h,
            "hsl_s": s,
            "hsl_l": l,
            "wcag_luminance": lum,
        }

    def _row_to_record(self, row: sqlite3.Row) -> ColorRecord:
        """将 sqlite3.Row 转换为 ColorRecord 数据类。

        Convert a sqlite3.Row to a ColorRecord dataclass.

        Args:
            row: 数据库查询结果行。

        Returns:
            ColorRecord 实例。
        """
        return ColorRecord(
            id=row["id"],
            name=row["name"],
            hex_code=row["hex_code"],
            rgb_r=row["rgb_r"],
            rgb_g=row["rgb_g"],
            rgb_b=row["rgb_b"],
            hsl_h=row["hsl_h"],
            hsl_s=row["hsl_s"],
            hsl_l=row["hsl_l"],
            wcag_luminance=row["wcag_luminance"],
            source=row["source"],
            source_url=row["source_url"],
            notes=row["notes"],
            created_date=row["created_date"],
        )

    def add(
        self,
        name: str,
        hex_code: str,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """添加颜色。

        Add a color to the database.

        自动计算 RGB、HSL、WCAG 亮度并写入预计算字段。
        可选传入标签列表，自动创建标签并建立多对多关联。

        Args:
            name: 颜色名称，在 colors 表中必须唯一。
            hex_code: 十六进制色值，如 "#00E5FF"。
            tags: 标签字符串列表，可选。每个标签自动创建（如已存在则复用）。
            source: 来源描述，可选。
            notes: 备注文本，可选。

        Returns:
            新插入颜色的 color_id。

        Raises:
            sqlite3.IntegrityError: 颜色名称重复时抛出。
        """
        comp = self._compute(hex_code)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO colors (name, hex_code, rgb_r, rgb_g, rgb_b, hsl_h, hsl_s, hsl_l, wcag_luminance, source, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    hex_code,
                    comp["rgb_r"],
                    comp["rgb_g"],
                    comp["rgb_b"],
                    comp["hsl_h"],
                    comp["hsl_s"],
                    comp["hsl_l"],
                    comp["wcag_luminance"],
                    source,
                    notes,
                ),
            )
            color_id = cur.lastrowid
            if tags:
                for tag_name in tags:
                    self._ensure_tag(tag_name)
                    tag_row = self._conn.execute(
                        "SELECT id FROM tags WHERE name = ?", (tag_name,)
                    ).fetchone()
                    if tag_row:
                        self._conn.execute(
                            "INSERT OR IGNORE INTO color_tags (color_id, tag_id) VALUES (?, ?)",
                            (color_id, tag_row["id"]),
                        )
            return color_id

    def _ensure_tag(self, tag_name: str) -> None:
        """确保标签存在，不存在则创建。

        Ensure a tag exists in the database, creating it if necessary.

        使用 INSERT OR IGNORE，已存在的标签静默跳过。

        Args:
            tag_name: 标签名称。
        """
        self._conn.execute(
            "INSERT OR IGNORE INTO tags (name, category) VALUES (?, ?)",
            (tag_name, "custom"),
        )

    def get_by_name(self, name: str) -> Optional[ColorRecord]:
        """按名称获取颜色。

        Get a color by its unique name.

        Args:
            name: 颜色名称。

        Returns:
            ColorRecord 实例，未找到时返回 None。
        """
        row = self._conn.execute(
            "SELECT * FROM colors WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_hex(self, hex_code: str) -> Optional[ColorRecord]:
        """按色值获取颜色。

        Get a color by its hex code.

        Args:
            hex_code: 十六进制色值，不含 # 前缀也可匹配。

        Returns:
            ColorRecord 实例，未找到时返回 None。
        """
        row = self._conn.execute(
            "SELECT * FROM colors WHERE hex_code = ?", (hex_code,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def search_by_tags(
        self, tags: list[str], match_all: bool = True
    ) -> list[ColorRecord]:
        """按标签搜索颜色。

        Search colors by tags.

        - match_all=True（默认）：颜色必须包含所有指定标签（HAVING COUNT 全匹配）。
        - match_all=False：颜色包含任意指定标签即返回（DISTINCT 去重）。

        Args:
            tags: 标签名称列表。
            match_all: 是否要求匹配全部标签，默认为 True。

        Returns:
            匹配的 ColorRecord 列表。tags 为空时返回空列表。
        """
        if not tags:
            return []
        placeholders = ",".join("?" for _ in tags)
        if match_all:
            rows = self._conn.execute(
                f"""
                SELECT c.* FROM colors c
                JOIN color_tags ct ON c.id = ct.color_id
                JOIN tags t ON ct.tag_id = t.id
                WHERE t.name IN ({placeholders})
                GROUP BY c.id
                HAVING COUNT(DISTINCT t.name) = ?
            """,
                tags + [len(tags)],
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"""
                SELECT DISTINCT c.* FROM colors c
                JOIN color_tags ct ON c.id = ct.color_id
                JOIN tags t ON ct.tag_id = t.id
                WHERE t.name IN ({placeholders})
            """,
                tags,
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search_by_hue_range(self, h_min: float, h_max: float) -> list[ColorRecord]:
        """按色相范围搜索颜色。

        Search colors within a hue range.

        Args:
            h_min: 色相下限（度）。
            h_max: 色相上限（度）。

        Returns:
            色相 hsl_h 在 [h_min, h_max] 范围内的 ColorRecord 列表。
        """
        rows = self._conn.execute(
            "SELECT * FROM colors WHERE hsl_h >= ? AND hsl_h <= ?",
            (h_min, h_max),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search_similar(self, hex_code: str, tolerance: float) -> list[ColorRecord]:
        """搜索相似色（以色相为中心）。

        Search for similar colors centered on a hue value.

        以目标 hex 的色相为中心 ±tolerance 搜索。
        当 tolerance >= 180 时返回所有颜色。
        自动处理 0°/360° 色相环 wraparound。

        Args:
            hex_code: 目标色值。
            tolerance: 色相差容忍度（度）。

        Returns:
            相似色列表。
        """
        r, g, b = hex_to_rgb(hex_code)
        h, _, _ = rgb_to_hsl(r, g, b)
        if tolerance >= 180:
            return self.all()
        h_min = (h - tolerance) % 360
        h_max = (h + tolerance) % 360
        if h_min <= h_max:
            return self.search_by_hue_range(h_min, h_max)
        else:
            return self.search_by_hue_range(h_min, 360) + self.search_by_hue_range(
                0, h_max
            )

    def all(self) -> list[ColorRecord]:
        """返回所有颜色。

        Return all colors.

        Returns:
            按创建时间倒序排列的 ColorRecord 列表。
        """
        rows = self._conn.execute(
            "SELECT * FROM colors ORDER BY created_date DESC"
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self) -> int:
        """返回颜色总数。

        Return the total number of colors.

        Returns:
            颜色总数。
        """
        row = self._conn.execute("SELECT COUNT(*) AS cnt FROM colors").fetchone()
        return row["cnt"] if row else 0

    def create_theme(self, name: str, description: str = "") -> int:
        """创建主题。

        Create a theme.

        Args:
            name: 主题名称，在 themes 表中必须唯一。
            description: 主题描述，可选。

        Returns:
            新创建主题的 theme_id。

        Raises:
            sqlite3.IntegrityError: 主题名称重复时抛出。
        """
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO themes (name, description) VALUES (?, ?)",
                (name, description),
            )
            return cur.lastrowid

    def set_theme_color(self, theme_name: str, role: str, color_name: str) -> None:
        """给主题绑定角色-颜色对。

        Bind a color role to a theme.

        校验 theme 和 color 存在后，INSERT OR REPLACE 写入。
        同一主题的同一角色重复调用会覆盖已有绑定。

        Args:
            theme_name: 主题名称。
            role: 角色名（如 "background"、"primary_fill"）。
            color_name: 颜色名称（需存在于 colors 表）。

        Raises:
            ValueError: 主题或颜色不存在时抛出。
        """
        theme_row = self._conn.execute(
            "SELECT id FROM themes WHERE name = ?", (theme_name,)
        ).fetchone()
        if not theme_row:
            raise ValueError(f"Theme '{theme_name}' not found")
        color_row = self._conn.execute(
            "SELECT id FROM colors WHERE name = ?", (color_name,)
        ).fetchone()
        if not color_row:
            raise ValueError(f"Color '{color_name}' not found")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO theme_colors (theme_id, role, color_id)
                VALUES (?, ?, ?)
            """,
                (theme_row["id"], role, color_row["id"]),
            )

    def get_theme(self, theme_name: str) -> Optional[dict[str, ColorRecord]]:
        """获取主题的所有角色-颜色映射。

        Get all role-color mappings for a theme.

        JOIN 三表（themes → theme_colors → colors），
        返回 {role: ColorRecord} 字典。

        Args:
            theme_name: 主题名称。

        Returns:
            {role: ColorRecord} 字典。主题不存在时返回 None。
        """
        rows = self._conn.execute(
            """
            SELECT tc.role, c.* FROM theme_colors tc
            JOIN colors c ON tc.color_id = c.id
            JOIN themes t ON tc.theme_id = t.id
            WHERE t.name = ?
        """,
            (theme_name,),
        ).fetchall()
        if not rows:
            return None
        return {row["role"]: self._row_to_record(row) for row in rows}

    def list_themes(self) -> list[str]:
        """返回所有主题名。

        List all theme names.

        Returns:
            按创建时间倒序排列的主题名称列表。
        """
        rows = self._conn.execute(
            "SELECT name FROM themes ORDER BY created_date DESC"
        ).fetchall()
        return [row["name"] for row in rows]

    def add_tag_to_color(self, color_name: str, tag_name: str) -> None:
        """给已有颜色追加一个标签。

        Add a tag to an existing color.

        校验 color 存在 → 确保 tag 存在 → 建立 color_tags 关联（自动去重）。

        Args:
            color_name: 颜色名称。
            tag_name: 标签名称。

        Raises:
            ValueError: 颜色不存在时抛出。
        """
        color_row = self._conn.execute(
            "SELECT id FROM colors WHERE name = ?", (color_name,)
        ).fetchone()
        if not color_row:
            raise ValueError(f"Color '{color_name}' not found")
        self._ensure_tag(tag_name)
        tag_row = self._conn.execute(
            "SELECT id FROM tags WHERE name = ?", (tag_name,)
        ).fetchone()
        if tag_row:
            with self._conn:
                self._conn.execute(
                    "INSERT OR IGNORE INTO color_tags (color_id, tag_id) VALUES (?, ?)",
                    (color_row["id"], tag_row["id"]),
                )

    def replace(
        self,
        name: str,
        hex_code: str,
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """覆盖已存在的颜色（UPDATE，保留 color_id 和主题绑定）。

        Replace an existing color (UPDATE, preserving color_id and theme bindings).

        UPDATE 方式更改 hex 和计算字段，清空旧标签后重新插入新标签。
        外键引用的 theme_colors 不受影响。

        Args:
            name: 颜色名称。
            hex_code: 十六进制色值。
            tags: 标签字符串列表，可选。
            source: 来源描述，可选。
            notes: 备注文本，可选。

        Returns:
            该颜色的 color_id。
        """
        comp = self._compute(hex_code)
        with self._conn:
            # 查找已有颜色，保留 color_id 不变（避免外键关联丢失）
            row = self._conn.execute(
                "SELECT id FROM colors WHERE name = ?", (name,)
            ).fetchone()
            if not row:
                raise ValueError(f"Color '{name}' not found")
            color_id = row["id"]
            # UPDATE 而非 DELETE+INSERT，保护 theme_colors 外键引用
            self._conn.execute(
                """
                UPDATE colors SET
                    hex_code = ?, rgb_r = ?, rgb_g = ?, rgb_b = ?,
                    hsl_h = ?, hsl_s = ?, hsl_l = ?, wcag_luminance = ?,
                    source = ?, notes = ?
                WHERE id = ?
            """,
                (
                    hex_code,
                    comp["rgb_r"], comp["rgb_g"], comp["rgb_b"],
                    comp["hsl_h"], comp["hsl_s"], comp["hsl_l"],
                    comp["wcag_luminance"],
                    source, notes,
                    color_id,
                ),
            )
            # 清空旧标签，重新插入新标签
            self._conn.execute(
                "DELETE FROM color_tags WHERE color_id = ?", (color_id,)
            )
            if tags:
                for tag_name in tags:
                    self._ensure_tag(tag_name)
                    tag_row = self._conn.execute(
                        "SELECT id FROM tags WHERE name = ?", (tag_name,)
                    ).fetchone()
                    if tag_row:
                        self._conn.execute(
                            "INSERT OR IGNORE INTO color_tags (color_id, tag_id) VALUES (?, ?)",
                            (color_id, tag_row["id"]),
                        )
            return color_id

    def delete_color(self, name: str) -> bool:
        """按名称删除颜色。

        Delete a color by name.

        外键 ON DELETE CASCADE 自动清理 color_tags 关联记录。

        Args:
            name: 颜色名称。

        Returns:
            True 表示删除成功，False 表示颜色不存在。
        """
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM colors WHERE name = ?", (name,)
            )
            return cur.rowcount > 0

    def delete_theme(self, name: str) -> bool:
        """按名称删除主题。

        Delete a theme by name.

        外键 ON DELETE CASCADE 自动清理 theme_colors 关联记录。

        Args:
            name: 主题名称。

        Returns:
            True 表示删除成功，False 表示主题不存在。
        """
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM themes WHERE name = ?", (name,)
            )
            return cur.rowcount > 0

    def close(self) -> None:
        """关闭 SQLite 连接。

        Close the SQLite connection.

        使用完毕后应调用此方法释放数据库资源。
        """
        self._conn.close()
