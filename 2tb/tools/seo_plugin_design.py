"""
WordPress SEO最適化プラグイン設計
=====================================
読書アプリ用のbookdataからSchema.org構造化データとOGPメタタグを生成

機能:
1. Schema.org Book/CreativeWork 構造化データ出力
2. Open Graph Protocol (OGP) メタタグ生成
3. Twitter Card メタタグ生成
4. JSON-LD形式で検索エンジンに最適化
"""

# =====================================
# 1. Schema.org Book構造化データ生成
# =====================================


def generate_schema_org_book(bookdata: dict, post_url: str) -> dict:
    """
    bookdataからSchema.org Book/CreativeWork JSONを生成

    参考: https://schema.org/Book
          https://schema.org/CreativeWork
    """

    # 基本Book構造
    schema = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": bookdata.get("title", ""),
        "author": {
            "@type": "Person",
            "name": bookdata.get("author", ""),
            "description": bookdata.get("author_info", {}).get("biography", ""),
        },
        "inLanguage": "ja",
        "url": post_url,
        # Schema.org標準プロパティ
        "genre": bookdata.get("genre", ""),  # "Mystery", "Drama" など
        "keywords": bookdata.get("keywords", []),
        "abstract": bookdata.get("synopsis", ""),
        "description": bookdata.get("synopsis", ""),
        # 時代設定
        "datePublished": bookdata.get("year", ""),
        "temporalCoverage": bookdata.get("era", ""),
        # 登場人物（Schema.org character）
        "character": [
            {
                "@type": "Person",
                "name": char.get("name", ""),
                "description": char.get("description", ""),
            }
            for char in bookdata.get("characters", [])
        ],
    }

    # 日本文学特化メタデータ（additionalProperty）
    if bookdata.get("japanese_genre"):
        schema["additionalProperty"] = []

        # 日本語ジャンル
        schema["additionalProperty"].append(
            {
                "@type": "PropertyValue",
                "name": "japanese_genre",
                "value": bookdata["japanese_genre"],
            }
        )

        # テーマタグ
        if bookdata.get("themes"):
            schema["additionalProperty"].append(
                {
                    "@type": "PropertyValue",
                    "name": "themes",
                    "value": bookdata["themes"],
                }
            )

        # 感情タグ
        if bookdata.get("emotions"):
            schema["additionalProperty"].append(
                {
                    "@type": "PropertyValue",
                    "name": "emotions",
                    "value": bookdata["emotions"],
                }
            )

    return schema


# =====================================
# 2. OGP (Open Graph Protocol) 生成
# =====================================


def generate_ogp_meta_tags(bookdata: dict, post_url: str, image_url: str = "") -> list:
    """
    OGPメタタグのHTMLを生成

    参考: https://ogp.me/
    """

    tags = []

    # 基本OGPタグ
    tags.append(f'<meta property="og:type" content="book" />')
    tags.append(f'<meta property="og:title" content="{bookdata.get("title", "")}" />')
    tags.append(f'<meta property="og:url" content="{post_url}" />')
    tags.append(
        f'<meta property="og:description" content="{bookdata.get("synopsis", "")[:200]}" />'
    )

    # 画像（カバーアートなど）
    if image_url:
        tags.append(f'<meta property="og:image" content="{image_url}" />')

    # 書籍固有のOGPタグ
    tags.append(
        f'<meta property="book:author" content="{bookdata.get("author", "")}" />'
    )

    if bookdata.get("year"):
        tags.append(
            f'<meta property="book:release_date" content="{bookdata["year"]}" />'
        )

    # タグ（キーワード）
    for keyword in bookdata.get("keywords", []):
        tags.append(f'<meta property="book:tag" content="{keyword}" />')

    return tags


# =====================================
# 3. Twitter Card生成
# =====================================


def generate_twitter_card_tags(bookdata: dict, image_url: str = "") -> list:
    """
    Twitter Cardメタタグを生成

    参考: https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/markup
    """

    tags = []

    # カードタイプ
    tags.append('<meta name="twitter:card" content="summary_large_image" />')
    tags.append(f'<meta name="twitter:title" content="{bookdata.get("title", "")}" />')
    tags.append(
        f'<meta name="twitter:description" content="{bookdata.get("synopsis", "")[:200]}" />'
    )

    if image_url:
        tags.append(f'<meta name="twitter:image" content="{image_url}" />')

    return tags


# =====================================
# 4. WordPress統合コード（PHP想定）
# =====================================

