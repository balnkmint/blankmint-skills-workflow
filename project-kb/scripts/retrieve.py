"""
retrieve.py — 检索网关

全文+结构化检索。语义检索为可选(需向量,默认不可用时 fallback 到全文)。
CLI、Web GUI、agent 都调本模块。
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import store
from summarizer import format_context


def search(query: str, mode: str = "hybrid", topk: int = 5) -> list[dict]:
    """统一检索入口。mode: keyword|semantic|hybrid。
    向量未接入时 semantic/hybrid 自动 fallback 到全文。"""
    if mode in ("semantic", "hybrid"):
        results = search_semantic(query, topk)
        if results:
            return results
        return search_keyword(query, topk)
    return search_keyword(query, topk)


def search_keyword(query: str, topk: int = 8) -> list[dict]:
    """FTS5 全文检索。"""
    return store.search_fts(query, topk)


def search_semantic(query: str, topk: int = 5) -> list[dict]:
    """语义检索。需向量(embed.py 已接入 + sqlite-vec)。
    默认未接入,返回空,调用方 fallback 到全文。"""
    try:
        import embed
        vec = embed.embed_text(query)
        if vec is None:
            return []
        return store.search_vector(vec, topk)
    except Exception:
        return []


def search_structured(sql: str) -> list[dict]:
    """结构化查询,直接转给 store.run_sql。"""
    return store.run_sql(sql)


def search_hybrid(query: str, topk: int = 5) -> list[dict]:
    """混合检索。向量可用时融合,否则 fallback 全文。"""
    return search(query, "hybrid", topk)


def rerank(results: list[dict], query: str) -> list[dict]:
    """可选重排(规模小可跳过)。"""
    return results


def format_results(results: list[dict], max_chars: int = 6000) -> str:
    """格式化检索结果为上下文文本(供 agent 问答用)。"""
    return format_context(results, max_chars)
