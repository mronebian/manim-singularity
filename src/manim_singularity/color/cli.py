import argparse
import sys

from ._db import ColorDB


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaVault — color database for Manim")
    parser.add_argument("--db-path", default=None,
                        help="Custom database path (overrides CHROMA_VAULT_DB_PATH env)")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize database (create file and tables)")
    p_init.add_argument("--db-path", default=None,
                        help="Custom database path (overrides CHROMA_VAULT_DB_PATH env)")

    p_add = sub.add_parser("add", help="Add a color")
    p_add.add_argument("--db-path", default=None)
    p_add.add_argument("name", help="Color name")
    p_add.add_argument("hex", help="Hex code (e.g. #00E5FF)")
    p_add.add_argument("--tags", nargs="*", default=[], help="Tags")
    p_add.add_argument("--source", default=None, help="Source description")

    p_list = sub.add_parser("list", help="List all colors")
    p_list.add_argument("--db-path", default=None)

    p_search = sub.add_parser("search", help="Search by tags")
    p_search.add_argument("--db-path", default=None)
    p_search.add_argument("tags", nargs="+", help="Tag names")

    p_stats = sub.add_parser("stats", help="Show statistics")
    p_stats.add_argument("--db-path", default=None)

    p_ct = sub.add_parser("create-theme", help="Create a theme")
    p_ct.add_argument("--db-path", default=None)
    p_ct.add_argument("name", help="Theme name")
    p_ct.add_argument("--desc", default="", help="Theme description")

    p_sr = sub.add_parser("set-role", help="Bind a color role to a theme")
    p_sr.add_argument("--db-path", default=None)
    p_sr.add_argument("theme", help="Theme name")
    p_sr.add_argument("role", help="Role name (e.g. background)")
    p_sr.add_argument("color_name", help="Color name in database")

    p_lt = sub.add_parser("list-themes", help="List all themes")
    p_lt.add_argument("--db-path", default=None)

    p_del = sub.add_parser("delete", help="Delete a color by name")
    p_del.add_argument("--db-path", default=None)
    p_del.add_argument("name", help="Color name")

    p_dt = sub.add_parser("delete-theme", help="Delete a theme by name")
    p_dt.add_argument("--db-path", default=None)
    p_dt.add_argument("name", help="Theme name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    db = ColorDB(db_path=args.db_path)

    if args.command == "init":
        path = db._conn.execute("PRAGMA database_list").fetchone()["file"]
        print(f"Database ready: {path}")

    elif args.command == "add":
        db.add(args.name, args.hex, tags=args.tags, source=args.source)
        print(f"Added '{args.name}' ({args.hex})")

    elif args.command == "list":
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
        colors = db.search_by_tags(args.tags, match_all=True)
        if not colors:
            print("No matches.")
            return
        for c in colors:
            print(f"  {c.name:20s} {c.hex_code}")

    elif args.command == "stats":
        print(f"Total colors:   {db.count()}")
        themes = db.list_themes()
        print(f"Themes:         {len(themes)}")
        if themes:
            print(f"  ({', '.join(themes)})")

    elif args.command == "create-theme":
        db.create_theme(args.name, description=args.desc)
        print(f"Created theme '{args.name}'")

    elif args.command == "set-role":
        db.set_theme_color(args.theme, args.role, args.color_name)
        print(f"Set '{args.theme}'.{args.role} → {args.color_name}")

    elif args.command == "list-themes":
        themes = db.list_themes()
        if not themes:
            print("No themes.")
        else:
            for t in themes:
                print(f"  {t}")

    elif args.command == "delete":
        if db.delete_color(args.name):
            print(f"Deleted color '{args.name}'")
        else:
            print(f"Color '{args.name}' not found")

    elif args.command == "delete-theme":
        if db.delete_theme(args.name):
            print(f"Deleted theme '{args.name}'")
        else:
            print(f"Theme '{args.name}' not found")

    db.close()


if __name__ == "__main__":
    main()
