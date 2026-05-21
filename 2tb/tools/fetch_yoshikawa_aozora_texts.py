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
MANIFEST_PATH = ROOT / "reports" / "yoshikawa_aozora_manifest.json"
DEST_DIR = ROOT / "Reading_library" / "吉川英治" / "青空文庫"

USER_AGENT = "GitHub-Copilot/yoshikawa-aozora-fetcher"


def safe_title(title: str) -> str:
    text = str(title or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")


def decode_best_effort(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def strip_aozora_headers(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = 0
    for index, line in enumerate(lines):
        if "-------------------------------------------------------" in line:
            start = index + 1
    if start:
        while start < len(lines) and not lines[start].strip():
            start += 1
        lines = lines[start:]
    return "\n".join(lines)


def strip_aozora_footers(text: str) -> str:
    footer_markers = (
        "底本：",
        "入力：",
        "校正：",
        "このファイルは、インターネットの図書館",
        "作成ファイル：",
        "青空文庫作成ファイル：",
    )
    lines = text.split("\n")
    end = len(lines)
    for index, line in enumerate(lines):
        if any(marker in line for marker in footer_markers):
            end = index
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


def pick_text_member(archive: zipfile.ZipFile) -> str | None:
    names = [name for name in archive.namelist() if not name.endswith("/")]
    for suffix in (".txt", ".TXT"):
        for name in names:
            if name.endswith(suffix):
                return name
    return names[0] if names else None


def download_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        member = pick_text_member(archive)
        if not member:
            raise ValueError("zip 内に本文ファイルが見つかりません")
        raw = archive.read(member)
    return decode_best_effort(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="青空文庫の吉川英治本文を取得し、ローカル保存します。")
    parser.add_argument("--title", dest="titles", action="append", help="取得対象の作品名。複数回指定可。")
    parser.add_argument("--force", action="store_true", help="既存ファイルがあっても上書き取得します。")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    wanted_titles = {str(title).strip() for title in (args.titles or []) if str(title).strip()}

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed: list[str] = []
    for item in items:
        title = str(item.get("title", "")).strip()
        if wanted_titles and title not in wanted_titles:
            continue
        matches = item.get("aozora_matches", [])
        if not isinstance(matches, list) or not matches:
            continue

        if len(matches) == 1:
            match = matches[0]
            destination = DEST_DIR / f"吉川英治_{safe_title(title)}.txt"
            targets = [(match, destination)]
        else:
            series_dir = DEST_DIR / safe_title(title)
            series_dir.mkdir(parents=True, exist_ok=True)
            targets = []
            for index, match in enumerate(matches, start=1):
                subtitle = str(match.get("subtitle", "")).strip() or f"part_{index:02d}"
                destination = series_dir / f"{index:02d}_{safe_title(subtitle)}.txt"
                targets.append((match, destination))

        for match, destination in targets:
            if destination.exists() and not args.force:
                skipped += 1
                continue
            text_url = str(match.get("text_url", "")).strip()
            if not text_url:
                failed.append(f"{title}: text_url が空です")
                continue
            try:
                text = download_text(text_url)
                destination.write_text(clean_aozora_text(text), encoding="utf-8")
                downloaded += 1
                print(f"Downloaded: {destination.relative_to(ROOT)}")
            except Exception as exc:
                failed.append(f"{title}: {destination.name}: {exc}")

    print(f"Manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Destination: {DEST_DIR.relative_to(ROOT)}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("\n".join(failed[:20]))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())