import google.generativeai as genai
from googleapiclient.discovery import build
import json
import csv
import time
import os
import re

# ==========================================
# 1. 設定エリア
# ==========================================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CHANNEL_ID = "UCeTnkaLU8_MAMSdMFVrf1dw"  # 丸竹書房

OUTPUT_FILE = "marutake_library.csv"

# テスト用に最初は 10本 で止まる設定。
# 全件実行時はここを None に書き換えてください。
LIMIT_COUNT = None

# ★除外設定: これより短い動画は除外します（秒単位）
# ショート動画は最大60秒なので、61秒以上に設定すれば確実に除外できます。
MIN_DURATION_SECONDS = 61

# ==========================================
# 2. ツール関数（時間判定・AI）
# ==========================================
if not YOUTUBE_API_KEY or not GEMINI_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY と GEMINI_API_KEY を環境変数で設定してください。")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


# YouTubeの時間形式 (PT1H2M10S) を 秒数 (integer) に変換する関数
def parse_duration(duration_str):
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def analyze_video_with_ai(title, description):
    prompt = f"""
    あなたは老舗出版社「丸竹書房」の書誌データ管理者です。
    以下の時代小説朗読の情報を元に、Webサイト用の分類データを作成してください。

    【入力データ】
    タイトル: {title}
    概要欄: {description}

    【制約事項】
    1. 「オーディオブック」「朗読」「小説」は除外。
    2. genre（ジャンル）は【許可リストA】から最も適切なものを1〜2つ選択。
       許可リストA: [捕物帳, 人情・市井・下町, 剣豪・武家, 仇討ち・復讐, 怪談・奇談, 歴史・実録, 職人・芸道, 滑稽・落語, 現代小説, その他]
    3. mood（雰囲気）は【許可リストB】から1つ選択。
       許可リストB: [泣ける, 痛快, 怖い, ほっこり, シリアス, 不思議]

    【出力フォーマット】
    以下のJSON形式のみを出力（Markdown不要）。
    {{
        "author": "著者名",
        "title": "作品名（装飾除く）",
        "genre": ["ジャンル1"],
        "mood": "雰囲気",
        "keywords": ["重要語句3-5個"],
        "era": "時代設定",
        "summary": "30文字以内のキャッチコピー"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Error: {e}")
        return None


# ==========================================
# 3. メイン処理
# ==========================================
def main():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # チャンネルのアップロードリストIDを取得
    ch_response = (
        youtube.channels().list(id=CHANNEL_ID, part="contentDetails").execute()
    )
    uploads_playlist_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]

    print(f"リストID取得: {uploads_playlist_id}")

    # CSV準備
    if not os.path.exists(OUTPUT_FILE):
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

    next_page_token = None
    processed_count = 0

    while True:
        # 1. まずリストから50件取得
        pl_request = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=50,
            pageToken=next_page_token,
        )
        pl_response = pl_request.execute()

        items = pl_response["items"]
        if not items:
            break

        # 2. 動画IDを抽出して、詳細情報（再生時間）を一括問い合わせ
        #    (playlistItemsだけでは時間はわからないため)
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items]

        vid_request = youtube.videos().list(
            part="contentDetails", id=",".join(video_ids)
        )
        vid_response = vid_request.execute()

        # IDと再生時間の辞書を作る
        duration_map = {}
        for v in vid_response["items"]:
            # contentDetailsにdurationが含まれていない場合を考慮
            if "contentDetails" in v and "duration" in v["contentDetails"]:
                duration_map[v["id"]] = parse_duration(v["contentDetails"]["duration"])
            else:
                duration_map[v["id"]] = 0

        # 3. ループ処理
        for item in items:
            if LIMIT_COUNT and processed_count >= LIMIT_COUNT:
                print("制限件数に達しました。終了します。")
                return

            vid = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            desc = item["snippet"]["description"]
            pub_date = item["snippet"]["publishedAt"][:10]

            # ★判定: Short動画を除外
            duration = duration_map.get(vid, 0)
            if duration < MIN_DURATION_SECONDS:
                print(f"[SKIP] Short動画を検出 ({duration}秒): {title[:20]}...")
                continue  # 次の動画へスキップ

            print(f"[{processed_count + 1}] Analyzing: {title[:20]}... ({duration}秒)")

            # AI分析
            ai_data = analyze_video_with_ai(title, desc)

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
                            duration,  # 秒数も一応保存
                        ]
                    )

            processed_count += 1
            time.sleep(2)  # 休憩

        next_page_token = pl_response.get("nextPageToken")
        if not next_page_token:
            break

    print("全処理完了しました！")


if __name__ == "__main__":
    main()
