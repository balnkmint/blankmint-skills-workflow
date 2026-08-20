"""
embed.py — 向量化(可选扩展)

引擎不含 AI,不内置 embedding 模型。
本模块提供接口框架,由使用方自行接入 embedding 来源(本地小模型或在线 API)。
默认不做向量化,引擎纯靠 FTS5 全文检索——对几十个项目完全够用。

如需语义检索(意思相近能查到),使用方需:
1. 实现 embed_text(text) -> list[float]
2. 在 store.py 启用 sqlite-vec 向量表 + add_embedding
3. retrieve.py 的 search_semantic 会自动启用
"""
from __future__ import annotations
import os

# 由使用方设置(环境变量或直接改)
EMBED_MODEL = os.environ.get("PKB_EMBED_MODEL")  # 默认 None=不启用


def get_model_info() -> dict:
    """返回 embedding 模型信息。默认未配置。"""
    return {"model": EMBED_MODEL, "dim": None}


def embed_text(text: str) -> list[float] | None:
    """单条文本→向量。

    默认返回 None(未接入),调用方应 fallback 到全文检索。
    使用方接入时在此实现(调本地小模型或在线 API)。
    """
    if not EMBED_MODEL:
        return None
    # TODO: 使用方接入 embedding 模型后实现
    # 示例(Ollama 本地小模型,不算大模型):
    #   import ollama
    #   return ollama.embeddings(model=EMBED_MODEL, prompt=text).embedding
    # 示例(在线 API):
    #   调用 OpenAI/其他 embedding API
    return None


def embed_batch(texts: list[str]) -> list[list[float] | None]:
    """批量向量化。默认返回全 None。"""
    return [embed_text(t) for t in texts]
