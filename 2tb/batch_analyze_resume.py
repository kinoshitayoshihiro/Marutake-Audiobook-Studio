import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import csv
import time
import os
import re

# ==========================================
# 1. 設定エリア
# ==========================================
YOUTUBE_API_KEY = "REDACTED_GOOGLE_API_KEY"
GEMINI_API_KEY = "REDACTED_GOOGLE_API_KEY"
CHANNEL_ID = "UCeTnkaLU8_MAMSdMFVrf1dw"  # 丸竹書房

OUTPUT_FILE = "marutake_library.csv"

# 1回の実行でAI処理する本数（API制限対策のため、まずは 20〜50 推奨）
# Short動画の記録はカウントに含めないので、サクサク進みます。
LIMIT_COUNT = None

# Short動画判定（秒）
MIN_DURATION_SECONDS = 120

# ==========================================
# 2. ツール関数
# ==========================================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


def parse_duration(duration_str):
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def analyze_video_with_ai_retry(title, description, max_retries=3):
    """API制限(429)対策のリトライ関数"""
    prompt = f"""
    あなたは老舗出版社「丸竹書房」の書誌データ管理者です。
    以下の時代小説朗読の情報を元に、Webサイト用の分類データを作成してください。
    
    タイトル: {title}
    概要欄: {description}
    
    制約事項:
    1. 「オーディオブック」「朗読」「小説」は除外。
    2. genre（ジャンル）は【許可リストA】から最も適切なものを1〜2つ選択。
       許可リストA: [捕物帳, 人情・市井・下町, 剣豪・武家, 仇討ち・復讐, 怪談・奇談, 歴史・実録, 職人・芸道, 滑稽・落語, 現代小説, その他]
    3. mood（雰囲気）は【許可リストB】から1つ選択。
       許可リストB: [泣ける, 痛快, 怖い, ほっこり, シリアス, 不思議]
    
    出力フォーマット: JSON形式のみ
    {{
        "author": "著者名",
        "title": "作品名",
        "genre": ["ジャンル"],
        "mood": "雰囲気",
        "keywords": ["重要語句"],
        "era": "時代設定",
        "summary": "30文字コピー"
    }}
    """

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            # Safety Filterなどでブロックされた場合の対策
            try:
                text = response.text
            except ValueError:
                print(
                    f"⚠️ AI Safety Filter triggered. Retrying... ({attempt+1}/{max_retries})"
                )
                time.sleep(5)
                continue

            # Markdownのコードブロック記法 (```json ... ```) を除去
            text = text.strip()
            if "```" in text:
                text = re.sub(r"```json\s*", "", text)
                text = re.sub(r"```\s*", "", text)

            # 前後の余計な文字を除去（{ で始まり } で終わる部分を抽出）
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)

            return json.loads(text)

        except json.JSONDecodeError:
            print(f"⚠️ JSON Parse Error. Retrying... ({attempt+1}/{max_retries})")
            time.sleep(5)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                # 待機時間を長めに設定 (指数関数的バックオフ)
                wait_time = 60 * (2**attempt)  # 60秒, 120秒, 240秒
                print(
                    f"⚠️ API制限 (429) を検出。{wait_time}秒 休憩します... ({attempt+1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                print(f"❌ AI Error: {e}")
                time.sleep(5)  # その他のエラーも少し待ってリトライ
    return None


# ==========================================
# 3. メイン処理
# ==========================================
def main():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # --- CSV読み込み (処理済みIDリスト作成) ---
    existing_ids = set()
    existing_titles = {}  # Title -> Duration

    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                # DictReaderを使って読み込む
                reader = csv.DictReader(f)
                for row in reader:
                    if "YoutubeID" in row:
                        existing_ids.add(row["YoutubeID"])

                        # タイトルと時間を記録（重複チェック用）
                        title = row.get("Title", "")
                        try:
                            dur = int(float(row.get("DurationSec", 0)))
                        except:
                            dur = 0

                        # 既に同じタイトルがある場合、長い方の時間を保持
                        if title in existing_titles:
                            if dur > existing_titles[title]:
                                existing_titles[title] = dur
                        else:
                            existing_titles[title] = dur

            print(f"📂 既存データ: {len(existing_ids)}件 はスキップします。")
        except Exception as e:
            print(f"CSV読み込みエラー（新規作成します）: {e}")
    else:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "YoutubeID",
                    "Title",
                    "Published",
                    "Author",
                    "CleanTitle",
                    "Genre",
                    "Mood",
                    "Keywords",
                    "Era",
                    "Summary",
                    "DurationSec",
                ]
            )

    # --- YouTube処理開始 ---
    ch_response = (
        youtube.channels().list(id=CHANNEL_ID, part="contentDetails").execute()
    )
    uploads_playlist_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]

    print("--- 処理を開始します ---")

    next_page_token = None
    ai_processed_count = 0

    while True:
        # リスト取得
        try:
            pl_request = youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="snippet",
                maxResults=50,
                pageToken=next_page_token,
            )
            pl_response = pl_request.execute()
        except HttpError as e:
            print(f"YouTube API Error: {e}")
            break

        items = pl_response["items"]
        if not items:
            break

        # 未処理動画のみ抽出
        target_items = []
        for item in items:
            vid = item["snippet"]["resourceId"]["videoId"]
            if vid not in existing_ids:
                target_items.append(item)

        if not target_items:
            next_page_token = pl_response.get("nextPageToken")
            if not next_page_token:
                break
            print("...ページ内すべて処理済み。次へ...")
            continue

        # 時間情報の一括取得
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in target_items]
        vid_request = youtube.videos().list(
            part="contentDetails", id=",".join(video_ids)
        )
        vid_response = vid_request.execute()
        duration_map = {
            v["id"]: parse_duration(v["contentDetails"]["duration"])
            for v in vid_response["items"]
        }

        # 個別処理
        for item in target_items:
            if LIMIT_COUNT and ai_processed_count >= LIMIT_COUNT:
                print("🛑 AI処理数の制限に達しました。終了します。")
                return

            vid = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            desc = item["snippet"]["description"]
            pub_date = item["snippet"]["publishedAt"][:10]

            duration = duration_map.get(vid, 0)

            # ★改善点: Short動画なら「SKIP」としてCSVに記録してしまう
            if duration < MIN_DURATION_SECONDS:
                print(f"[SKIP] Short動画を除外: {title[:15]}...")
                existing_ids.add(vid)
                continue

            # ★改善点: 重複タイトルチェック
            if title in existing_titles:
                prev_duration = existing_titles[title]
                # 新しい動画が既存より明らかに長い場合（+60秒）は更新（追加）を許可
                if duration > prev_duration + 60:
                    print(
                        f"[UPDATE] より長いバージョンを発見 (既存: {prev_duration}s -> 新規: {duration}s): {title[:15]}..."
                    )
                    existing_titles[title] = duration
                else:
                    # 既存の方が長い、または同等の場合はスキップ
                    print(
                        f"[SKIP] 重複タイトル (既存: {prev_duration}s, 新規: {duration}s): {title[:15]}..."
                    )
                    existing_ids.add(vid)
                    continue
            else:
                existing_titles[title] = duration

            # ここからAI処理（ここだけが重い）
            print(f"[{ai_processed_count + 1}] 分析中: {title[:20]}...")

            ai_data = analyze_video_with_ai_retry(title, desc)

            if ai_data:
                with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            vid,
                            title,
                            pub_date,
                            ai_data.get("author", ""),
                            ai_data.get("title", ""),
                            ",".join(ai_data.get("genre", [])),
                            ai_data.get("mood", ""),
                            ",".join(ai_data.get("keywords", [])),
                            ai_data.get("era", ""),
                            ai_data.get("summary", ""),
                            duration,
                        ]
                    )
                existing_ids.add(vid)
                ai_processed_count += 1

                # API休憩（重要）
                time.sleep(5)

        next_page_token = pl_response.get("nextPageToken")
        if not next_page_token:
            break

    print("🎉 処理完了！")


if __name__ == "__main__":
    main()
