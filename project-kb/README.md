# project-kb

通用项目知识库。把任意项目目录放进去,自动分析(探测技术栈、解析代码与文档)入库成可检索数据库。支持命令行、Web 界面、关键词/结构化查询。**引擎不含 AI**——不做 AI 总结,不做 AI 问答,只做存储和检索。纯本地,数据私有。

## 架构

```
项目放入 → 自动分析入库 → 存储 → 检索 → 三种访问方式
            │              │       │       │
       探测/解析         SQLite   全文/    CLI
       (不含AI)         +FTS5    结构化   Web GUI
                                          REST API
```

引擎不含 AI 推理——入库只做探测+解析+存储,不做 AI 总结;问答时引擎只检索,推理由使用它的 agent(Claude/其他)自己完成。这样引擎通用,任何 AI agent 都能用。

五层:
- **数据源**:原始项目目录(不动,find/grep 永远可用)
- **入库**:探测语言→多格式解析→存储(不含 AI)
- **存储**:SQLite(元数据+FTS5全文),一个 .db 文件
- **检索**:全文(BM25 前缀+LIKE 兜底)、结构化(SQL)
- **访问**:CLI / Web GUI / REST API

## 安装

### 1. 装系统依赖
- Python 3.10+
- LibreOffice(仅解析 .doc 老格式): `brew install libreoffice`

### 2. 装 Python 包
```bash
cd project-kb
pip install -r requirements.txt
```

### 3. 初始化数据库
```bash
python scripts/store.py init
```

## 用法

### 入库一个项目
```bash
python scripts/ingest.py --path /path/to/your/project
```

### 批量入库(把项目放进 inbox 目录)
```bash
mkdir -p inbox && cp -r /path/to/projectA inbox/
python scripts/ingest.py --inbox inbox
```

### 检索
```bash
# 全文检索(中英文)
python scripts/cli.py search "虚拟化隔离"

# 结构化查询
python scripts/cli.py sql "SELECT name, language, tech_stack FROM projects WHERE language='Rust'"

# 列出所有项目
python scripts/cli.py list
```

### 启动 Web GUI
```bash
python scripts/server.py
# 浏览器打开 http://localhost:8787
```
三个功能:检索(中英文搜索)、结构化查询(SQL)、项目列表(点"查看全部内容"展开所有内容块)。

### 数据库路径
默认 `project-kb/data/project_kb.db`。用环境变量改:
```bash
export PKB_DB_PATH=/your/path/project_kb.db
```
所有生成文件(数据库、启动脚本等)建议放同一个文件夹,不散乱。

## 引擎不含 AI 怎么做总结/问答

引擎不内置 AI。入库时不做 AI 总结。当 agent(Claude 等)收到项目相关问题时:

1. agent 调检索接口(CLI/API)拿相关片段
2. agent 自己基于片段思考、组织回答
3. 检索为空 → agent 说"未找到",不编造

用 Claude 就用 Claude 的能力,用别的 agent 就用那个 agent 的能力。引擎只提供"查",不提供"想"。

## 配置

- `config/stacks.toml`: 技术栈识别表,可扩展新语言(加构建文件→语言映射)
- `schema.sql`: 数据库表结构
- 数据库文件默认在 `project-kb/data/project_kb.db`(可用 `PKB_DB_PATH` 环境变量覆盖)

## 目录结构

```
project-kb/
├── SKILL.md                  # Claude skill 主指令
├── README.md                 # 本文件
├── requirements.txt
├── .gitignore
├── config/
│   ├── stacks.toml           # 技术栈识别表
│   └── summarize_prompt.txt  # (可选)总结参考 prompt
├── schema.sql                # 数据库表结构
├── scripts/
│   ├── store.py              # 存储层(SQLite+FTS5)
│   ├── profiler.py           # 项目探测
│   ├── parser_code.py        # 代码解析
│   ├── parser_doc.py         # 文档解析(markitdown)
│   ├── summarizer.py         # 选关键片段 + 格式化上下文
│   ├── embed.py              # 向量化(可选)
│   ├── ingest.py             # 入库主流程
│   ├── retrieve.py           # 检索网关
│   ├── cli.py                # CLI 入口
│   └── server.py             # FastAPI Web 服务
├── web/
│   └── index.html            # Web GUI
├── inbox/                    # 放项目进来自动入库(自动创建,git忽略)
└── data/                     # 数据库文件(自动创建,git忽略)
```

## 环境自适应

store.py 自动处理不同环境的 SQLite 写入:
- VM 沙箱挂载目录(如 Claude 桌面 bash 的 /Users 路径):用 `journal_mode=OFF` + 清理残留 journal
- 本地终端:任何路径都能写
- 用户给什么路径都能用,不用管环境差异

## License

MIT