WORDPRESS_INTEGRATION_CODE = """
<?php
/**
 * Plugin Name: Reading App SEO Optimizer
 * Description: 読書アプリ用のSchema.org構造化データとOGPメタタグを自動生成
 * Version: 1.0.0
 * Author: Marutake AudioBook Library
 */

// Schema.org JSON-LD出力
function rao_output_schema_org_jsonld() {
    if (!is_single()) return;
    
    global $post;
    
    // immersive_readerショートコードからbookdataを抽出
    preg_match('/\\[immersive_reader\\](.+?)\\[\\/immersive_reader\\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata) return;
    
    // Schema.org構造化データ生成
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Book',
        'name' => $bookdata['title'] ?? '',
        'author' => array(
            '@type' => 'Person',
            'name' => $bookdata['author'] ?? ''
        ),
        'inLanguage' => 'ja',
        'url' => get_permalink(),
        'genre' => $bookdata['genre'] ?? '',
        'keywords' => implode(', ', $bookdata['keywords'] ?? []),
        'abstract' => $bookdata['synopsis'] ?? '',
        'description' => $bookdata['synopsis'] ?? ''
    );
    
    // 日本語ジャンル・テーマ・感情タグを追加
    if (!empty($bookdata['japanese_genre']) || 
        !empty($bookdata['themes']) || 
        !empty($bookdata['emotions'])) {
        
        $schema['additionalProperty'] = array();
        
        if (!empty($bookdata['japanese_genre'])) {
            $schema['additionalProperty'][] = array(
                '@type' => 'PropertyValue',
                'name' => 'japanese_genre',
                'value' => $bookdata['japanese_genre']
            );
        }
        
        if (!empty($bookdata['themes'])) {
            $schema['additionalProperty'][] = array(
                '@type' => 'PropertyValue',
                'name' => 'themes',
                'value' => $bookdata['themes']
            );
        }
        
        if (!empty($bookdata['emotions'])) {
            $schema['additionalProperty'][] = array(
                '@type' => 'PropertyValue',
                'name' => 'emotions',
                'value' => $bookdata['emotions']
            );
        }
    }
    
    // JSON-LD出力
    echo '<script type="application/ld+json">';
    echo json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    echo '</script>';
}
add_action('wp_head', 'rao_output_schema_org_jsonld');

// OGPメタタグ出力
function rao_output_ogp_tags() {
    if (!is_single()) return;
    
    global $post;
    
    preg_match('/\\[immersive_reader\\](.+?)\\[\\/immersive_reader\\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata) return;
    
    $title = esc_attr($bookdata['title'] ?? '');
    $author = esc_attr($bookdata['author'] ?? '');
    $synopsis = esc_attr(mb_substr($bookdata['synopsis'] ?? '', 0, 200));
    $url = esc_url(get_permalink());
    
    echo '<meta property="og:type" content="book" />' . "\\n";
    echo '<meta property="og:title" content="' . $title . '" />' . "\\n";
    echo '<meta property="og:url" content="' . $url . '" />' . "\\n";
    echo '<meta property="og:description" content="' . $synopsis . '" />' . "\\n";
    echo '<meta property="book:author" content="' . $author . '" />' . "\\n";
    
    // キーワードタグ
    if (!empty($bookdata['keywords'])) {
        foreach ($bookdata['keywords'] as $keyword) {
            echo '<meta property="book:tag" content="' . esc_attr($keyword) . '" />' . "\\n";
        }
    }
    
    // Twitter Card
    echo '<meta name="twitter:card" content="summary_large_image" />' . "\\n";
    echo '<meta name="twitter:title" content="' . $title . '" />' . "\\n";
    echo '<meta name="twitter:description" content="' . $synopsis . '" />' . "\\n";
}
add_action('wp_head', 'rao_output_ogp_tags');

// 検索結果スニペット最適化
function rao_optimize_meta_description() {
    if (!is_single()) return;
    
    global $post;
    
    preg_match('/\\[immersive_reader\\](.+?)\\[\\/immersive_reader\\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || empty($bookdata['synopsis'])) return;
    
    $description = esc_attr(mb_substr($bookdata['synopsis'], 0, 160));
    echo '<meta name="description" content="' . $description . '" />' . "\\n";
}
add_action('wp_head', 'rao_optimize_meta_description');
?>
"""


# =====================================
# 5. 使用例・テスト
# =====================================

if __name__ == "__main__":
    # サンプルbookdata
    sample_bookdata = {
        "title": "艶妻傳",
        "author": "野村胡堂",
        "genre": "Mystery",
        "keywords": ["捕物帳", "推理", "江戸", "人情", "錢形平次"],
        "japanese_genre": "捕物帳",
        "themes": ["justice", "deduction", "edo_culture"],
        "emotions": ["tension", "warmth", "surprise"],
        "synopsis": "鎌倉町の油問屋・越前屋の若い内儀お加奈...",
        "characters": [{"name": "錢形平次", "description": "明神下に住む岡っ引き"}],
    }

    # Schema.org JSON-LD生成
    import json

    schema = generate_schema_org_book(
        sample_bookdata, "https://example.com/book/tsuyazuma-den"
    )
    print("=== Schema.org JSON-LD ===")
    print(json.dumps(schema, ensure_ascii=False, indent=2))

    # OGPタグ生成
    print("\n=== OGP Meta Tags ===")
    ogp_tags = generate_ogp_meta_tags(
        sample_bookdata, "https://example.com/book/tsuyazuma-den"
    )
    for tag in ogp_tags:
        print(tag)

    # Twitter Cardタグ生成
    print("\n=== Twitter Card Tags ===")
    twitter_tags = generate_twitter_card_tags(sample_bookdata)
    for tag in twitter_tags:
        print(tag)
