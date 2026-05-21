import csv
from collections import Counter
import statistics

INPUT_FILE = "marutake_library.csv"

def analyze_csv():
    total_count = 0
    short_skip_count = 0
    ai_analyzed_count = 0
    
    genres = []
    moods = []
    authors = []
    durations = []
    
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_count += 1
                
                # Check for SHORT_SKIP
                if row.get("Genre") == "SHORT_SKIP":
                    short_skip_count += 1
                    continue
                
                ai_analyzed_count += 1
                
                # Collect data for analysis
                if row.get("Genre"):
                    # Genre might be comma separated
                    g_list = [g.strip() for g in row["Genre"].split(",")]
                    genres.extend(g_list)
                
                if row.get("Mood"):
                    moods.append(row["Mood"])
                
                if row.get("Author"):
                    authors.append(row["Author"])
                
                if row.get("DurationSec"):
                    try:
                        durations.append(int(row["DurationSec"]))
                    except ValueError:
                        pass

        print(f"--- 分析結果 ---")
        print(f"総動画数: {total_count} 件")
        print(f"Short動画 (SKIP): {short_skip_count} 件")
        print(f"AI分析済み動画: {ai_analyzed_count} 件")
        print("-" * 20)
        
        if durations:
            avg_duration = statistics.mean(durations)
            print(f"平均再生時間 (Short除く): {int(avg_duration // 60)}分 {int(avg_duration % 60)}秒")
            print(f"最長再生時間: {int(max(durations) // 60)}分 {int(max(durations) % 60)}秒")
            print(f"最短再生時間: {int(min(durations) // 60)}分 {int(min(durations) % 60)}秒")
        
        print("-" * 20)
        print("【人気ジャンル Top 5】")
        for g, count in Counter(genres).most_common(5):
            print(f"  - {g}: {count}")
            
        print("-" * 20)
        print("【多い雰囲気 Top 5】")
        for m, count in Counter(moods).most_common(5):
            print(f"  - {m}: {count}")

        print("-" * 20)
        print("【著者 Top 5】")
        for a, count in Counter(authors).most_common(5):
            print(f"  - {a}: {count}")

    except FileNotFoundError:
        print(f"エラー: {INPUT_FILE} が見つかりません。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    analyze_csv()
