-- project-kb 数据库表结构
-- 存储: SQLite + FTS5 全文 + sqlite-vec 向量,一个 .db 文件搞定
-- 由 scripts/store.py init 执行

-- 启用 sqlite-vec 扩展(需在连接时先 load_extension)
-- .load ./vec0

-- ============================================================
-- 1. 项目元数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,              -- 项目名(目录名或指定)
    root_path       TEXT NOT NULL UNIQUE,      -- 项目根目录绝对路径
    language        TEXT,                      -- 主语言(占比最高)
    languages       TEXT,                      -- JSON: {"Rust": 0.85, "Python": 0.10, ...}
    tech_stack      TEXT,                      -- JSON: ["cargo", "tokio", "serde"]
    build_files     TEXT,                      -- JSON: ["Cargo.toml", "Makefile"]
    dependencies    TEXT,                      -- JSON: 关键依赖列表
    entry_files     TEXT,                      -- JSON: 入口文件路径
    dir_structure   TEXT,                      -- 目录树摘要(前2-3层)
    file_count      INTEGER DEFAULT 0,
    line_count      INTEGER DEFAULT 0,
    summary         TEXT,                      -- AI 生成的自然语言摘要(一段话)
    summary_struct  TEXT,                      -- JSON: 结构化摘要卡片
    ingested_at    TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_projects_language ON projects(language);

-- ============================================================
-- 2. 内容分块表(代码块/文档段落/配置等)
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    source_file     TEXT NOT NULL,             -- 相对项目根的路径
    chunk_type      TEXT NOT NULL,             -- code | doc | config | readme
    language        TEXT,                      -- 代码语言(文档块为NULL)
    symbol          TEXT,                      -- 函数/类/方法名(代码块),文档则为标题
    content         TEXT NOT NULL,             -- 块内容
    line_start      INTEGER,
    line_end        INTEGER,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(source_file);

-- ============================================================
-- 3. FTS5 全文索引(对 chunks.content 做关键词检索,内置 BM25)
-- ============================================================
-- content 表名为 chunks_fts,外部内容表指向 chunks
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    source_file,
    project_id UNINDEXED,
    content_rowid='id',
    tokenize='unicode61'   -- 中文需额外处理,见下方说明
);

-- 触发器: chunks 增删改时同步 FTS
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, source_file, project_id)
    VALUES (new.id, new.content, new.source_file, new.project_id);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, source_file, project_id)
    VALUES ('delete', old.id, old.content, old.source_file, old.project_id);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, source_file, project_id)
    VALUES ('delete', old.id, old.content, old.source_file, old.project_id);
    INSERT INTO chunks_fts(rowid, content, source_file, project_id)
    VALUES (new.id, new.content, new.source_file, new.project_id);
END;

-- 说明: unicode61 分词对中文是按字切分,够用但不完美。
-- 若需更好中文分词,可换 jieba 前置分词后入库,或用 trigram tokenizer:
--   tokenize='unicode61 remove_diacritics 2' + 后续优化

-- ============================================================
-- 4. 向量表(sqlite-vec,存 embedding)
-- ============================================================
-- 维度取决于模型:bge-m3 = 1024, bge-small-zh = 512
-- 这里用占位维度,store.py 建表时按实际模型维度创建
-- CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
--     id INTEGER PRIMARY KEY,
--     embedding FLOAT[1024]
-- );

-- ============================================================
-- 5. 元信息表(存 skill 配置/模型信息)
-- ============================================================
CREATE TABLE IF NOT EXISTS meta (
    key     TEXT PRIMARY KEY,
    value   TEXT
);
-- 示例键: embed_model, embed_dim, llm_model, version, created_at

-- ============================================================
-- 6. 入库历史(记录每次入库/更新操作,便于增量)
-- ============================================================
CREATE TABLE IF NOT EXISTS ingest_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER,
    action      TEXT,                          -- ingest | update | reindex
    status      TEXT,                          -- success | failed
    chunks_added INTEGER DEFAULT 0,
    error       TEXT,
    started_at  TEXT,
    finished_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
