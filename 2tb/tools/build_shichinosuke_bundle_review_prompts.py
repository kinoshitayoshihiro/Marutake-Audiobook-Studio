#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shichinosuke_catalog_builder_impl import BUNDLE_REVIEW_QUEUE_PATH, ROOT

DEFAULT_OUTPUT_DIR = ROOT / "reports" / "shichinosuke_bundle_review_prompts"
DEFAULT_INDEX_PATH = ROOT / "reports" / "shichinosuke_bundle_review_prompts.md"
DEFAULT_JSONL_PATH = ROOT / "reports" / "shichinosuke_bundle_review_prompts.jsonl"


def resolve_report_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="七之助の総集編 bundle 審査プロンプトを生成する"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=BUNDLE_REVIEW_QUEUE_PATH,
        help="bundle review queue JSON のパス",
    )
    parser.add_argument(
        "--bundle-id",
        action="append",
        default=[],
        help="対象 bundle_id（複数指定可）",
    )
    parser.add_argument(
        "--bundle-group",
        choices=["classification", "sequential", "all"],
        default="all",
        help="対象 bundle group",
    )
    parser.add_argument(
        "--tier",
        choices=["primary", "alternate", "all"],
        default="primary",
        help="対象 candidate tier",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="先頭から何件生成するか。0 は無制限",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="個別 prompt を書くディレクトリ",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help="生成一覧 Markdown の出力先",
    )
    parser.add_argument(
        "--jsonl-path",
        type=Path,
        default=DEFAULT_JSONL_PATH,
        help="LLM 連携向け JSONL の出力先",
    )
    return parser.parse_args()


