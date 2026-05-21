#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path("/Volumes/2TB/Marutake AudioBook Library")
READING_LIB = BASE_DIR / "Reading_library/納言恭平著"
TOOLS_DIR = BASE_DIR / "tools"

volumes_to_fix = [
    {"volume": 7, "file": "納言恭平　七之助捕物帳　第七巻.txt"},
    {"volume": 8, "file": "納言恭平　七之助捕物帳　第八巻.txt"},
]

for vol in volumes_to_fix:
    volume_num = vol["volume"]
    filename = vol["file"]
    source_file = READING_LIB / filename
    utf8_file = READING_LIB / f"納言恭平　七之助捕物帳　第{volume_num}巻_utf8.txt"
    
    print(f"📚 第{volume_num}巻 エンコーディング変換...")
    
    # Shift-JIS → UTF-8変換
    try:
        result = subprocess.run(
            ["iconv", "-f", "SHIFT_JIS", "-t", "UTF-8", str(source_file)],
            capture_output=True, text=True, check=True
        )
        with open(utf8_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        print(f"✅ UTF-8変換完了: {utf8_file.name}")
    except Exception as e:
        print(f"❌ 変換失敗: {e}")
        continue
    
    # BookData JSON作成
    print(f"📝 BookData JSON製作開始...")
    cmd = [
        "python3",
        str(TOOLS_DIR / "batch_create_shichino_series.py"),
        "--volume", str(volume_num),
        "--title", f"第{volume_num}巻",
        "--file", utf8_file.name
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        print(f"✅ 第{volume_num}巻 製作完了")
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: {e.stderr}")

print("\n製作完了！")
