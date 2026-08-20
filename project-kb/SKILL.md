---
name: project-kb
description: 通用项目知识库。把任意项目目录放入后自动分析(探测语言/技术栈、解析代码与文档含docx/pdf)入库成可检索数据库。支持CLI检索和Web查询界面(已实现)。引擎不含AI,不做AI总结问答,只做存储检索,AI能力由使用它的agent自己做。当用户说"项目入库""扫描项目""我的项目库里""知识库检索""项目库查询""分析这个项目"等时触发。
---

# project-kb — 通用项目知识库

把任意项目目录丢进来,自动探测语言/技术栈、解析代码和文档(含 docx/pdf)、入库成 SQLite+FTS5 可检索数据库。支持 CLI 检索 + Web 查询界面。引擎不含 AI——不做 AI 总结,不做 AI 问答,只做存储和检索。

## 定位脚本目录(每次使用前先做)

project-kb 的脚本目录按以下顺序查找,找到即用,记为 `KB`:

1. 环境变量 `PKB_HOME`(非空就用): `echo $PKB_HOME`
2. `~/project-kb` 目录存在就用: `test -d ~/project-kb && echo ~/project-kb`
3. 当前目录或上级目录有 `project-kb` 子目录就用
4. 都找不到 → 问用户 project-kb 目录的绝对路径,记住

找到后,所有脚本在 `$KB/scripts/` 下。下面命令里的 `$KB` 替换成实际找到的路径。

## database 文件夹(入库前必问用户,所有生成文件集中存放)

**每次新对话第一次入库前,问用户 database 文件夹。** 问法:

> "所有生成的文件(数据库、启动脚本等)保存到哪个文件夹？默认是 $KB/data/，你也可以指定别的文件夹。"

- 用户给文件夹路径 → 该文件夹为**所有生成文件的存放处**。数据库文件名为 `project_kb.db` 放该文件夹下,设 `export PKB_DB_PATH=<文件夹>/project_kb.db`
- 用户说"用默认"/"随便" → 用 `$KB/data/`,`export PKB_DB_PATH=$KB/data/project_kb.db`
- **重要:所有生成的文件(数据库 .db、启动脚本 .command、临时文件等)都必须放这个文件夹,不要散落到项目目录根、home 或其他地方**
- store.py 自动处理各种环境的 SQLite 写入(包括 VM 沙箱挂载目录),用户给 `/Users/` 路径也能直接写

## 依赖(必须装,别跳过)

project-kb 需要:
- `tomli` — Python 3.10 没有 tomllib(3.11+ 才有),**必须装**
- `markitdown` — 解析 docx/pdf/pptx/xlsx 富文档需要
- `fastapi` + `uvicorn` — Web 查询界面需要

装:
```bash
pip install tomli 'markitdown[all]' fastapi uvicorn --break-system-packages
```
装失败要看错误信息处理。别跟用户说"不需要装依赖"——tomli 是必须的。

## 核心命令(CLI)

### 入库一个项目
```bash
python3 $KB/scripts/ingest.py --path <项目目录> [--name <项目名>]
```
自动探测→解析代码和文档→入库。完成后报告语言/技术栈/块数/库路径。

### 关键词检索
```bash
python3 $KB/scripts/cli.py search "<query>" [--topk 8]
```
FTS5 前缀匹配 + LIKE 兜底,中英文都能查到。

### 结构化查询(SQL)
```bash
python3 $KB/scripts/cli.py sql "<SELECT ...>"
```

### 列出所有项目
```bash
python3 $KB/scripts/cli.py list
```

## Web 查询界面(已实现,启动即用)

```bash
python3 $KB/scripts/server.py
```
浏览器打开 http://localhost:8787。三个功能:
- **检索**: 搜索框,中英文关键词检索
- **结构化查询**: SQL 输入框 + 表格结果
- **项目列表**: 浏览所有已入库项目,点"查看全部内容"展开显示该项目的所有内容块

启动前确保 `PKB_DB_PATH` 已设(和入库时同一个库)。

API 端点(也可被其他程序/agent 调用):
- `GET /api/projects` — 列所有项目
- `GET /api/search?q=<词>&topk=<n>` — 关键词检索
- `GET /api/project/{id}/chunks` — 某项目全部内容块
- `GET /api/sql?sql=<SELECT...>` — 结构化查询

## 你的工作流

### 用户说"把 XXX 入库"/"扫描项目"
1. 定位 project-kb 目录(上面的查找逻辑),确定 `KB`
2. 装依赖(如果还没装)
3. **问用户 database 文件夹**(如果这次对话还没问过)。用户给文件夹后 `export PKB_DB_PATH=<文件夹>/project_kb.db`;说用默认就 `$KB/data/project_kb.db`。**记住:所有生成文件都放这个文件夹。**
4. 确认项目路径(用户只给名字就问绝对路径)
5. 跑 `python3 $KB/scripts/ingest.py --path <路径>`
6. 报告:识别到什么语言/技术栈、共几个项目、多少块、库路径
7. 失败则读错误、定位原因、指导修复,不要静默失败

### 用户问项目内容("我那个 X 怎么做的 Y")
1. 确认库路径已设(没问过就走上面的问文件夹流程)
2. **先检索,不要凭记忆答**: `python3 $KB/scripts/cli.py search "<关键词>"`
3. 检索为空 → 明确告诉用户"知识库中未找到相关内容",不编造。如果库文件不存在或为空,提示用户先入库。
4. 有结果 → 你基于检索到的片段自己思考、组织回答,可引用来源(项目名/文件/行号)
5. 用户问题不明确 → 先列出库里匹配的项目让用户确认

### 用户说"库里有哪些项目"/"列出所有项目"
先确认库路径,跑 `python3 $KB/scripts/cli.py list`。

### 用户要浏览器查询/web 界面
确保 PKB_DB_PATH 已设,跑 `python3 $KB/scripts/server.py`,告诉用户浏览器打开 http://localhost:8787。
如果用户要启动脚本(.command),生成到用户的 database 文件夹里。

## 重要原则

- **检索优先**:涉及项目内容的问题,必须先调检索,不凭自身记忆回答库里有什么。
- **不编造**:检索为空就说没有,不"根据通用知识"补充。
- **引擎不含 AI**:不做 AI 总结,不做 AI 问答。引擎只存储和检索,推理由使用它的 agent 自己完成。这是全 AI agent 通用的关键。
- **通用不预设语言**:入库自动探测,不假设项目是某种特定语言。
- **保留原始文件**:入库只读不改,原始目录永远在,用户随时能 find/grep。
- **环境自适应**:store.py 自动处理不同环境的 SQLite 写入。
- **文件不散乱**:所有生成文件放用户指定的 database 文件夹,不散落到别处。
