"""
profiler.py — 项目探测器

入库第一步:扫项目目录,识别语言、技术栈、目录结构、入口文件、README。
纯文件系统操作,不依赖 AI。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

SKILL_ROOT = Path(__file__).resolve().parent.parent
STACKS_CONFIG = SKILL_ROOT / "config" / "stacks.toml"


@dataclass
class ProjectProfile:
    name: str
    root_path: str
    language: str | None = None
    languages: dict[str, float] = field(default_factory=dict)
    tech_stack: list[str] = field(default_factory=list)
    build_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entry_files: list[str] = field(default_factory=list)
    dir_structure: str = ""
    file_count: int = 0
    line_count: int = 0
    readme_path: str | None = None


def load_config(config_path: str | None = None) -> dict:
    """读 stacks.toml。"""
    path = Path(config_path) if config_path else STACKS_CONFIG
    with open(path, "rb") as f:
        return tomllib.load(f)


def _iter_files(root: Path, config: dict):
    """遍历项目文件,跳过 ignore_dirs 和 ignore_files。"""
    ignore_dirs = set(config.get("ignore_dirs", {}).keys())
    ignore_files = set()
    for pat, _ in config.get("ignore_files", {}).items():
        ignore_files.add(pat)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ignore_dirs and not d.startswith(".")
                       and d not in ("node_modules", "target", "__pycache__",
                                     ".venv", "venv", "dist", "build", ".git")]
        for fn in filenames:
            if fn in ignore_files or fn.startswith("."):
                continue
            # 简单 glob: *.lock 等
            if any(_glob_match(pat, fn) for pat in ignore_files):
                continue
            yield Path(dirpath) / fn


def _glob_match(pattern: str, name: str) -> bool:
    if "*" not in pattern:
        return pattern == name
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def detect_language(root: Path, config: dict) -> tuple[str | None, dict[str, float]]:
    """扩展名统计→语言占比。返回(主语言, {语言:占比})。"""
    extensions = config.get("extensions", {})
    counts: dict[str, int] = {}
    total = 0
    for f in _iter_files(root, config):
        ext = f.suffix
        lang = extensions.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
            total += 1
    if not counts:
        return None, {}
    languages = {k: round(v / total, 3) for k, v in sorted(counts.items(), key=lambda x: -x[1])}
    main_lang = max(counts, key=counts.get)
    return main_lang, languages


def detect_tech_stack(root: Path, config: dict) -> tuple[list[str], list[str]]:
    """扫描构建文件,命中即认对应技术栈。返回(tech_stack, found_build_files)。"""
    build_files_cfg = config.get("build_files", {})
    tech_stack: list[str] = []
    found: list[str] = []
    for fname, info in build_files_cfg.items():
        # fname 可能是通配如 *.csproj
        if "*" in fname:
            import fnmatch
            matches = [p.name for p in root.rglob("*") if fnmatch.fnmatch(p.name, fname)]
            if matches:
                lang = info.get("language", "")
                if lang and lang not in tech_stack:
                    tech_stack.append(lang)
                for s in info.get("stack", []):
                    if s not in tech_stack:
                        tech_stack.append(s)
                found.extend(matches)
        else:
            p = root / fname
            if p.exists():
                lang = info.get("language", "")
                if lang and lang not in tech_stack:
                    tech_stack.append(lang)
                for s in info.get("stack", []):
                    if s not in tech_stack:
                        tech_stack.append(s)
                found.append(fname)
    return tech_stack, found


def extract_dir_structure(root: Path, depth: int = 3, config: dict | None = None) -> str:
    """生成目录树文本(前 depth 层)。"""
    ignore_dirs = set((config or {}).get("ignore_dirs", {}).keys()) if config else set()
    lines: list[str] = []
    _build_tree(root, "", depth, 0, ignore_dirs, lines, root)
    return "\n".join(lines)


def _build_tree(path: Path, prefix: str, max_depth: int, cur: int,
                ignore_dirs: set, lines: list[str], root: Path) -> None:
    if cur > max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return
    dirs = [e for e in entries if e.is_dir()]
    files = [e for e in entries if e.is_file()]
    # 只展示文件前若干个,避免过长
    show_files = files[:15]
    if len(files) > 15:
        show_files.append(None)  # type: ignore
    items = dirs + show_files
    for i, item in enumerate(items):
        if item is None:
            lines.append(f"{prefix}… ({len(files)-15} more files)")
            continue
        if item.is_dir():
            if item.name in ignore_dirs or item.name.startswith("."):
                continue
            rel = str(item.relative_to(root))
            lines.append(f"{prefix}{item.name}/")
            _build_tree(item, prefix + "  ", max_depth, cur + 1, ignore_dirs, lines, root)
        else:
            if item.name.startswith("."):
                continue
            lines.append(f"{prefix}{item.name}")


def find_entry_files(root: Path, language: str | None, config: dict) -> list[str]:
    """按语言找入口文件。"""
    if not language:
        return []
    hints = {
        "Rust": ["src/main.rs", "src/lib.rs", "main.rs"],
        "Python": ["__main__.py", "app.py", "main.py", "src/__main__.py"],
        "JavaScript": ["index.js", "src/index.js"],
        "TypeScript": ["index.ts", "src/index.ts"],
        "Go": ["main.go", "cmd/main.go"],
        "Java": ["src/main/java"],
        "C": ["main.c"],
        "C++": ["main.cpp"],
    }
    found = []
    for hint in hints.get(language, []):
        p = root / hint
        if p.exists():
            found.append(hint)
    return found


def find_readme(root: Path) -> str | None:
    """找 README(大小写不敏感)。"""
    for name in ["README.md", "README.rst", "README.txt", "README",
                 "readme.md", "readme.txt"]:
        p = root / name
        if p.exists():
            return str(p.relative_to(root))
    return None


def extract_dependencies(root: Path, language: str | None) -> list[str]:
    """从依赖文件提取关键依赖名(最小版:支持 Cargo.toml / requirements.txt)。"""
    deps: list[str] = []
    if language == "Rust":
        cargo = root / "Cargo.toml"
        if cargo.exists():
            try:
                text = cargo.read_text(encoding="utf-8")
                in_deps = False
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("[dependencies]") or s.startswith("[dev-dependencies]"):
                        in_deps = True
                        continue
                    if s.startswith("["):
                        in_deps = False
                        continue
                    if in_deps and "=" in s and not s.startswith("#"):
                        name = s.split("=")[0].strip()
                        if name:
                            deps.append(name)
            except Exception:
                pass
    elif language == "Python":
        req = root / "requirements.txt"
        if req.exists():
            try:
                for line in req.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if s and not s.startswith("#"):
                        deps.append(s.split("==")[0].split(">=")[0].split("<=")[0].strip())
            except Exception:
                pass
    return deps[:50]


def count_files_and_lines(root: Path, config: dict) -> tuple[int, int]:
    """统计代码文件数和总行数。"""
    extensions = set(config.get("extensions", {}).keys())
    extensions |= set(config.get("doc_extensions", {}).keys())
    file_count = 0
    line_count = 0
    for f in _iter_files(root, config):
        if f.suffix in extensions:
            file_count += 1
            try:
                line_count += sum(1 for _ in open(f, encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return file_count, line_count


def profile(root: str, name: str | None = None) -> ProjectProfile:
    """完整探测一个项目。"""
    root_path = Path(root).resolve()
    config = load_config()
    language, languages = detect_language(root_path, config)
    tech_stack, build_files = detect_tech_stack(root_path, config)
    entry_files = find_entry_files(root_path, language, config)
    readme = find_readme(root_path)
    dependencies = extract_dependencies(root_path, language)
    dir_structure = extract_dir_structure(root_path, 3, config)
    file_count, line_count = count_files_and_lines(root_path, config)
    return ProjectProfile(
        name=name or root_path.name,
        root_path=str(root_path),
        language=language,
        languages=languages,
        tech_stack=tech_stack,
        build_files=build_files,
        dependencies=dependencies,
        entry_files=entry_files,
        dir_structure=dir_structure[:2000],  # 截断防过长
        file_count=file_count,
        line_count=line_count,
        readme_path=readme,
    )
