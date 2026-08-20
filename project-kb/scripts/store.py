"""
store.py — 存储层

SQLite + FTS5 存储和检索。最小闭环版:不含 sqlite-vec 向量部分。
所有函数接受可选 conn 参数,入库时可复用同一连接提速。
"""
from __future__ import annotations
from typing import Any
import os
import sqlite3
import json
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = os.environ.get("PKB_DB_PATH", str(SKILL_ROOT / "data" / "project_kb.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    root_path       TEXT NOT NULL UNIQUE,
    language        TEXT,
    languages       TEXT,
    tech_stack      TEXT,
    build_files     TEXT,
    dependencies    TEXT,
    entry_files     TEXT,
    dir_structure   TEXT,
    file_count      INTEGER DEFAULT 0,
    line_count      INTEGER DEFAULT 0,
    summary         TEXT,
    summary_struct  TEXT,
    ingested_at     TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_projects_language ON projects(language);

CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    source_file     TEXT NOT NULL,
    chunk_type      TEXT NOT NULL,
    language        TEXT,
    symbol          TEXT,
    content         TEXT NOT NULL,
    line_start      INTEGER,
    line_end        INTEGER,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, source_file, project_id UNINDEXED, content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, source_file, project_id)
    VALUES (new.id, new.content, new.source_file, new.project_id);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, source_file, project_id)
    VALUES ('delete', old.id, old.content, old.source_file, old.project_id);
END;
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER, action TEXT, status TEXT,
    chunks_added INTEGER DEFAULT 0, error TEXT,
    started_at TEXT, finished_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""


