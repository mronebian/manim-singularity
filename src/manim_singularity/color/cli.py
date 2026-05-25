import argparse
import sys

from ._db import ColorDB


def main() -> None:
    """
    chroma 命令行入口。
    零 manim 依赖，直接从 _db 导入 ColorDB。
    注册 4 个子命令：add / list / search / stats。
    """
    parser = argparse.ArgumentParser(description="ChromaVault — color database for Manim")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", help="Add a color")
    p_add.add_argument("name", help="Color name")
    p_add.add_argument("hex", help="Hex code (e.g. #00E5FF)")
    p_add.add_argument("--tags", nargs="*", default=[], help="Tags")
    p_add.add_argument("--source", default=None, help="Source description")

    p_list = sub.add_parser("list", help="List all colors")

    p_search = sub.add_parser("search", help="Search by tags")
    p_search.add_argument("tags", nargs="+", help="Tag names")

    p_stats = sub.add_parser("stats", help="Show statistics")

    p_ct = sub.add_parser("create-theme", help="Create a theme")
    p_ct.add_argument("name", help="Theme name")
    p_ct.add_argument("--desc", default="", help="Theme description")

    p_sr = sub.add_parser("set-role", help="Bind a color role to a theme")
    p_sr.add_argument("theme", help="Theme name")
    p_sr.add_argument("role", help="Role name (e.g. background)")
    p_sr.add_argument("color_name", help="Color name in database")

    p_lt = sub.add_parser("list-themes", help="List all themes")

    p_del = sub.add_parser("delete", help="Delete a color by name")
    p_del.add_argument("name", help="Color name")

    p_dt = sub.add_parser("delete-theme", help="Delete a theme by name")
    p_dt.add_argument("name", help="Theme name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    db = ColorDB()

    if args.command == "add":
        """添加颜色：插入并打印结果"""
        db.add(args.name, args.hex, tags=args.tags, source=args.source)
        print(f"Added '{args.name}' ({args.hex})")

    elif args.command == "list":
        """列出所有颜色：遍历 all()，对每条查关联标签名一并打印"""
        colors = db.all()
        if not colors:
            print("No colors in database.")
            return
        for c in colors:
            tags = ", ".join(
                t["name"] for t in db._conn.execute(
                    "SELECT t.name FROM tags t JOIN color_tags ct ON t.id = ct.tag_id WHERE ct.color_id = ?",
                    (c.id,),
                ).fetchall()
            )
            tag_str = f"  [{tags}]" if tags else ""
            print(f"  {c.name:20s} {c.hex_code}{tag_str}")

    elif args.command == "search":
        """按标签全匹配搜索，打印符合条件的颜色"""
        colors = db.search_by_tags(args.tags, match_all=True)
        if not colors:
            print("No matches.")
            return
        for c in colors:
            print(f"  {c.name:20s} {c.hex_code}")

    elif args.command == "stats":
        """打印颜色总数和主题数"""
        print(f"Total colors:   {db.count()}")
        themes = db.list_themes()
        print(f"Themes:         {len(themes)}")
        if themes:
            print(f"  ({', '.join(themes)})")

    elif args.command == "create-theme":
        """创建主题"""
        db.create_theme(args.name, description=args.desc)
        print(f"Created theme '{args.name}'")

    elif args.command == "set-role":
        """绑定角色-颜色到主题"""
        db.set_theme_color(args.theme, args.role, args.color_name)
        print(f"Set '{args.theme}'.{args.role} → {args.color_name}")

    elif args.command == "list-themes":
        """列出所有主题名"""
        themes = db.list_themes()
        if not themes:
            print("No themes.")
        else:
            for t in themes:
                print(f"  {t}")

    elif args.command == "delete":
        """按名称删除颜色"""
        if db.delete_color(args.name):
            print(f"Deleted color '{args.name}'")
        else:
            print(f"Color '{args.name}' not found")

    elif args.command == "delete-theme":
        """按名称删除主题"""
        if db.delete_theme(args.name):
            print(f"Deleted theme '{args.name}'")
        else:
            print(f"Theme '{args.name}' not found")

    db.close()


if __name__ == "__main__":
    main()
