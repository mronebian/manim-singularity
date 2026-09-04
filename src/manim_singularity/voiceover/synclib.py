"""跨机语音批处理同步库（纯 stdlib）。

Cross-machine voice batch sync library (pure stdlib).

职责：
- 缓存键：每段旁白 = 一个 wav。
    * 本地 IndexTTS：MD5(speak||preset:lang:vCACHE_VERSION).wav
    * edge-tts：MD5(speak||voice).wav（沿用旧 edge 时代命名，老缓存可直接复用）
- AST 静态扫描场景，仅收集**本地 preset** 段（edge 段渲染时逐句实时在线合成）。
- 批处理执行：local（arch 本机直接 uv run）或 ssh（拉起 arch → 传 manifest →
  批量合成 → rsync 回传），把缺失 wav 补进本地缓存目录。
- on_progress 回调用于把进度接到 manim logger（渲染路径）或 print（CLI 路径）。

不 import manim / compat，保证在纯 CLI 环境也能跑。
"""
import ast
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
from typing import Callable, Optional

from .presets import (
    CACHE_VERSION,
    DEFAULT_PRESET,
    is_preset,
    normalize_backend,
    preset_lang,
)

#: VoiceOver 上会产生一段旁白的调用方法名。
TARGET_METHODS = {"say_blocking", "context", "play_with_audio"}

#: 环境变量默认值。
ENV = {
    "repo": "VO_TTS_REPO",            # tts 仓库路径（local 模式子进程执行目录）
    "ssh_repo": "VO_TTS_REPO_SSH",    # arch 上 tts 仓库路径（ssh 模式远端目录）
    "conn": "VO_TTS_CONN",            # ""=local，ssh:archlinux / ssh:user@host
    "host": "VO_TTS_HOST",            # 兼容旧名：直接给 host 也视为 ssh
}

SSH_REPO_DEFAULT = "/home/mronebian/startup_program/tts"
SSH_STAGE_DEFAULT = "/home/mronebian/.cache/vo_stage"

Progress = Callable[[str], None]


def _noop(_msg: str) -> None:
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(ENV[key], default)


def _short(text: str, n: int = 22) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def cache_name(speak_text: str, preset: str, lang: str) -> str:
    """本地 IndexTTS 段的缓存文件名（带 CACHE_VERSION）。

    必须与运行时 VoiceManager 的计算完全一致（同一函数），
    否则预生成的文件运行时命不中。换品牌参考音后 CACHE_VERSION+1 即全部失效。
    """
    payload = f"{speak_text}||{preset}:{lang}:v{CACHE_VERSION}".encode("utf-8")
    return hashlib.md5(payload).hexdigest() + ".wav"


def edge_cache_name(speak_text: str, edge_voice: str) -> str:
    """edge-tts 段的缓存文件名（沿用旧 edge 时代命名，老缓存可复用）。"""
    payload = f"{speak_text}||{edge_voice}".encode("utf-8")
    return hashlib.md5(payload).hexdigest() + ".wav"


def task_from(speak_text: str, voice: str, lang: Optional[str] = None,
              backend: str = "auto") -> Optional[dict]:
    """把一个旁白段标准化成本地批处理任务。

    只有解析为本地 preset 时返回任务 dict；edge 段返回 None（不进本地批量）。
    """
    b = normalize_backend(backend)
    if b == "edge":
        return None
    if not is_preset(voice):
        preset = DEFAULT_PRESET
    else:
        preset = voice
    if b == "local" and not is_preset(voice):
        # 显式 local + 非 preset 名：也用默认品牌音本地合成
        preset = DEFAULT_PRESET
    lang = lang or preset_lang(preset)
    return {
        "out": cache_name(speak_text, preset, lang),
        "text": speak_text,
        "preset": preset,
        "lang": lang,
    }


# --------------------------------------------------------------------------- #
# AST 收集
# --------------------------------------------------------------------------- #
def _lit(node) -> Optional[str]:
    """尽力把 AST 节点取成字符串字面量（跨行/常量拼接可解，f-string 动态返回 None）。"""
    try:
        if isinstance(node, ast.JoinedStr):
            return None
        return ast.literal_eval(node)
    except Exception:
        return None


