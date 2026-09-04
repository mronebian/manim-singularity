"""跨机语音批处理同步库（纯 stdlib）。

Cross-machine voice batch sync library (pure stdlib).

职责：
- 生成缓存键：一段旁白 = MD5(speak_text||preset:lang).wav（与 manager.py 共用，
  保证预生成与运行时命中同一缓存文件）。
- AST 静态收集场景源码里的解说任务（say_blocking / context / play_with_audio）。
- 批处理执行：local（arch 本机直接 uv run）或 ssh（拉起 arch → 传 manifest →
  批量合成 → rsync 回传），把缺失的 wav 补进本地缓存目录。
- 供 manager.py 运行时"单条补"（动态文本 miss）复用同一管道。

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

from .presets import DEFAULT_PRESET, PRESET_LANG, PRESET_IDS, resolve_voice

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


def _env(key: str, default: str = "") -> str:
    return os.environ.get(ENV[key], default)


def cache_name(speak_text: str, preset: str, lang: str) -> str:
    """一段旁白的缓存文件名。

    Cache file name for one narration segment.

    必须与运行时 VoiceManager 的计算完全一致（同一函数），
    否则预生成的文件运行时命不中。
    """
    payload = f"{speak_text}||{preset}:{lang}".encode("utf-8")
    return hashlib.md5(payload).hexdigest() + ".wav"


def task_from(speak_text: str, voice: str, lang: str | None = None) -> dict:
    """把一个旁白段标准化成批处理任务。

    Normalize one narration segment into a batch task dict.
    """
    preset, preset_lang = resolve_voice(voice)
    lang = lang or preset_lang
    return {
        "out": cache_name(speak_text, preset, lang),
        "text": speak_text,
        "preset": preset,
        "lang": lang,
    }


def _lit(node) -> str | None:
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
    if isinstance(args[0], ast.Starred):
        return None
    if pos < len(args):
        return _lit(args[pos])
    return None


def collect_from_scene(path: str) -> list[dict]:
    """AST 扫描单个 scene 文件，提取旁白任务列表（已按缓存键去重）。

    AST-scan one scene file and return narration tasks (deduped by cache key).
    """
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)

    vo_defaults: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and getattr(val.func, "id", "") == "VoiceOver"):
            continue
        voice = DEFAULT_PRESET
        for k in val.keywords:
            if k.arg == "default_voice":
                v = _lit(k.value)
                if v:
                    voice = v
                break
        for t in node.targets:
            if isinstance(t, ast.Name):
                vo_defaults[t.id] = voice
            elif isinstance(t, ast.Attribute):
                vo_defaults[t.attr] = voice

    def receiver_voice(call: ast.Call) -> str:
        func = call.func
        if isinstance(func, ast.Attribute):
            rec = func.value
            if isinstance(rec, ast.Name):
                return vo_defaults.get(rec.id, vo_defaults.get(func.attr, DEFAULT_PRESET))
            if isinstance(rec, ast.Attribute):
                return vo_defaults.get(func.attr, DEFAULT_PRESET)
        return DEFAULT_PRESET

    seen: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in TARGET_METHODS):
            continue

        method = func.attr
        voice_lit = None
        tts_text = None
        display = None
        if method == "play_with_audio":
            text = _call_arg(node, 0, "text")
            voice_lit = _call_arg(node, 0, "voice")
            tts_text = _call_arg(node, 0, "tts_text")
        else:
            text = _call_arg(node, 0, "")  # say_blocking/context: text = 第 0 位置参数
            voice_lit = _call_arg(node, 1, "voice")
            tts_text = _call_arg(node, 3, "tts_text")

        voice = voice_lit or receiver_voice(node)
        speak = tts_text or text or display
        if not speak:
            continue
        task = task_from(speak, voice)
        if task["out"] not in seen:
            seen[task["out"]] = task
    return list(seen.values())


def _run(cmd: list[str], data: bytes | None = None) -> None:
    p = subprocess.run(cmd, input=data, capture_output=True)
    if p.returncode != 0:
        tail = (p.stdout + p.stderr).decode("utf-8", "replace")[-2000:]
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(shlex.quote(c) for c in cmd)}\n{tail}")


def run_batch(tasks: list[dict], cache_dir: str) -> list[dict]:
    """执行批处理：local/ssh 生成缺失 wav 并落入 cache_dir。

    Run the batch: synthesize missing wavs (local or over ssh) into cache_dir.

    返回实际生成的文件名列表。
    """
    conn = _env("conn") or (f"ssh:{_env('host')}" if _env("host") else "")
    repo = _env("repo") or SSH_REPO_DEFAULT
    out_files = [t["out"] for t in tasks]
    manifest = json.dumps(tasks, ensure_ascii=False).encode("utf-8")

    if not conn:
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
        remote_cmd = (
            f"cd {shlex.quote(ssh_repo)} && "
            f"uv run --project . python {shlex.quote(os.path.join(ssh_repo, 'tools', 'vo_synth_batch.py'))} "
            f"--out-dir {shlex.quote(stage)}"
        )
        try:
            _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, remote_cmd], data=manifest)
            os.makedirs(cache_dir, exist_ok=True)
            _run(["rsync", "-a", "--remove-source-files", f"{host}:{stage}/", cache_dir + "/"])
            _run(["ssh", "-o", "BatchMode=yes", host, f"rm -rf {shlex.quote(stage)}"])
        except RuntimeError:
            raise
    return [f for f in out_files if os.path.isfile(os.path.join(cache_dir, f))]


def _move_wavs(stage: str, cache_dir: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    for name in os.listdir(stage):
        if name.lower().endswith(".wav"):
            shutil.move(os.path.join(stage, name), os.path.join(cache_dir, name))


def warm(tasks: list[dict], cache_dir: str) -> tuple[int, int]:
    """预生成缺失任务。返回 (命中数, 本次新生成数)。

    Pre-generate missing tasks; returns (hit_count, generated_count).
    """
    os.makedirs(cache_dir, exist_ok=True)
    missing = []
    hit = 0
    for t in tasks:
        p = os.path.join(cache_dir, t["out"])
        if os.path.isfile(p):
            hit += 1
        else:
            missing.append(t)
    if not missing:
        return hit, 0
    got = run_batch(missing, cache_dir)
    return hit, len(got)


def warm_scene_file(path: str, cache_dir: str) -> tuple[int, int] | None:
    """预热单个场景文件：扫描 → 比对 → 整批生成缺失语音。

    Warm one scene file: AST-scan → diff against cache → batch-generate missing.

    返回 (命中数, 新生成数)；文件不存在/不可解析时返回 None。
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        tasks = collect_from_scene(path)
    except Exception:
        return None
    if not tasks:
        return (0, 0)
    return warm(tasks, cache_dir)


def ensure_task(task: dict, cache_dir: str) -> str:
    """确保单条任务可用（manager 运行时 miss 时调用）。返回 wav 路径。

    Ensure a single task's wav exists (runtime cache-miss path); returns wav path.
    """
    p = os.path.join(cache_dir, task["out"])
    if not os.path.isfile(p):
        run_batch([task], cache_dir)
    return p
