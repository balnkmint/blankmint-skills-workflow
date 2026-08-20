"""
parser_doc.py — 文档解析分块

用 markitdown 解析富文档(docx/pdf/pptx/xlsx/html),.md/.txt 直接读。
.doc 老格式用 LibreOffice 先转 .docx。
解析失败容错返回空,不中断入库。
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile

# 简单文本类文档(可直接读取,不走 markitdown 省开销)
_TEXT_EXTS = {".md", ".markdown", ".txt", ".rst", ".text"}
# 富文档(需 markitdown 解析)
_RICH_EXTS = {".docx", ".doc", ".pdf", ".pptx", ".xlsx", ".html", ".htm"}

# markitdown 实例缓存(复用,避免每次解析重建)
_MD = None


def _get_markitdown():
    """惰性初始化 markitdown 单例。"""
    global _MD
    if _MD is None:
        from markitdown import MarkItDown
        _MD = MarkItDown()
    return _MD


def is_doc_file(file_path: Path) -> bool:
    """判断是否文档文件(走文档解析器)。"""
    return file_path.suffix.lower() in (_TEXT_EXTS | _RICH_EXTS)


def convert_doc_to_docx(doc_path: Path) -> Path | None:
    """用 LibreOffice headless 把 .doc 转成 .docx,返回新路径。
    LibreOffice 不存在或转换失败返回 None。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print(f"  ⚠ LibreOffice 未安装,跳过 .doc: {doc_path.name}")
        return None
    # 转换到临时目录,再把结果复制到持久临时位置
    with tempfile.TemporaryDirectory() as td:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "docx",
                 "--outdir", td, str(doc_path)],
                capture_output=True, timeout=90, check=False,
            )
        except Exception as e:
            print(f"  ⚠ .doc 转换失败 {doc_path.name}: {e}")
            return None
        out = Path(td) / (doc_path.stem + ".docx")
        if out.exists() and out.stat().st_size > 0:
            persistent = Path(tempfile.gettempdir()) / f"pkb_{doc_path.stem}.docx"
            try:
                shutil.copy(out, persistent)
                return persistent
            except Exception:
                return None
    return None


def _markitdown_parse(file_path: Path) -> str:
    """用 markitdown 解析富文档→纯文本。失败返回空字符串。"""
    try:
        md = _get_markitdown()
        r = md.convert(str(file_path))
        return getattr(r, "text_content", "") or ""
    except Exception as e:
        print(f"  ⚠ markitdown 解析失败 {file_path.name}: {e}")
        return ""


def parse_doc(file_path: Path) -> str:
    """解析文档→纯文本。

    .md/.txt/.rst 直接读取;
    .docx/.pdf/.pptx/.xlsx/.html 用 markitdown;
    .doc 先转 .docx 再用 markitdown。
    """
    ext = file_path.suffix.lower()
    if ext in _TEXT_EXTS:
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    if ext == ".doc":
        docx = convert_doc_to_docx(file_path)
        if docx:
            return _markitdown_parse(docx)
        return ""
    if ext in _RICH_EXTS:
        return _markitdown_parse(file_path)
    return ""


def split_doc_chunks(content: str, source_file: str = "") -> list[dict]:
    """把纯文本按段落切。markdown 按标题或空行分段。"""
    if not content.strip():
        return []
    chunks: list[dict] = []
    lines = content.splitlines()
    current: list[str] = []
    current_title: str | None = None
    start_line = 1
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # markdown 标题作为分界
        if stripped.startswith("#"):
            if current:
                text = "\n".join(current).strip()
                if text:
                    chunks.append({
                        "chunk_type": "doc",
                        "language": None,
                        "symbol": current_title,
                        "content": text,
                        "line_start": start_line,
                        "line_end": i - 1,
                    })
            current = [line]
            current_title = stripped.lstrip("# ").strip() or None
            start_line = i
        elif stripped == "" and len(current) > 0:
            current.append(line)
            # 空行+累积够长就切一段
            if len("\n".join(current)) > 500:
                text = "\n".join(current).strip()
                if text:
                    chunks.append({
                        "chunk_type": "doc",
                        "language": None,
                        "symbol": current_title,
                        "content": text,
                        "line_start": start_line,
                        "line_end": i,
                    })
                current = []
                start_line = i + 1
        else:
            current.append(line)
    # 收尾
    if current:
        text = "\n".join(current).strip()
        if text:
            chunks.append({
                "chunk_type": "doc",
                "language": None,
                "symbol": current_title,
                "content": text,
                "line_start": start_line,
                "line_end": len(lines),
            })
    return chunks


def parse_and_split(file_path: Path) -> list[dict]:
    """对外统一入口: 文档→文本→块列表。"""
    text = parse_doc(file_path)
    return split_doc_chunks(text, str(file_path))
