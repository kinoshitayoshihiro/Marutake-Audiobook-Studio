from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "reports" / "zenigata_heiji_recording_state.json"
CATALOG_PATH = ROOT / "reports" / "zenigata_heiji_works_catalog.csv"


def normalize_state(raw: Any) -> dict[str, Any]:
    overrides: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        entries = raw.get("recording_overrides", [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                title = str(entry.get("title", "")).strip()
                if not title:
                    continue
                if "is_recorded" not in entry:
                    continue
                overrides.append(
                    {
                        "title": title,
                        "is_recorded": bool(entry.get("is_recorded")),
                        "note": str(entry.get("note", "")).strip(),
                        "updated_at": str(entry.get("updated_at", "")).strip(),
                    }
                )
    return {"recording_overrides": overrides}


def load_titles() -> set[str]:
    if not CATALOG_PATH.exists():
        return set()
    titles: set[str] = set()
    with CATALOG_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = str(row.get("title", "")).strip()
            if title:
                titles.add(title)
    return titles


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return normalize_state({})
    try:
        return normalize_state(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return normalize_state({})


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_override(
    state: dict[str, Any],
    title: str,
    is_recorded: bool,
    note: str,
) -> None:
    remaining = [
        entry
        for entry in state.get("recording_overrides", [])
        if str(entry.get("title", "")).strip() != title
    ]
    remaining.append(
        {
            "title": title,
            "is_recorded": is_recorded,
            "note": note,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["recording_overrides"] = remaining


def clear_override(state: dict[str, Any], title: str) -> None:
    state["recording_overrides"] = [
        entry
        for entry in state.get("recording_overrides", [])
        if str(entry.get("title", "")).strip() != title
    ]


def filtered_overrides(
    state: dict[str, Any],
    only_recorded: bool = False,
    only_unrecorded: bool = False,
) -> list[dict[str, Any]]:
    overrides = list(state.get("recording_overrides", []))
    if only_recorded:
        overrides = [entry for entry in overrides if bool(entry.get("is_recorded"))]
    if only_unrecorded:
        overrides = [entry for entry in overrides if not bool(entry.get("is_recorded"))]
    overrides.sort(key=lambda entry: str(entry.get("title", "")))
    return overrides


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="銭形平次捕物控の録音状態JSONを更新します。"
    )
    parser.add_argument(
        "--record",
        action="append",
        default=[],
        help="朗読済みにする作品名",
    )
    parser.add_argument(
        "--unrecord",
        action="append",
        default=[],
        help="未朗読に戻す作品名",
    )
    parser.add_argument(
        "--clear",
        action="append",
        default=[],
        help="手動更新を解除する作品名",
    )
    parser.add_argument("--note", default="", help="更新メモ")
    parser.add_argument("--list", action="store_true", help="現在の手動更新一覧を表示")
    parser.add_argument(
        "--list-recorded",
        action="store_true",
        help="手動更新のうち朗読済みだけ表示",
    )
    parser.add_argument(
        "--list-unrecorded",
        action="store_true",
        help="手動更新のうち未朗読だけ表示",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state = load_state()
    known_titles = load_titles()

    for title in args.record:
        normalized = title.strip()
        if not normalized:
            continue
        if known_titles and normalized not in known_titles:
            parser.error(f"作品名が見つかりません: {normalized}")
        update_override(state, normalized, True, args.note or "録音完了として更新")

    for title in args.unrecord:
        normalized = title.strip()
        if not normalized:
            continue
        if known_titles and normalized not in known_titles:
            parser.error(f"作品名が見つかりません: {normalized}")
        update_override(state, normalized, False, args.note or "未朗読として更新")

    for title in args.clear:
        normalized = title.strip()
        if not normalized:
            continue
        clear_override(state, normalized)

    save_state(state)

    if (
        args.list
        or args.list_recorded
        or args.list_unrecorded
        or args.record
        or args.unrecord
        or args.clear
    ):
        print(f"Wrote: {STATE_PATH.relative_to(ROOT)}")
        overrides = filtered_overrides(
            state,
            only_recorded=bool(args.list_recorded),
            only_unrecorded=bool(args.list_unrecorded),
        )
        print(f"Overrides: {len(overrides)}")
        for entry in overrides:
            status = "朗読済み" if entry.get("is_recorded") else "未朗読"
            print(
                f"- {entry.get('title', '')}: {status}"
                f" / {entry.get('updated_at', '')}"
            )
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