def _resolve(db_path: str) -> str:
    p = Path(db_path)
    if not p.is_absolute():
        p = SKILL_ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _clean_db_files(db_path: str) -> None:
    """清理残留 journal/wal 文件(挂载目录不能删文件,truncate 到空)。"""
    for suffix in ("-journal", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            try:
                open(p, "w").close()
            except Exception:
                pass


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = _resolve(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        # 挂载目录(如 /Users 在 VM 沙箱)写不了 journal/锁,关掉以支持挂载路径写入
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
    except sqlite3.OperationalError:
        # 残留 journal 文件导致失败,清理后重试
        conn.close()
        _clean_db_files(path)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
    return conn


def _get(conn, db_path):
    return conn if conn is not None else connect(db_path)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """建库建表(首次)。"""
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('version','0.1.0')"
    )
    conn.commit()
    conn.close()


def add_project(meta: dict, conn=None, db_path: str = DEFAULT_DB_PATH) -> int:
    """插入项目元数据,返回 project_id。已存在(同 path)则更新。"""
    c = _get(conn, db_path)
    existing = c.execute(
        "SELECT id FROM projects WHERE root_path=?", (meta["root_path"],)
    ).fetchone()
    if existing:
        pid = existing["id"]
        c.execute(
            """UPDATE projects SET name=?,language=?,languages=?,tech_stack=?,
               build_files=?,dependencies=?,entry_files=?,dir_structure=?,
               file_count=?,line_count=? WHERE id=?""",
            (meta.get("name"), meta.get("language"), meta.get("languages"),
             meta.get("tech_stack"), meta.get("build_files"),
             meta.get("dependencies"), meta.get("entry_files"),
             meta.get("dir_structure"), meta.get("file_count", 0),
             meta.get("line_count", 0), pid),
        )
    else:
        cur = c.execute(
            """INSERT INTO projects(name,root_path,language,languages,tech_stack,
               build_files,dependencies,entry_files,dir_structure,file_count,line_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (meta.get("name"), meta.get("root_path"), meta.get("language"),
             meta.get("languages"), meta.get("tech_stack"), meta.get("build_files"),
             meta.get("dependencies"), meta.get("entry_files"),
             meta.get("dir_structure"), meta.get("file_count", 0),
             meta.get("line_count", 0)),
        )
        pid = cur.lastrowid
    if conn is None:
        c.commit()
        c.close()
    return pid


def add_chunk(project_id: int, chunk: dict, conn=None, db_path: str = DEFAULT_DB_PATH) -> int:
    """插入一个内容块,返回 chunk_id。FTS5 由触发器自动同步。"""
    c = _get(conn, db_path)
    cur = c.execute(
        """INSERT INTO chunks(project_id,source_file,chunk_type,language,symbol,
           content,line_start,line_end)
           VALUES (?,?,?,?,?,?,?,?)""",
        (project_id, chunk.get("source_file"), chunk.get("chunk_type", "code"),
         chunk.get("language"), chunk.get("symbol"), chunk.get("content"),
         chunk.get("line_start"), chunk.get("line_end")),
    )
    cid = cur.lastrowid
    if conn is None:
        c.commit()
        c.close()
    return cid


def add_chunks_batch(project_id: int, chunks: list[dict], conn=None, db_path: str = DEFAULT_DB_PATH) -> int:
    """批量插入块,返回插入数。复用连接,比循环调 add_chunk 快。"""
    c = _get(conn, db_path)
    rows = [(project_id, ch.get("source_file"), ch.get("chunk_type", "code"),
             ch.get("language"), ch.get("symbol"), ch.get("content"),
             ch.get("line_start"), ch.get("line_end")) for ch in chunks]
    c.executemany(
        """INSERT INTO chunks(project_id,source_file,chunk_type,language,symbol,
           content,line_start,line_end) VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    if conn is None:
        c.commit()
        c.close()
    return len(rows)


def update_project_summary(project_id: int, summary: str, summary_struct: dict | None = None,
                           conn=None, db_path: str = DEFAULT_DB_PATH) -> None:
    """回填项目摘要。"""
    c = _get(conn, db_path)
    c.execute(
        "UPDATE projects SET summary=?, summary_struct=? WHERE id=?",
        (summary, json.dumps(summary_struct, ensure_ascii=False) if summary_struct else None, project_id),
    )
    if conn is None:
        c.commit()
        c.close()


def get_project(project_id: int, conn=None, db_path: str = DEFAULT_DB_PATH) -> dict | None:
    c = _get(conn, db_path)
    row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if conn is None:
        c.close()
    return _row_to_dict(row)


def get_project_by_path(root_path: str, conn=None, db_path: str = DEFAULT_DB_PATH) -> dict | None:
    c = _get(conn, db_path)
    row = c.execute("SELECT * FROM projects WHERE root_path=?", (root_path,)).fetchone()
    if conn is None:
        c.close()
    return _row_to_dict(row)


def list_projects(conn=None, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    c = _get(conn, db_path)
    rows = c.execute("SELECT * FROM projects ORDER BY ingested_at DESC").fetchall()
    if conn is None:
        c.close()
    return [_row_to_dict(r) for r in rows]


def get_project_chunks(project_id: int, conn=None, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """返回某项目的所有内容块(完整 content)。"""
    c = _get(conn, db_path)
    rows = c.execute(
        """SELECT * FROM chunks WHERE project_id=? ORDER BY source_file, line_start""",
        (project_id,),
    ).fetchall()
    if conn is None:
        c.close()
    return [_row_to_dict(r) for r in rows]


def search_fts(query: str, topk: int = 8, conn=None, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """检索: FTS5 前缀匹配 + LIKE 兜底。
    FTS5 对整段中文 token 会漏部分词,LIKE 兜底补上。"""
    c = _get(conn, db_path)
    results: list[dict] = []
    seen: set = set()
    # 1. FTS5 前缀匹配(英文和 token 开头有效,带 BM25 分数)
    fts_query = _build_fts_query(query)
    try:
        rows = c.execute(
            """SELECT c.id, c.project_id, c.source_file, c.chunk_type, c.language,
                      c.symbol, c.content, c.line_start, c.line_end,
                      bm25(chunks_fts) AS score, p.name AS project_name
               FROM chunks_fts
               JOIN chunks c ON c.id = chunks_fts.rowid
               JOIN projects p ON p.id = c.project_id
               WHERE chunks_fts MATCH ?
               ORDER BY score LIMIT ?""",
            (fts_query, topk),
        ).fetchall()
        for r in rows:
            d = _row_to_dict(r)
            if d["id"] not in seen:
                results.append(d)
                seen.add(d["id"])
    except Exception:
        pass
    # 2. LIKE 兜底(中文部分词,FTS5 漏的)
    for term in _split_terms(query):
        if len(results) >= topk:
            break
        rows = c.execute(
            """SELECT c.id, c.project_id, c.source_file, c.chunk_type, c.language,
                      c.symbol, c.content, c.line_start, c.line_end,
                      -10.0 AS score, p.name AS project_name
               FROM chunks c JOIN projects p ON p.id = c.project_id
               WHERE c.content LIKE ? OR c.source_file LIKE ?
               LIMIT ?""",
            (f"%{term}%", f"%{term}%", topk),
        ).fetchall()
        for r in rows:
            d = _row_to_dict(r)
            if d["id"] not in seen:
                results.append(d)
                seen.add(d["id"])
            if len(results) >= topk:
                break
    if conn is None:
        c.close()
    return results[:topk]


def run_sql(sql: str, conn=None, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """执行只读 SELECT,返回结果列表。非 SELECT 拒绝。"""
    stripped = sql.strip().lower()
    if not stripped.startswith("select"):
        raise ValueError("只允许 SELECT 查询")
    c = _get(conn, db_path)
    rows = c.execute(sql).fetchall()
    if conn is None:
        c.close()
    return [_row_to_dict(r) for r in rows]


def delete_project(project_id: int, conn=None, db_path: str = DEFAULT_DB_PATH) -> None:
    """删除项目及其所有块(级联)。"""
    c = _get(conn, db_path)
    c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    if conn is None:
        c.commit()
        c.close()


def log_ingest(project_id: int, action: str, status: str, chunks_added: int = 0,
               error: str | None = None, conn=None, db_path: str = DEFAULT_DB_PATH) -> None:
    c = _get(conn, db_path)
    pid = project_id if project_id else None
    c.execute(
        """INSERT INTO ingest_log(project_id,action,status,chunks_added,error,started_at)
           VALUES (?,?,?,?,?,datetime('now','localtime'))""",
        (pid, action, status, chunks_added, error),
    )
    if conn is None:
        c.commit()
        c.close()


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    # JSON 字段反序列化
    for k in ("languages", "tech_stack", "build_files", "dependencies",
              "entry_files", "summary_struct"):
        if d.get(k) and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _build_fts_query(query: str) -> str:
    """FTS5 查询: 英文整词 + 中文2字前缀('词*')。
    前缀匹配能命中 token 开头的中文词;LIKE 兜底补漏。"""
    import re
    terms = [t for t in re.split(r"[\s,，。、;；?？!！]+", query.strip()) if t]
    if not terms:
        return f"{query}*"
    parts: list[str] = []
    for term in terms:
        if re.match(r"^[a-zA-Z0-9_-]{3,}$", term):
            parts.append(f"{term}*")
        elif len(term) <= 2:
            parts.append(f"{term}*")
        else:
            for i in range(len(term) - 1):
                parts.append(f"{term[i:i+2]}*")
    return " OR ".join(parts)


def _split_terms(query: str) -> list[str]:
    """分词用于 LIKE 查询(2字滑窗,宽松匹配)。"""
    import re
    terms = [t for t in re.split(r"[\s,，。、;；?？!！]+", query.strip()) if t]
    if not terms:
        return [query]
    result: list[str] = []
    for term in terms:
        if len(term) <= 2:
            result.append(term)
        else:
            for i in range(len(term) - 1):
                result.append(term[i:i + 2])
    return result
