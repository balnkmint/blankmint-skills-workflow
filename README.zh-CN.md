# AI Agent Skills & Workflows

[English](./README.en.md) | [中文](./README.zh-CN.md)

---

## 关于

本仓库收录面向 AI Agent 的可复用工作流 Skill。每个 skill 是一套独立的指令集（一个 `SKILL.md` 加上可选的脚本和参考文件），引导 AI Agent 按结构化流程完成任务。这些 skill 不绑定特定工具——适用于 Claude、Cowork、ChatGPT、Gemini 或任何能读取 Markdown 的 AI 助手。

## 已有 Skill

| Skill | 说明 |
|-------|------|
| [offline-patch-workflow](./offline-patch-workflow/SKILL.md) | 本地分析并制作补丁，经用户传入堡垒机或无外网服务器应用、编译和验证，回传日志迭代；包含版本核对、离线依赖、正式分支迁移及无上下文交接模板。 |
| [ppt-markdown-workflow](./ppt-markdown-workflow) | 为技术分享创建并维护成对的 Markdown 文件——一份写幻灯片页面内容，一份写演讲讲稿——并自动校验页码、标题和素材引用的一致性。 |
| [code-analysis-workflow](./code-analysis-workflow) | 系统性阅读源码并生成结构化技术分析文档——调用链图、架构对比表、数据结构层次图，适用于从陌生代码库提炼架构和设计决策。 |
| [project-kb](./project-kb) | 通用项目知识库——把任意项目目录放入后自动分析（探测语言/技术栈、解析代码与文档含 docx/pdf）入库成可检索数据库，支持 CLI 检索和 Web 查询界面，引擎不含 AI，适用于任何 AI Agent。 |

## 使用方式

每个 skill 有两种使用方式：

**方式 A — 安装（推荐，适用于支持的工具）**

1. 下载或克隆本仓库。
2. 找到需要的 skill 文件夹（如 `ppt-markdown-workflow`）。
3. 安装到你的 AI 工具中：
   - 支持 skill 导入的工具：按工具自身的机制安装 `.skill` 包或将文件夹复制到 skills 目录，通过 `/skill名称` 触发。
4. 在对话中输入 `/skill名称` 或从菜单中选择即可触发。

**方式 B — 直接喂给任意 AI**

1. 打开 skill 的 `SKILL.md` 文件（以及引用的 `references/*.md` 或 `scripts/*.py` 等文件）。
2. 复制内容，粘贴到 AI 对话中作为系统提示或消息发送。
3. 开始描述你的任务，AI 会按照 skill 中定义的工作流执行。

这意味着你可以在任何 AI 聊天工具中使用这些 skill，无需安装。

## 打包 Skill

将 skill 打包为可安装的文件：

```bash
zip -r my-skill.skill my-skill/ -x "*.DS_Store"
```

## 贡献

欢迎提交 Issue 或 Pull Request，分享新的工作流 skill 或改进现有内容。

## License

MIT