def _call_arg(call: ast.Call, pos: int, kw: str):
    if kw:
        for k in call.keywords:
            if k.arg == kw:
                return _lit(k.value)
    args = call.args
    if args and isinstance(args[0], ast.Starred):
        return None
    if pos < len(args):
        return _lit(args[pos])
    return None


def _segment_local(speak_voice: str, backend: str) -> bool:
    b = normalize_backend(backend)
    if b == "edge":
        return False
    if b == "local":
        return True
    return is_preset(speak_voice)  # auto：非 preset → edge


def scan_scene(path: str, override_backend: Optional[str] = None) -> tuple[list[dict], int]:
    """扫描单个 scene 文件。

    Args:
        path: scene .py 文件。
        override_backend: 运行时层后端（如 VoiceOver 的 backend / VO_BACKEND），
            仅当调用处与 VoiceOver 构造都没有显式 backend 时生效。None → 纯 AST 推断。

    Returns:
        (本地任务列表[按缓存键去重], edge 段数量)。
        edge 段渲染时由 VoiceManager 逐句实时 edge 合成。
    """
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)

    vo_defaults: dict[str, str] = {}
    vo_backends: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and getattr(val.func, "id", "") == "VoiceOver"):
            continue
        voice = DEFAULT_PRESET
        backend = ""
        for k in val.keywords:
            if k.arg == "default_voice":
                v = _lit(k.value)
                if v:
                    voice = v
            elif k.arg == "backend":
                v = _lit(k.value)
                if v:
                    backend = v
        for t in node.targets:
            if isinstance(t, ast.Name):
                vo_defaults[t.id] = voice
                vo_backends[t.id] = backend
            elif isinstance(t, ast.Attribute):
                vo_defaults[t.attr] = voice
                vo_backends[t.attr] = backend

    def receiver_defaults(call: ast.Call) -> tuple[str, str]:
        func = call.func
        attr = func.attr if isinstance(func, ast.Attribute) else ""
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return (vo_defaults.get(func.value.id, DEFAULT_PRESET),
                    vo_backends.get(func.value.id, ""))
        return (vo_defaults.get(attr, DEFAULT_PRESET), vo_backends.get(attr, ""))

    seen: dict[str, dict] = {}
    edge_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in TARGET_METHODS):
            continue

        method = func.attr
        def_voice, def_backend = receiver_defaults(node)
        voice_lit = None
        tts_text = None
        if method == "play_with_audio":
            text = _call_arg(node, 0, "text")
            voice_lit = _call_arg(node, 0, "voice")
            tts_text = _call_arg(node, 0, "tts_text")
        else:
            text = _call_arg(node, 0, "")
            voice_lit = _call_arg(node, 1, "voice")
            tts_text = _call_arg(node, 3, "tts_text")
        backend_lit = None
        for k in node.keywords:
            if k.arg == "backend":
                backend_lit = _lit(k.value)
                break

        voice = voice_lit or def_voice or DEFAULT_PRESET
        backend = backend_lit or def_backend or override_backend or "auto"
        speak = tts_text or text
        if not speak:
            continue
        if not _segment_local(voice, backend):
            edge_count += 1
            continue
        task = task_from(speak, voice, backend=backend)
        if task is None:
            edge_count += 1
            continue
        if task["out"] not in seen:
            seen[task["out"]] = task
    return list(seen.values()), edge_count


def collect_from_scene(path: str) -> list[dict]:
    """扫描单个 scene 文件，返回本地批处理任务列表（AST 语义的本地段）。"""
    tasks, _ = scan_scene(path)
    return tasks


# --------------------------------------------------------------------------- #
# 执行
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], data: Optional[bytes] = None) -> None:
    p = subprocess.run(cmd, input=data, capture_output=True)
    if p.returncode != 0:
        tail = (p.stdout + p.stderr).decode("utf-8", "replace")[-2000:]
        raise RuntimeError(
            f"command failed ({p.returncode}): {' '.join(shlex.quote(c) for c in cmd)}\n{tail}"
        )


