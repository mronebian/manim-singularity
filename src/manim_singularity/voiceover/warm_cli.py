"""vo-warm 命令行：渲染前预生成缺失旁白（本地 IndexTTS 段）。

vo-warm CLI: pre-generate missing narration before rendering.

只处理本地段；edge 段（legacy edge 音色名）不进本地批量，由渲染时逐句在线合成。

用法（在场景文件所在项目根目录执行，默认缓存目录 ./media/voice）：
    vo-warm Code/euler.py                    # 本机模式（arch）
    vo-warm Code/euler.py --conn ssh:archlinux   # 远端模式（Mac → arch）
    vo-warm Code/euler.py --list              # 只列出收集到的本地段，不合成

可用环境变量覆盖默认值：
    VO_TTS_REPO      local 模式 tts 仓库路径
    VO_TTS_REPO_SSH  ssh 模式下 arch 端 tts 仓库路径
    VO_TTS_CONN      "" = local；ssh:archlinux / ssh:user@host
"""
import argparse
import os
import sys

from .synclib import scan_scene, warm


def _default_cache_dir() -> str:
    return os.path.join(os.getcwd(), "media", "voice")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-generate missing local voiceover audio.")
    ap.add_argument("files", nargs="+", help="scene .py 文件")
    ap.add_argument("--cache-dir", default="", help="缓存目录（默认 ./media/voice）")
    ap.add_argument("--conn", default="", help="''=local；ssh:archlinux；ssh:user@host")
    ap.add_argument("--list", action="store_true", help="只列本地段任务，不合成")
    args = ap.parse_args(argv)

    if args.conn:
        os.environ.setdefault("VO_TTS_CONN", args.conn)
    cache_dir = args.cache_dir or _default_cache_dir()

    tasks: list[dict] = []
    edge_total = 0
    for f in args.files:
        t, e = scan_scene(f)
        tasks.extend(t)
        edge_total += e
    # 跨文件去重
    seen: dict[str, dict] = {}
    for t in tasks:
        seen.setdefault(t["out"], t)
    tasks = list(seen.values())

    print(f"[vo] 扫描 {len(args.files)} 个场景：本地段 {len(tasks)} | edge 段 {edge_total}"
          "（edge 段渲染时逐句在线合成，不在此预热）")
    if args.list:
        for t in sorted(tasks, key=lambda x: x["out"]):
            print(f"{t['out']}  [{t['preset']}:{t['lang']}]  {t['text'][:40]!r}")
        return 0

    def _prog(msg: str) -> None:
        print(f"[vo] {msg}", flush=True)

    hit, generated = warm(tasks, cache_dir, on_progress=_prog)
    print(f"[vo] 汇总：任务 {len(tasks)} | 命中 {hit} | 新生成 {generated} | 缓存 {cache_dir}")
    if generated < len(tasks) - hit:
        print("[vo] 警告：部分任务生成失败，见上方输出", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
