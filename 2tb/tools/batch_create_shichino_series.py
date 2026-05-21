#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
七之助捕物帳シリーズ 自動製作システム

使用方法:
    python batch_create_shichino_series.py --start 30 --end 35

    または個別作成:
    python batch_create_shichino_series.py --volume 30 --title "お高祖頭巾" --file "納言恭平著七之助捕物帳 お高祖頭巾の女 .txt"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# プロジェクトルート
BASE_DIR = Path("/Volumes/2TB/Marutake AudioBook Library")
READING_LIBRARY = BASE_DIR / "Reading_library/納言恭平著"
BOOKDATA_DIR = BASE_DIR / "bookdata"
TOOLS_DIR = BASE_DIR / "tools"

# 既存ツールのインポート
sys.path.insert(0, str(TOOLS_DIR))


class ShichinoSeriesProducer:
    """七之助捕物帳シリーズ製作クラス"""

    def __init__(self):
        self.base_dir = BASE_DIR
        self.reading_library = READING_LIBRARY
        self.bookdata_dir = BOOKDATA_DIR
        self.tools_dir = TOOLS_DIR

        # タイトルフォーマット
        self.title_template = "七之助捕物帳 第{volume}巻【{subtitle}】納言恭平著　朗読七味春五郎　発行元丸竹書房"

        # 捕物帳メタデータテンプレート
        self.metadata_template = {
            "genre": "Mystery",
            "keywords": ["捕物帳", "江戸", "推理", "時代劇"],
            "japanese_genre": "捕物帳",
            "sub_genre": ["人情捕物帳", "推理捕物帳"],
            "themes": ["justice", "deduction", "edo_culture", "honor"],
            "emotions": ["tension", "warmth", "surprise", "humor"],
            "setting": {"period": "江戸時代", "location": "江戸（東京）"},
        }

    def find_source_file(
        self, volume_num: int, subtitle: Optional[str] = None
    ) -> Optional[Path]:
        """
        指定巻数に対応するソースファイルを検索

        Args:
            volume_num: 巻数
            subtitle: サブタイトル（オプション）

        Returns:
            ファイルパスまたはNone
        """
        # 既存の「第N巻」ファイルを探す
        patterns = [
            f"納言恭平　七之助捕物帳　第{volume_num}巻*.txt",
            f"納言恭平　七之助捕物帳　第{self._num_to_kanji(volume_num)}巻*.txt",
        ]

        # サブタイトルが指定されている場合
        if subtitle:
            patterns.extend(
                [
                    f"*{subtitle}*.txt",
                    f"七之助捕物帳*{subtitle}*.txt",
                    f"納言恭平*{subtitle}*.txt",
                ]
            )

        for pattern in patterns:
            files = list(self.reading_library.glob(pattern))
            if files:
                return files[0]

        return None

    def _num_to_kanji(self, num: int) -> str:
        """数字を漢数字に変換（1-99対応）"""
        kanji_map = {
            1: "一",
            2: "二",
            3: "三",
            4: "四",
            5: "五",
            6: "六",
            7: "七",
            8: "八",
            9: "九",
            10: "十",
        }

        if num <= 10:
            return kanji_map.get(num, str(num))
        elif num < 20:
            return "十" + kanji_map.get(num - 10, "")
        elif num < 100:
            tens = num // 10
            ones = num % 10
            result = kanji_map[tens] + "十"
            if ones > 0:
                result += kanji_map[ones]
            return result
        else:
            return str(num)

    def _kanji_to_num(self, kanji: str) -> str:
        """漢数字を数字文字列に変換"""
        try:
            if kanji.isdigit():
                return kanji

            kanji_map = {
                "一": "1",
                "二": "2",
                "三": "3",
                "四": "4",
                "五": "5",
                "六": "6",
                "七": "7",
                "八": "8",
                "九": "9",
                "十": "10",
            }

            # 単純な漢数字
            if kanji in kanji_map:
                return kanji_map[kanji]

            # 十の位がある場合
            if "十" in kanji:
                if kanji == "十":
                    return "10"
                elif kanji.startswith("十"):
                    return str(10 + int(kanji_map.get(kanji[1], "0")))
                else:
                    tens = int(kanji_map.get(kanji[0], "0"))
                    ones = int(kanji_map.get(kanji[2], "0")) if len(kanji) > 2 else 0
                    return str(tens * 10 + ones)

            return kanji
        except:
            return kanji

    def create_bookdata(
        self,
        volume_num: int,
        subtitle: str,
        source_file: Path,
        output_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        bookdata JSONを作成

        Args:
            volume_num: 巻数
            subtitle: サブタイトル
            source_file: ソーステキストファイル
            output_name: 出力ファイル名（オプション）

        Returns:
            作成されたJSONファイルパスまたはNone
        """
        # タイトル生成
        title = self.title_template.format(
            volume=self._num_to_kanji(volume_num), subtitle=subtitle
        )

        # 出力ファイル名
        if output_name is None:
            output_name = f"七之助捕物帳_第{volume_num:02d}巻_{subtitle}.json"

        output_path = self.bookdata_dir / output_name

        # メタデータ生成（LLMプロンプト使用）
        print(f"\n📝 Step 1: LLM用メタデータプロンプト生成")
        print(f"   ソース: {source_file.name}")

        # generate_meta_template.pyを使用
        meta_prompt_cmd = [
            "python3",
            str(self.tools_dir / "generate_meta_template.py"),
            str(source_file),
            "--title",
            title,
            "--author",
            "納言恭平",
            "--prompt",
        ]

        try:
            result = subprocess.run(
                meta_prompt_cmd, capture_output=True, text=True, check=True
            )
            prompt_text = result.stdout
            print(f"   ✅ プロンプト生成完了 ({len(prompt_text)} chars)")

            # プロンプトをファイルに保存
            prompt_file = self.tools_dir / f"prompt_vol{volume_num:02d}_{subtitle}.txt"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt_text)
            print(f"   📄 プロンプト保存: {prompt_file.name}")

        except subprocess.CalledProcessError as e:
            print(f"   ❌ エラー: {e.stderr}")
            return None

        # convert_to_bookdata.pyを使用してJSON作成
        print(f"\n📚 Step 2: bookdata JSON作成")

        # まず基本的なメタデータJSONを作成
        meta_json = self.metadata_template.copy()
        meta_json["keywords"].append(subtitle)

        # タイトル情報を追加（convert_to_bookdata.pyでマージされる）
        meta_json["title"] = title
        meta_json["author"] = "納言恭平"
        meta_json["narrator"] = "七味春五郎"
        meta_json["publisher"] = "丸竹書房"

        meta_file = self.tools_dir / f"meta_vol{volume_num:02d}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_json, f, ensure_ascii=False, indent=2)

        convert_cmd = [
            "python3",
            str(self.tools_dir / "convert_to_bookdata.py"),
            str(source_file),
            "--title",
            title,
            "--author",
            "納言恭平",
            "--meta",
            str(meta_file),
            "-o",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                convert_cmd, capture_output=True, text=True, check=True
            )
            print(f"   ✅ JSON作成完了: {output_path.name}")

            # 作成されたJSONを確認
            with open(output_path, "r", encoding="utf-8") as f:
                bookdata = json.load(f)

            print(f"\n   📊 作成内容:")
            print(f"      タイトル: {bookdata.get('title', 'N/A')}")
            print(f"      著者: {bookdata.get('author', 'N/A')}")
            print(f"      ジャンル: {bookdata.get('japanese_genre', 'N/A')}")
            print(f"      テーマ: {', '.join(bookdata.get('themes', []))}")
            print(f"      感情: {', '.join(bookdata.get('emotions', []))}")

            return output_path

        except subprocess.CalledProcessError as e:
            print(f"   ❌ エラー: {e.stderr}")
            return None

    def create_volume(
        self, volume_num: int, subtitle: str, source_file_name: Optional[str] = None
    ):
        """
        指定巻を製作

        Args:
            volume_num: 巻数
            subtitle: サブタイトル
            source_file_name: ソースファイル名（オプション）
        """
        print(f"\n{'='*70}")
        print(
            f"七之助捕物帳 第{self._num_to_kanji(volume_num)}巻【{subtitle}】製作開始"
        )
        print(f"{'='*70}")

        # ソースファイル探索
        if source_file_name:
            source_file = self.reading_library / source_file_name
            if not source_file.exists():
                print(f"❌ エラー: ファイルが見つかりません: {source_file_name}")
                return
        else:
            source_file = self.find_source_file(volume_num, subtitle)
            if not source_file:
                print(f"❌ エラー: 第{volume_num}巻のソースファイルが見つかりません")
                print(f"   サブタイトル: {subtitle}")
                return

        print(f"📖 ソースファイル: {source_file.name}")

        # bookdata JSON作成
        json_path = self.create_bookdata(volume_num, subtitle, source_file)

        if json_path:
            print(f"\n✅ 第{self._num_to_kanji(volume_num)}巻【{subtitle}】製作完了！")
            print(f"📄 出力: {json_path}")
            print(f"\n💡 次のステップ:")
            print(f"   1. WordPress管理画面 → JSON アップロード")
            print(f"   2. {json_path.name} をアップロード")
            print(f"   3. 投稿が自動作成されます（SEO最適化済み）")
        else:
            print(f"\n❌ 第{self._num_to_kanji(volume_num)}巻【{subtitle}】製作失敗")

    def batch_create(
        self, start_vol: int, end_vol: int, volume_mapping: Dict[int, Dict[str, str]]
    ):
        """
        複数巻を一括製作

        Args:
            start_vol: 開始巻数
            end_vol: 終了巻数
            volume_mapping: {巻数: {"subtitle": "サブタイトル", "file": "ファイル名"}}
        """
        print(f"\n{'='*70}")
        print(f"七之助捕物帳シリーズ 一括製作")
        print(f"第{start_vol}巻 ～ 第{end_vol}巻")
        print(f"{'='*70}")

        created = []
        failed = []

        for vol in range(start_vol, end_vol + 1):
            if vol not in volume_mapping:
                print(f"\n⚠️  第{vol}巻: マッピング情報なし、スキップ")
                continue

            mapping = volume_mapping[vol]
            subtitle = mapping.get("subtitle")
            source_file_name = mapping.get("file")

            if not subtitle:
                print(f"\n⚠️  第{vol}巻: サブタイトルなし、スキップ")
                continue

            try:
                self.create_volume(vol, subtitle, source_file_name)
                created.append(vol)
            except Exception as e:
                print(f"\n❌ 第{vol}巻 製作エラー: {e}")
                failed.append(vol)

        # サマリー
        print(f"\n{'='*70}")
        print(f"製作サマリー")
        print(f"{'='*70}")
        print(f"✅ 成功: {len(created)}巻 - {created}")
        if failed:
            print(f"❌ 失敗: {len(failed)}巻 - {failed}")
        print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="七之助捕物帳シリーズ 自動製作システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 個別作成
  python batch_create_shichino_series.py --volume 30 --title "お高祖頭巾" --file "納言恭平著七之助捕物帳 お高祖頭巾の女 .txt"
  
  # 一括作成（マッピングファイル使用）
  python batch_create_shichino_series.py --batch --mapping volume_mapping.json
        """,
    )

    parser.add_argument("--volume", type=int, help="巻数")
    parser.add_argument("--title", "--subtitle", dest="subtitle", help="サブタイトル")
    parser.add_argument("--file", help="ソーステキストファイル名")
    parser.add_argument("--batch", action="store_true", help="一括製作モード")
    parser.add_argument("--mapping", help="巻数マッピングJSONファイル")
    parser.add_argument("--start", type=int, help="一括製作開始巻数")
    parser.add_argument("--end", type=int, help="一括製作終了巻数")

    args = parser.parse_args()

    producer = ShichinoSeriesProducer()

    # 個別作成モード
    if args.volume and args.subtitle:
        producer.create_volume(args.volume, args.subtitle, args.file)

    # 一括作成モード
    elif args.batch and args.mapping:
        with open(args.mapping, "r", encoding="utf-8") as f:
            volume_mapping_raw = json.load(f)

        # JSONキーは文字列なので整数に変換
        volume_mapping = {int(k): v for k, v in volume_mapping_raw.items()}

        start_vol = args.start or min(volume_mapping.keys())
        end_vol = args.end or max(volume_mapping.keys())

        producer.batch_create(start_vol, end_vol, volume_mapping)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
