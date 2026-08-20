"""
server.py — FastAPI Web 服务

提供 Web GUI(检索+结构化查询+项目列表)和 REST API。
启动: python3 server.py  →  http://localhost:8787

引擎不含 AI——不做 AI 总结、不做 AI 问答,只做存储和检索。
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import store

app = FastAPI(title="project-kb", version="0.1.0")
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回 Web GUI 首页。"""
    html = WEB_DIR / "index.html"
    return html.read_text(encoding="utf-8")


@app.get("/api/projects")
async def api_projects():
    """列所有已入库项目。"""
    return store.list_projects()


@app.get("/api/project/{project_id}/chunks")
async def api_project_chunks(project_id: int):
    """返回某项目的全部内容块(完整 content)。"""
    return store.get_project_chunks(project_id)


@app.get("/api/search")
async def api_search(q: str, mode: str = "hybrid", topk: int = 8):
    """关键词检索。FTS5 前缀 + LIKE 兜底,中英文都能查。"""
    return store.search_fts(q, topk)


@app.get("/api/sql")
async def api_sql(sql: str):
    """结构化查询(只读 SELECT)。"""
    try:
        return store.run_sql(sql)
    except Exception as e:
        return {"error": str(e)}


def run(host: str = "127.0.0.1", port: int = 8787):
    """启动服务。"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
