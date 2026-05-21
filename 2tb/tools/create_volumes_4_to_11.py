#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
七之助捕物帳 第4-11巻の一括製作スクリプト
"""
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path("/Volumes/2TB/Marutake AudioBook Library")
TOOLS_DIR = BASE_DIR / "tools"

# 第4-11巻のマッピング
volumes = [
    {"volume": 4, "subtitle": "", "file": "納言恭平　七之助捕物帳　第四巻.txt"},
    {"volume": 5, "subtitle": "", "file": "納言恭平　七之助捕物帳　第五巻.txt"},
    {"volume": 6, "subtitle": "", "file": "納言恭平　七之助捕物帳　第六巻.txt"},
    {"volume": 7, "subtitle": "", "file": "納言恭平　七之助捕物帳　第七巻.txt"},
    {"volume": 8, "subtitle": "", "file": "納言恭平　七之助捕物帳　第八巻.txt"},
    {"volume": 9, "subtitle": "", "file": "納言恭平　七之助捕物帳　第九巻.txt"},
    {"volume": 10, "subtitle": "大黑丸秘譚", "file": "納言恭平　七之助捕物帳　第十巻　大黑丸秘譚.txt"},
    {"volume": 11, "subtitle": "鶯替騷動", "file": "納言恭平　七之助捕物帳　第11巻　鶯替騷動.txt"},
]

print("="*70)
print("七之助捕物帳 第4-11巻 一括製作")
print("="*70)

success = []
failed = []

for vol in volumes:
    volume_num = vol["volume"]
    subtitle = vol["subtitle"]
    filename = vol["file"]
    
    # サブタイトルがない場合は空文字
    if subtitle:
        title_arg = subtitle
    else:
        title_arg = f"第{volume_num}巻"
    
    print(f"\n📚 第{volume_num}巻 製作開始...")
    
    cmd = [
        "python3",
        str(TOOLS_DIR / "batch_create_shichino_series.py"),
        "--volume", str(volume_num),
        "--title", title_arg,
        "--file", filename
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        success.append(volume_num)
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: {e.stderr}")
        failed.append(volume_num)

print("\n" + "="*70)
print("製作サマリー")
print("="*70)
print(f"✅ 成功: {len(success)}巻 - {success}")
if failed:
    print(f"❌ 失敗: {len(failed)}巻 - {failed}")
print("="*70)
