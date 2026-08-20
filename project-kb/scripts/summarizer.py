"""
summarizer.py — 关键片段选取与上下文格式化

引擎不含 AI。本模块只负责:
1. 从入库的内容块里选出最有代表性的片段(供 agent 总结时用)
2. 把检索结果格式化成上下文文本(供 agent 问答时用)

AI 总结和问答由使用引擎的 agent(Claude/其他)自己完成。
"""
from __future__ import annotations
from profiler import ProjectProfile


def select_key_snippets(profile: ProjectProfile, chunks: list[dict],
                        max_chars: int = 8000) -> list[str]:
    """从所有块里选最有代表性的片段,供 agent 做项目总结时参考。

    优先级: 入口文件 > README/文档 > 最大代码块 > 配置。
    总字符控制在 max_chars 内(防止上下文过长)。
    """
    selected: list[str] = []
    total = 0
    priority: list[dict] = []
    # 入口文件优先
    for ch in chunks:
        if ch.get("source_file") in (profile.entry_files or []):
            priority.append(ch)
    # 文档次之
    for ch in chunks:
        if ch.get("chunk_type") == "doc" and ch not in priority:
            priority.append(ch)
    # 其余
    for ch in chunks:
        if ch not in priority:
            priority.append(ch)
    for ch in priority:
        text = ch.get("content", "")
        if total + len(text) > max_chars:
            text = text[: max_chars - total]
        if text:
            selected.append(text)
            total += len(text)
        if total >= max_chars:
            break
    return selected


def format_context(results: list[dict], max_chars: int = 6000) -> str:
    """把检索结果格式化成 agent 可用的上下文文本。

    每条: 【项目名/文件/符号】<内容>。
    总长截断在 max_chars。供 agent 问答时拼进自己的 prompt。
    """
    parts: list[str] = []
    total = 0
    for r in results:
        proj = r.get("project_name") or r.get("project_id") or "?"
        f = r.get("source_file", "?")
        sym = r.get("symbol")
        header = f"【{proj}】{f}"
        if sym:
            header += f" · {sym}"
        content = r.get("content", "")
        chunk_len = len(header) + len(content) + 2
        if total + chunk_len > max_chars:
            content = content[: max(0, max_chars - total - len(header) - 2)]
        parts.append(f"{header}\n{content}")
        total += chunk_len
        if total >= max_chars:
            break
    return "\n\n---\n\n".join(parts)