def run_batch(tasks: list[dict], cache_dir: str,
              on_progress: Optional[Progress] = None) -> list[str]:
    """执行批处理：local/ssh 生成缺失 wav 并落入 cache_dir。

    返回实际生成的文件名列表。
    """
    p = on_progress or _noop
    conn = _env("conn") or (f"ssh:{_env('host')}" if _env("host") else "")
    repo = _env("repo") or SSH_REPO_DEFAULT
    out_files = [t["out"] for t in tasks]
    manifest = json.dumps(tasks, ensure_ascii=False).encode("utf-8")

    if not conn:
        p(f"拉起 local 合成 {len(tasks)} 段（uv run {repo}）")
        with tempfile.TemporaryDirectory(prefix="vo_stage_") as stage:
            _run([
                "uv", "run", "--project", repo, "python",
                os.path.join(repo, "tools", "vo_synth_batch.py"),
                "--out-dir", stage,
            ], data=manifest)
            _move_wavs(stage, cache_dir)
    else:
        host = conn.split(":", 1)[1] if ":" in conn else conn
        ssh_repo = _env("ssh_repo") or SSH_REPO_DEFAULT
        stage = SSH_STAGE_DEFAULT
        p(f"ssh {host} 拉起合成 {len(tasks)} 段…")
        remote_cmd = (
            f"cd {shlex.quote(ssh_repo)} && "
            f"uv run --project . python {shlex.quote(os.path.join(ssh_repo, 'tools', 'vo_synth_batch.py'))} "
            f"--out-dir {shlex.quote(stage)}"
        )
        _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, remote_cmd], data=manifest)
        os.makedirs(cache_dir, exist_ok=True)
        _run(["rsync", "-a", "--remove-source-files", f"{host}:{stage}/", cache_dir + "/"])
        _run(["ssh", "-o", "BatchMode=yes", host, f"rm -rf {shlex.quote(stage)}"])
    return [f for f in out_files if os.path.isfile(os.path.join(cache_dir, f))]


def _move_wavs(stage: str, cache_dir: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    for name in os.listdir(stage):
        if name.lower().endswith(".wav"):
            shutil.move(os.path.join(stage, name), os.path.join(cache_dir, name))


def warm(tasks: list[dict], cache_dir: str,
         on_progress: Optional[Progress] = None) -> tuple[int, int]:
    """预生成缺失任务。返回 (命中数, 本次新生成数)。"""
    p = on_progress or _noop
    os.makedirs(cache_dir, exist_ok=True)
    missing = []
    hit = 0
    for t in tasks:
        if os.path.isfile(os.path.join(cache_dir, t["out"])):
            hit += 1
        else:
            missing.append(t)
    p(f"任务 {len(tasks)} 段：缓存命中 {hit} | 缺失 {len(missing)}")
    if not missing:
        return hit, 0
    run_batch(missing, cache_dir, on_progress=on_progress)
    n_ok = 0
    for i, t in enumerate(missing, 1):
        ok = os.path.isfile(os.path.join(cache_dir, t["out"]))
        n_ok += int(ok)
        p(f"[{i}/{len(missing)}] {'完成' if ok else '失败'} {_short(t['text'])} -> {t['out']}")
    return hit, n_ok


def warm_scene_file(path: str, cache_dir: str,
                    on_progress: Optional[Progress] = None) -> Optional[tuple[int, int]]:
    """预热单个场景文件（仅本地段）。返回 (命中数, 新生成数)；文件无效返回 None。"""
    if not path or not os.path.isfile(path):
        return None
    try:
        tasks, _ = scan_scene(path)
    except Exception:
        return None
    if not tasks:
        return (0, 0)
    return warm(tasks, cache_dir, on_progress=on_progress)


def ensure_task(task: dict, cache_dir: str) -> str:
    """确保单条任务可用（manager 运行时 miss 时调用）。返回 wav 路径。"""
    pth = os.path.join(cache_dir, task["out"])
    if not os.path.isfile(pth):
        run_batch([task], cache_dir)
    return pth
