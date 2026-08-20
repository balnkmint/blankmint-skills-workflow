"""
parser_code.py — 代码解析分块(最小版)

最小闭环: 不依赖 tree-sitter,直接按行数切分。
后续填实现时换 tree-sitter 精确切函数,接口不变。
"""
from __future__ import annotations
from pathlib import Path

SYMBOL_NODE_TYPES: dict[str, set[str]] = {
    "Rust": {"function_item", "impl_item", "struct_item", "enum_item", "trait_item"},
    "Python": {"function_definition", "class_definition"},
    "JavaScript": {"function_declaration", "class_declaration"},
    "TypeScript": {"function_declaration", "class_declaration"},
    "Go": {"function_declaration", "method_declaration", "type_declaration"},
    "Java": {"method_declaration", "class_declaration"},
}

# 扩展名→语言(与 profiler 配置一致,本地缓存避免循环依赖)
_EXT_LANG = {
    ".rs": "Rust", ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++",
    ".hpp": "C++", ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".sh": "Shell", ".bash": "Shell", ".lua": "Lua", ".scala": "Scala",
    ".clj": "Clojure", ".hs": "Haskell", ".zig": "Zig", ".ex": "Elixir",
}


def get_parser(language: str):
    """tree-sitter parser(最小版未实现,返回 None)。"""
    return None


def split_code_chunks(file_path: Path, language: str) -> list[dict]:
    """解析源文件→代码块。最小版走 fallback_split。"""
    return fallback_split(file_path, language)


def fallback_split(file_path: Path, language: str | None, max_lines: int = 60) -> list[dict]:
    """按行数切分(每 max_lines 一块)。简单但通用,任何语言都能用。

    改进点(后续): 按 tree-sitter 的函数/类节点切分,每块是一个完整函数。
    """
    chunks: list[dict] = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return chunks
    lines = text.splitlines()
    if not lines:
        return chunks
    for i in range(0, len(lines), max_lines):
        block = "\n".join(lines[i:i + max_lines])
        chunks.append({
            "chunk_type": "code",
            "language": language,
            "symbol": None,
            "content": block,
            "line_start": i + 1,
            "line_end": min(i + max_lines, len(lines)),
        })
    return chunks


def parse_file(file_path: Path, language: str | None = None) -> list[dict]:
    """对外统一入口:给定文件返回代码块列表。

    每块附 source_file(相对路径,由调用方填)。
    语言未知时按扩展名猜。
    """
    if language is None:
        language = _EXT_LANG.get(file_path.suffix)
    if language is None:
        return []  # 非代码文件,跳过
    return split_code_chunks(file_path, language)


def is_code_file(file_path: Path) -> bool:
    """判断是否代码文件(走代码解析器)。"""
    return file_path.suffix in _EXT_LANG
