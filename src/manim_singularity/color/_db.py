import colorsys
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """去掉 #，取每两位 16 进制转 RGB 0-255"""
    hex_code = hex_code.lstrip("#")
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """
    用 colorsys.rgb_to_hls 转 HSL。
    注意 colorsys 返回 (h, l, s)，我们重排为 (h, s, l) 并量化为 ° 和 %。
    """
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h * 360, s * 100, l * 100


def wcag_luminance(r: int, g: int, b: int) -> float:
    """
    计算 WCAG 2.0 相对亮度。
    sRGB 线性化分段函数：c ≤ 0.03928 时线性，否则 gamma 2.4。
    公式：0.2126R + 0.7152G + 0.0722B
    """

    def linearize(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


@dataclass
class ColorRecord:
    """
    数据类，存一条颜色的所有预计算字段。
    - rgb / hsl：便捷属性返回元组
    - to_manim_color：懒导入 ManimColor（避免 _db.py 直接依赖 manim）
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
        """返回 (r, g, b) 元组"""
        return (self.rgb_r, self.rgb_g, self.rgb_b)

    @property
    def hsl(self) -> tuple[float, float, float]:
        """返回 (h, s, l) 元组"""
        return (self.hsl_h, self.hsl_s, self.hsl_l)

    def to_manim_color(self):
        """将 hex_code 转为 ManimColor（懒导入，减少启动开销）"""
        from manim import ManimColor

        return ManimColor(self.hex_code)


class ColorDB:
    """
    SQLite 颜色数据库核心。
    零外部依赖，仅用 Python 标准库（sqlite3 + colorsys）。

    默认路径：<项目根>/assets/colors.db，可通过 db_path 参数自定义。
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库连接。
        - 默认 path 指向项目 assets/colors.db
        - WAL 模式提升并发性能
        - 外键约束开启，级联删除
        """
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
        """
        5 张表：
        - colors：颜色主表，name 唯一，含预计算字段
        - tags：标签目录，name 唯一
        - color_tags：颜色-标签多对多关联
        - themes：主题表
        - theme_colors：主题-颜色绑定表，role 为角色名

        6 个索引：hex_code、hsl_h、hsl_l、wcag_luminance、color_id、tag_id
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
        """
        给定 hex，一次算完 RGB、HSL、WCAG 亮度。
        结果存入数据库的自计算字段，避免每次查询重复运算。
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
        """将 sqlite3.Row 转换为 ColorRecord 数据类"""
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
        """
        添加颜色。
        1. 预计算 RGB / HSL / 亮度
        2. 插入 colors 行
        3. 遍历 tags 列表，自动创建标签并建立多对多关联
        4. 返回 color_id
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
        """确保标签存在：INSERT OR IGNORE，已存在时静默跳过"""
        self._conn.execute(
            "INSERT OR IGNORE INTO tags (name, category) VALUES (?, ?)",
            (tag_name, "custom"),
        )

    def get_by_name(self, name: str) -> Optional[ColorRecord]:
        """按 name 唯一查询，返回 ColorRecord 或 None"""
        row = self._conn.execute(
            "SELECT * FROM colors WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_hex(self, hex_code: str) -> Optional[ColorRecord]:
        """按 hex_code 唯一查询，返回 ColorRecord 或 None"""
        row = self._conn.execute(
            "SELECT * FROM colors WHERE hex_code = ?", (hex_code,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def search_by_tags(
        self, tags: list[str], match_all: bool = True
    ) -> list[ColorRecord]:
        """
        按标签搜索颜色。
        - match_all=True（默认）：颜色必须拥有所有指定标签（HAVING COUNT 全匹配）
        - match_all=False：颜色拥有任意指定标签即返回（DISTINCT 去重）
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
        """按色相范围筛选 hsl_h ∈ [h_min, h_max]，用于色相筛选"""
        rows = self._conn.execute(
            "SELECT * FROM colors WHERE hsl_h >= ? AND hsl_h <= ?",
            (h_min, h_max),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search_similar(self, hex_code: str, tolerance: float) -> list[ColorRecord]:
        """
        以目标 hex 的色相为中心 ±tolerance 搜索相似色。
        处理 0°/360° 色相环 wraparound：
        - 若范围跨越 0°，拆为两段 [h_min, 360] + [0, h_max]
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
        """返回所有颜色，按创建时间倒序"""
        rows = self._conn.execute(
            "SELECT * FROM colors ORDER BY created_date DESC"
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self) -> int:
        """返回颜色总数"""
        row = self._conn.execute("SELECT COUNT(*) AS cnt FROM colors").fetchone()
        return row["cnt"] if row else 0

    def create_theme(self, name: str, description: str = "") -> int:
        """
        创建主题，返回 theme_id。
        description 为选填说明文本。
        """
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO themes (name, description) VALUES (?, ?)",
                (name, description),
            )
            return cur.lastrowid

    def set_theme_color(self, theme_name: str, role: str, color_name: str) -> None:
        """
        给主题绑定一个角色-颜色对。
        校验 theme 和 color 存在后，INSERT OR REPLACE 写入。
        role 为角色名（如 "primary"、"bg"），无预留列表限制。
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
        """
        获取主题的所有角色-颜色映射。
        JOIN 三表（themes → theme_colors → colors），返回 {role: ColorRecord}。
        主题不存在时返回 None。
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
        """返回所有主题名列表，按创建时间倒序"""
        rows = self._conn.execute(
            "SELECT name FROM themes ORDER BY created_date DESC"
        ).fetchall()
        return [row["name"] for row in rows]

    def add_tag_to_color(self, color_name: str, tag_name: str) -> None:
        """
        给已有颜色追加一个标签。
        校验 color 存在 → 确保 tag 存在 → 建立 color_tags 关联（自动去重）。
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

    def delete_color(self, name: str) -> bool:
        """
        按名称删除颜色（级联删除 color_tags 关联）。
        返回 True 表示删除了记录，False 表示颜色不存在。
        """
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM colors WHERE name = ?", (name,)
            )
            return cur.rowcount > 0

    def delete_theme(self, name: str) -> bool:
        """
        按名称删除主题（级联删除 theme_colors 关联）。
        返回 True 表示删除了记录，False 表示主题不存在。
        """
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM themes WHERE name = ?", (name,)
            )
            return cur.rowcount > 0

    def close(self) -> None:
        """关闭 SQLite 连接"""
        self._conn.close()
