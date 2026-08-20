# AI Agent Skills & Workflows

[中文](./README.zh-CN.md) | [English](./README.en.md)

---

## About

This repository curates reusable workflow skills for AI agents. Each skill is a self-contained set of instructions (a `SKILL.md` plus optional scripts and references) that guides an AI agent through a structured task. These skills are agent-agnostic — they work with Claude, Cowork, ChatGPT, Gemini, or any AI assistant that can read markdown.

## Available Skills

| Skill | Description |
|-------|-------------|
| [ppt-markdown-workflow](./ppt-markdown-workflow) | Draft and maintain paired Markdown files for technical presentations — one for slide content, one for speaker notes — with automated consistency checks. |
| [code-analysis-workflow](./code-analysis-workflow) | Systematically read source code and generate structured technical analysis docs — call chains, architecture diagrams, data structures, and design decisions. |
| [project-kb](./project-kb) | Universal project knowledge base — drop in any project directory to auto-analyze (detect language/tech stack, parse code and docs including docx/pdf) into a searchable database. CLI search + web UI. Engine contains no AI; works with any agent. |

## How to Use

There are two ways to use any skill in this repo:

**Option A — Install (recommended for supported tools)**

1. Download or clone this repository.
2. Locate the skill folder you want (e.g., `ppt-markdown-workflow`).
3. Install it into your AI tool:
   - Tools with skill import support: follow the tool's mechanism to install the `.skill` package or copy the folder into your skills directory. Trigger with `/skill-name`.
4. Trigger the skill by typing `/skill-name` or selecting it from the menu.

**Option B — Feed directly to any AI**

1. Open the skill's `SKILL.md` file (and any referenced files like `references/*.md` or `scripts/*.py`).
2. Copy the content and paste it into your AI conversation as a system prompt or message.
3. Start describing your task — the AI will follow the workflow defined in the skill.

This means you can use these skills with literally any AI chatbot, no installation required.

## Creating a Skill Package

To share a skill as an installable package:

```bash
zip -r my-skill.skill my-skill/ -x "*.DS_Store"
```

## Contributing

Feel free to submit issues or pull requests with new workflow skills or improvements to existing ones.

## License

MIT
