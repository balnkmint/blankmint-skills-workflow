#!/usr/bin/env python3
"""Validate a slide-content Markdown file and its matching speaker notes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADING_RE = re.compile(r"^# 第(\d+)页｜(.+?)\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check page numbering and headings in paired PPT Markdown files."
    )
    parser.add_argument("content", type=Path, help="PPT content Markdown")
    parser.add_argument("speaker_notes", type=Path, help="Speaker notes Markdown")
    parser.add_argument(
        "--check-assets",
        action="store_true",
        help="Fail when an absolute local image path does not exist.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"file not found: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"not valid UTF-8: {path}") from exc


def collect_pages(text: str, path: Path) -> list[tuple[int, str]]:
    pages = [(int(number), title.strip()) for number, title in HEADING_RE.findall(text)]
    if not pages:
        raise ValueError(f"no page headings found in {path}")
    return pages


def check_page_numbers(pages: list[tuple[int, str]], label: str) -> list[str]:
    errors: list[str] = []
    numbers = [number for number, _ in pages]
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        errors.append(f"{label}: duplicate page numbers: {duplicates}")

    expected = list(range(1, len(pages) + 1))
    if numbers != expected:
        errors.append(f"{label}: page order is {numbers}, expected {expected}")
    return errors


def check_assets(text: str, source: Path) -> list[str]:
    errors: list[str] = []
    for target in IMAGE_RE.findall(text):
        candidate = target.strip().split(maxsplit=1)[0].strip("<>")
        if candidate.startswith(("http://", "https://", "data:")):
            continue
        asset = Path(candidate)
        if asset.is_absolute() and not asset.exists():
            errors.append(f"{source}: missing image asset: {asset}")
    return errors


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    try:
        content_text = read_text(args.content)
        notes_text = read_text(args.speaker_notes)
        content_pages = collect_pages(content_text, args.content)
        notes_pages = collect_pages(notes_text, args.speaker_notes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors.extend(check_page_numbers(content_pages, "PPT content"))
    errors.extend(check_page_numbers(notes_pages, "Speaker notes"))

    if content_pages != notes_pages:
        errors.append("page headings differ between the two files")
        max_pages = max(len(content_pages), len(notes_pages))
        for index in range(max_pages):
            content_page = content_pages[index] if index < len(content_pages) else None
            notes_page = notes_pages[index] if index < len(notes_pages) else None
            if content_page != notes_page:
                errors.append(
                    f"  position {index + 1}: content={content_page}, notes={notes_page}"
                )

    if args.check_assets:
        errors.extend(check_assets(content_text, args.content))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {len(content_pages)} pages; headings and order match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
