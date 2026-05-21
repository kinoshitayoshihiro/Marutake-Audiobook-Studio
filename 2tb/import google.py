import google.generativeai as genai
from googleapiclient.discovery import build
import json

# ==========================================
# 1. 設定エリア (ここに取得したキーを貼ってください)
# ==========================================
YOUTUBE_API_KEY = "REDACTED_GOOGLE_API_KEY"
GEMINI_API_KEY = "REDACTED_GOOGLE_API_KEY"

# テストしたい動画のID (URLの v= の後ろの部分)
# 例: 丸竹書房様の動画IDを一つ指定してください
TARGET_VIDEO_ID = "yHswFCjHBo8"


# ==========================================
# 2. YouTubeからデータを取得する関数
# ==========================================
def get_youtube_info(video_id):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    request = youtube.videos().list(part="snippet", id=video_id)
    response = request.execute()

    if not response["items"]:
        return None

    snippet = response["items"][0]["snippet"]
    return {
        "title": snippet["title"],
        "description": snippet["description"],
        "published_at": snippet["publishedAt"],  # ここから年を取得できます
        "channel_title": snippet["channelTitle"],
    }


# ==========================================
# 3. Gemini (AI) に分析させる関数
# ==========================================
def analyze_with_ai(video_data):
    genai.configure(api_key=GEMINI_API_KEY)

    # 処理が速くて安いモデルを使用
    model = genai.GenerativeModel("gemini-2.0-flash")

    # AIへの命令書（プロンプト）
    prompt = f"""
    あなたは老舗出版社「丸竹書房」のベテラン編集者です。
    以下のYouTube朗読動画の情報を元に、Webサイト用の分類タグを作成してください。

    【入力データ】
    タイトル: {video_data['title']}
    概要欄: {video_data['description']}

    【制約事項】
    1. 「オーディオブック」「朗読」「小説」という単語はタグに含めないでください。
    2. genre は、以下の【許可リスト】の中から、当てはまるものを1つ〜2つ選んでください。
       許可リスト: [捕物帳, 人情・市井, 剣豪・武家, 怪談・奇談, 歴史・実録, 滑稽・落語, 現代小説, その他]
    3. mood（雰囲気）は、以下の中から1つ選んでください。
       許可リスト: [泣ける, 痛快, 怖い, ほっこり, シリアス]

    【出力フォーマット】
    以下のJSON形式のみを出力してください。
    {{
        "author": "著者名（敬称略）",
        "title_clean": "作品名（シリーズ名や【】を除く）",
        "genre": ["許可リストから選択"],
        "mood": "許可リストから選択",
        "keywords": ["具体的な重要語句を3〜5個 (例: 遺産相続, 兄弟, 復讐)"],
        "era": "時代設定 (江戸, 明治, 大正, 昭和, 現代)",
        "summary": "30文字以内の魅力的なキャッチコピー"
    }}
    """

    response = model.generate_content(prompt)
    return response.text


# ==========================================
# 4. メイン実行処理
# ==========================================
if __name__ == "__main__":
    print(f"--- 動画ID: {TARGET_VIDEO_ID} の分析を開始します ---")

    # step 1: YouTubeデータ取得
    video_info = get_youtube_info(TARGET_VIDEO_ID)

    if video_info:
        print(f"取得成功: {video_info['title']}")
        print("AI分析中... (数秒お待ちください)")

        # step 2: AI分析
        ai_result = analyze_with_ai(video_info)

        # step 3: 結果表示
        print("\n--- AI分析結果 (JSON) ---")
        # JSONとして整形して表示
        try:
            # AIが ```json などをつける場合があるので除去する簡易処理
            clean_json = ai_result.replace("```json", "").replace("```", "").strip()
            parsed_data = json.loads(clean_json)
            print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
        except:
            print("生データ表示:")
            print(ai_result)

    else:
        print("動画が見つかりませんでした。IDを確認してください。")
