"""
cli.py — 命令行入口

子命令: search / list / sql
引擎不含 AI——只做存储和检索,推理由使用它的 agent 自己完成。
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import store


def cmd_search(args) -> None:
    """关键词检索。"""
    results = store.search_fts(args.query, topk=args.topk)
    if not results:
        print("无匹配结果")
        return
    print(f"找到 {len(results)} 条结果:\n")
    for r in results:
        proj = r.get("project_name", "?")
        f = r.get("source_file", "?")
        sym = r.get("symbol")
        score = r.get("score", 0)
        header = f"【{proj}】{f}"
        if sym:
            header += f" · {sym}"
        header += f"  (分数: {score:.3f})"
        print(header)
        ls = r.get("line_start")
        le = r.get("line_end")
        if ls:
            print(f"  行 {ls}-{le}")
        content = r.get("content", "")
        preview = content[:400]
        for line in preview.splitlines():
            print(f"  {line}")
        if len(content) > 400:
            print(f"  …({len(content)} 字)")
        print()


def cmd_list(args) -> None:
    """列出所有项目。"""
    projects = store.list_projects()
    if not projects:
        print("还没有项目,用 ingest.py --path <路径> 入库")
        return
    print(f"共 {len(projects)} 个项目:\n")
    for p in projects:
        lang = p.get("language") or "?"
        stack = p.get("tech_stack") or []
        if isinstance(stack, str):
            import json
            try:
                stack = json.loads(stack)
            except Exception:
                stack = []
        print(f"[{p['id']}] {p['name']}  ({lang})")
        if stack:
            print(f"    技术栈: {', '.join(stack)}")
        print(f"    文件: {p.get('file_count', 0)}  行: {p.get('line_count', 0)}")
        if p.get("summary"):
            print(f"    摘要: {p['summary'][:120]}")


def cmd_sql(args) -> None:
    """结构化查询。"""
    results = store.run_sql(args.sql)
    if not results:
        print("无结果")
        return
    cols = list(results[0].keys())
    widths = [min(40, max([len(str(c))] + [len(str(r.get(c, ""))[:40]) for r in results])) for c in cols]
    header = " | ".join(str(c).ljust(w) for c, w in zip(cols, widths))
    print(header)
    print("-" * len(header))
    for r in results:
        print(" | ".join(str(r.get(c, ""))[:w].ljust(w) for c, w in zip(cols, widths)))


def main():
    p = argparse.ArgumentParser(
        prog="kquery",
        description="project-kb 项目知识库查询(引擎不含 AI)",
    )
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("search", help="关键词检索项目内容")
    s.add_argument("query", help="搜索词")
    s.add_argument("--topk", type=int, default=8, help="返回条数(默认8)")
    s.set_defaults(func=cmd_search)

    l = sub.add_parser("list", help="列出所有已入库项目")
    l.set_defaults(func=cmd_list)

    q = sub.add_parser("sql", help="结构化查询(SQL)")
    q.add_argument("sql", help="SELECT 语句")
    q.set_defaults(func=cmd_sql)

    args = p.parse_args()
    if not args.command:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
