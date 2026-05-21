#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

path = Path("reports/zenigata_heiji_works_catalog.csv")
rows = list(csv.DictReader(path.open(encoding="utf-8")))

no_channel = [r for r in rows if r["has_channel_entry"] == "no"]
no_audio = [r for r in rows if r["has_audio_archive"] == "no"]
no_channel_no_audio = [
    r for r in rows if r["has_channel_entry"] == "no" and r["has_audio_archive"] == "no"
]
local_only = [r for r in no_channel_no_audio if r["has_local_text"] == "yes"]
thin = [
    r
    for r in no_channel_no_audio
    if r["has_local_text"] == "no"
    and r["has_bookdata"] == "no"
    and r["has_meta"] == "no"
]

print("all", len(rows))
print("no_channel", len(no_channel))
print("no_audio", len(no_audio))
print("no_channel_no_audio", len(no_channel_no_audio))
print("local_only", len(local_only))
print("thin", len(thin))
print("titles")
for row in no_channel_no_audio[:40]:
    print(row["title"])
