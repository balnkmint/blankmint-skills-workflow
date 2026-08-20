"""
ingest.py — 入库主流程

最小闭环版: 探测→解析→存库。跳过 AI 总结和向量化(后续补)。
"""
from __future__ import annotations
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import store
import profiler
from profiler import _iter_files, load_config
from parser_code import parse_file, is_code_file
from parser_doc import is_doc_file, parse_and_split


def _profile_to_meta(prof: profiler.ProjectProfile) -> dict:
    """ProjectProfile → store.add_project 需要的 dict(JSON 序列化 list/dict 字段)。"""
    return {
        "name": prof.name,
        "root_path": prof.root_path,
        "language": prof.language,
        "languages": json.dumps(prof.languages, ensure_ascii=False),
        "tech_stack": json.dumps(prof.tech_stack, ensure_ascii=False),
        "build_files": json.dumps(prof.build_files, ensure_ascii=False),
        "dependencies": json.dumps(prof.dependencies, ensure_ascii=False),
        "entry_files": json.dumps(prof.entry_files, ensure_ascii=False),
        "dir_structure": prof.dir_structure,
        "file_count": prof.file_count,
        "line_count": prof.line_count,
    }


def ingest_project(root: str, name: str | None = None,
                   db_path: str = store.DEFAULT_DB_PATH) -> dict:
    """完整入库一个项目,返回结果摘要。"""
    root_path = Path(root).resolve()
    if not root_path.exists():
        return {"status": "error", "error": f"路径不存在: {root_path}"}

    t0 = time.time()
    print(f"▶ 探测项目: {root_path}")
    prof = profiler.profile(str(root_path), name)
    print(f"  语言: {prof.language}  技术栈: {prof.tech_stack}")
    print(f"  代码文件: {prof.file_count}  总行数: {prof.line_count}")
    if prof.entry_files:
        print(f"  入口文件: {', '.join(prof.entry_files)}")

    # 建库 + 连接
    store.init_db(db_path)
    conn = store.connect(db_path)
    try:
        # 存项目(已存在则更新)
        meta = _profile_to_meta(prof)
        pid = store.add_project(meta, conn=conn)
        # 重新入库先清旧块
        conn.execute("DELETE FROM chunks WHERE project_id=?", (pid,))

        # 遍历解析所有文件
        config = load_config()
        all_chunks: list[dict] = []
        code_files = doc_files = 0
        for f in _iter_files(root_path, config):
            rel = str(f.relative_to(root_path))
            try:
                if is_code_file(f):
                    chunks = parse_file(f)
                    for ch in chunks:
                        ch["source_file"] = rel
                    all_chunks.extend(chunks)
                    code_files += 1
                elif is_doc_file(f):
                    chunks = parse_and_split(f)
                    for ch in chunks:
                        ch["source_file"] = rel
                    all_chunks.extend(chunks)
                    doc_files += 1
            except Exception as e:
                print(f"  ⚠ 解析失败 {rel}: {e}")

        # 批量入库
        n = store.add_chunks_batch(pid, all_chunks, conn=conn)
        conn.commit()
        store.log_ingest(pid, "ingest", "success", n, conn=conn)
        conn.commit()

        elapsed = time.time() - t0
        print(f"✓ 入库完成: {prof.name}")
        print(f"  代码文件 {code_files}  文档文件 {doc_files}  内容块 {n}")
        print(f"  耗时 {elapsed:.1f}s")
        return {
            "project_id": pid, "name": prof.name, "chunks": n,
            "code_files": code_files, "doc_files": doc_files,
            "elapsed": round(elapsed, 1), "status": "success",
        }
    except Exception as e:
        store.log_ingest(0, "ingest", "failed", 0, str(e), conn=conn)
        conn.commit()
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def ingest_inbox(inbox_dir: str = "inbox",
                 db_path: str = store.DEFAULT_DB_PATH) -> list[dict]:
    """扫描 inbox 下每个子目录,各自当独立项目入库。"""
    inbox = Path(inbox_dir)
    if not inbox.is_absolute():
        inbox = profiler.SKILL_ROOT / inbox_dir
    if not inbox.exists():
        print(f"inbox 不存在: {inbox}")
        return []
    results = []
    for sub in sorted(inbox.iterdir()):
        if sub.is_dir() and not sub.name.startswith("."):
            print(f"\n{'='*50}")
            r = ingest_project(str(sub), db_path=db_path)
            results.append(r)
    return results


def select_key_snippets(profile, chunks: list[dict], max_chars: int = 8000) -> list[str]:
    """选关键片段喂给总结器(最小闭环未用,留接口)。"""
    selected: list[str] = []
    total = 0
    # 优先入口文件和 README
    priority = []
    for ch in chunks:
        if ch.get("source_file") in (profile.entry_files or []):
            priority.append(ch)
    for ch in chunks:
        if ch.get("chunk_type") == "doc":
            priority.append(ch)
    for ch in chunks:
        if ch not in priority:
            priority.append(ch)
    for ch in priority:
        text = ch.get("content", "")
        if total + len(text) > max_chars:
            text = text[: max_chars - total]
        selected.append(text)
        total += len(text)
        if total >= max_chars:
            break
    return selected


def main():
    import argparse
    p = argparse.ArgumentParser(description="项目知识库入库")
    p.add_argument("--path", help="单个项目路径")
    p.add_argument("--name", help="项目名(默认用目录名)")
    p.add_argument("--inbox", help="inbox 目录(批量入库)")
    args = p.parse_args()
    if args.inbox:
        results = ingest_inbox(args.inbox)
        ok = sum(1 for r in results if r.get("status") == "success")
        print(f"\n批量入库完成: {ok}/{len(results)} 成功")
    elif args.path:
        r = ingest_project(args.path, args.name)
        if r.get("status") != "success":
            print(f"入库失败: {r.get('error')}")
            sys.exit(1)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