def load_review_queue(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_filename(value: str) -> str:
    invalid = str.maketrans(
        {
            "/": "_",
            "\\": "_",
            ":": "_",
            "*": "_",
            "?": "_",
            '"': "_",
            "<": "_",
            ">": "_",
            "|": "_",
            " ": "_",
        }
    )
    return value.translate(invalid)


def select_items(
    items: list[dict[str, Any]],
    *,
    bundle_ids: list[str],
    bundle_group: str,
    tier: str,
    limit: int,
) -> list[dict[str, Any]]:
    selected = items
    if bundle_ids:
        bundle_id_set = set(bundle_ids)
        selected = [
            item for item in selected if str(item.get("bundle_id", "")) in bundle_id_set
        ]
    if bundle_group != "all":
        selected = [
            item for item in selected if item.get("bundle_group") == bundle_group
        ]
    if tier != "all":
        selected = [item for item in selected if item.get("candidate_tier") == tier]
    if limit > 0:
        selected = selected[:limit]
    return selected


def format_list(items: list[str], fallback: str = "なし") -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return " / ".join(cleaned) if cleaned else fallback


def build_prompt_text(item: dict[str, Any]) -> str:
    works = item.get("works", [])
    work_sections: list[str] = []
    for index, work in enumerate(works, start=1):
        work_sections.extend(
            [
                f"### 作品{index}",
                f"- 通し番号: {work.get('serial_number', '-')}",
                f"- タイトル: {work.get('title', '')}",
                f"- 短縮タイトル: {work.get('short_title', '')}",
                f"- 大分類: {work.get('major_category', '')}",
                f"- 小分類: {format_list(work.get('minor_categories', []), 'なし')}",
                f"- themes: {format_list(work.get('themes', []), 'なし')}",
                f"- characters: {format_list(work.get('characters', []), 'なし')}",
                f"- 本文参照: {format_list(work.get('text_paths', []), '本文パスなし')}",
                f"- bookdata: {work.get('bookdata_path', '')}",
                f"- synopsis: {work.get('synopsis', '')}",
                "",
            ]
        )

    return "\n".join(
        [
            f"# 総集編審査プロンプト: {item.get('label', '')}",
            "",
            "## 役割",
            "あなたは江戸捕物帳シリーズの編集者兼アーカイバーです。",
            "総集編候補として選ばれた3作品が、本当に同一テーマ総集編として自然かを判定してください。",
            "",
            "## 審査対象 bundle",
            f"- bundle_id: {item.get('bundle_id', '')}",
            f"- group: {item.get('bundle_group', '')}",
            f"- 候補区分: {item.get('candidate_tier', '')}",
            f"- 候補区分理由: {item.get('candidate_tier_reason', '')}",
            f"- 公開優先度: {item.get('publication_priority', '')}",
            f"- 公開理由: {item.get('publication_reason', '')}",
            f"- 推奨タイトル案: {item.get('recommended_title', '')}",
            f"- 大分類: {item.get('major_category', '')}",
            f"- 小分類: {item.get('minor_category', '')}",
            f"- Python要約: {item.get('summary', '')}",
            "",
            "## 判定ルール",
            "- 3作品の中心テーマが本当に揃っているかを最優先で判断する。",
            "- synopsis と themes を主に使い、必要に応じて text_paths の本文参照先も根拠に使う。",
            "- 単なるキーワード一致ではなく、事件構造・感情の軸・見せ場の共通性を見る。",
            "- 1作品だけ明らかに浮いている場合は、不一致として扱ってよい。",
            "- 代替案を出す場合は、差し替え意図も明記する。",
            "",
            "## 出力形式",
            "以下のJSONだけを返してください。",
            "",
            "```json",
            "{",
            '  "bundle_id": "...",',
            '  "label": "...",',
            '  "decision": "approve | revise | reject",',
            '  "score": 1,',
            '  "reason": "2〜6文で判定理由",',
            '  "theme_consistency": {',
            '    "shared_core": "3作品に共通する中心テーマ",',
            '    "notes": ["観点1", "観点2"]',
            "  },",
            '  "work_assessment": [',
            '    {"title": "...", "fit": "high | medium | low", "comment": "..."}',
            "  ],",
            '  "suggested_title": "必要なら改善した総集編タイトル",',
            '  "replacement_plan": {',
            '    "needed": false,',
            '    "replace_out": "",',
            '    "replace_in_hint": "",',
            '    "reason": ""',
            "  }",
            "}",
            "```",
            "",
            "## 作品データ",
            *work_sections,
        ]
    )


def build_jsonl_record(item: dict[str, Any], prompt_text: str) -> dict[str, Any]:
    return {
        "bundle_id": item.get("bundle_id", ""),
        "bundle_group": item.get("bundle_group", ""),
        "label": item.get("label", ""),
        "candidate_tier": item.get("candidate_tier", ""),
        "recommended_title": item.get("recommended_title", ""),
        "publication_priority": item.get("publication_priority", ""),
        "prompt": prompt_text,
    }


def write_outputs(
    items: list[dict[str, Any]],
    *,
    output_dir: Path,
    index_path: Path,
    jsonl_path: Path,
) -> None:
    output_dir = resolve_report_path(output_dir)
    index_path = resolve_report_path(index_path)
    jsonl_path = resolve_report_path(jsonl_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# 七之助 総集編 LLM審査プロンプト一覧",
        "",
        f"- 件数: {len(items)}",
        f"- 出力ディレクトリ: {output_dir.relative_to(ROOT).as_posix()}",
        "",
    ]
    jsonl_lines: list[str] = []

    for item in items:
        file_name = sanitize_filename(
            f"{item.get('candidate_tier', 'primary')}_{item.get('bundle_id', 'bundle')}"
        )
        prompt_path = output_dir / f"{file_name}.md"
        prompt_text = build_prompt_text(item)
        prompt_path.write_text(prompt_text, encoding="utf-8")

        index_lines.extend(
            [
                f"## {item.get('label', '')}",
                "",
                f"- bundle_id: {item.get('bundle_id', '')}",
                f"- 候補区分: {item.get('candidate_tier', '')}",
                f"- 推奨タイトル案: {item.get('recommended_title', '')}",
                f"- ファイル: {prompt_path.relative_to(ROOT).as_posix()}",
                "",
            ]
        )
        jsonl_lines.append(
            json.dumps(
                build_jsonl_record(item, prompt_text),
                ensure_ascii=False,
            )
        )

    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    jsonl_path.write_text("\n".join(jsonl_lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    items = load_review_queue(args.input)
    output_dir = resolve_report_path(args.output_dir)
    index_path = resolve_report_path(args.index_path)
    jsonl_path = resolve_report_path(args.jsonl_path)
    selected = select_items(
        items,
        bundle_ids=args.bundle_id,
        bundle_group=args.bundle_group,
        tier=args.tier,
        limit=args.limit,
    )
    write_outputs(
        selected,
        output_dir=output_dir,
        index_path=index_path,
        jsonl_path=jsonl_path,
    )
    print(f"Wrote: {index_path.relative_to(ROOT)}")
    print(f"Wrote: {jsonl_path.relative_to(ROOT)}")
    print(f"Wrote dir: {output_dir.relative_to(ROOT)}")
    print(f"Prompts: {len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
