#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reports" / "umon_aozora_manifest.json"
DEST_DIR = ROOT / "Reading_library" / "右門捕物帖" / "青空文庫"

USER_AGENT = "GitHub-Copilot/umon-aozora-fetcher"


def safe_title(title: str) -> str:
    text = str(title or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")


def decode_best_effort(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def strip_aozora_headers(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = 0
    for idx, line in enumerate(lines):
        if "-------------------------------------------------------" in line:
            start = idx + 1
    if start:
        while start < len(lines) and not lines[start].strip():
            start += 1
        lines = lines[start:]
    return "\n".join(lines)


def strip_aozora_footers(text: str) -> str:
    markers = (
        "底本：",
        "入力：",
        "校正：",
        "このファイルは、インターネットの図書館",
        "作成ファイル：",
        "青空文庫作成ファイル：",
    )
    lines = text.split("\n")
    end = len(lines)
    for idx, line in enumerate(lines):
        if any(m in line for m in markers):
            end = idx
            break
    return "\n".join(lines[:end])


def clean_aozora_text(text: str) -> str:
    cleaned = text.replace("\ufeff", "").replace("\x00", "")
    cleaned = strip_aozora_headers(cleaned)
    cleaned = strip_aozora_footers(cleaned)
    cleaned = re.sub(r"［＃.*?］", "", cleaned)
    cleaned = re.sub(r"《.*?》", "", cleaned)
    cleaned = cleaned.replace("｜", "")
    cleaned = re.sub(r"※[^。\n]*", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def pick_text_member(zf: zipfile.ZipFile) -> str | None:
    names = [name for name in zf.namelist() if not name.endswith("/")]
    for suffix in (".txt", ".TXT"):
        for name in names:
            if name.endswith(suffix):
                return name
    return names[0] if names else None


def download_zip_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        member = pick_text_member(zf)
        if not member:
            raise ValueError("zip 内に本文ファイルが見つかりません")
        raw = zf.read(member)
    return decode_best_effort(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="右門捕物帖の青空本文を取得して整形保存する")
    parser.add_argument("--title", dest="titles", action="append", help="取得対象の作品名。複数指定可")
    parser.add_argument("--force", action="store_true", help="既存ファイルがあっても上書き")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = manifest.get("items", [])

    wanted = {str(t).strip() for t in (args.titles or []) if str(t).strip()}

    targets = [
        item
        for item in items
        if item.get("status") == "resolved"
        and item.get("aozora_text_url")
        and (not wanted or str(item.get("title", "")).strip() in wanted)
    ]

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed: list[str] = []

    for item in targets:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        out_path = DEST_DIR / f"右門捕物帖_{safe_title(title)}.txt"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        try:
            text = download_zip_text(str(item.get("aozora_text_url", "")).strip())
            out_path.write_text(clean_aozora_text(text), encoding="utf-8")
            downloaded += 1
            print(f"Downloaded: {out_path.relative_to(ROOT)}")
        except Exception as exc:
            failed.append(f"{title}: {exc}")

    print(f"Manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Destination: {DEST_DIR.relative_to(ROOT)}")
    print(f"Targets: {len(targets)}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("\n".join(failed[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
