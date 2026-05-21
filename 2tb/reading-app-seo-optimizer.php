<?php
/**
 * Plugin Name: Reading App SEO Optimizer
 * Plugin URI: https://marutake-audiobook.com
 * Description: 読書アプリ用のSchema.org構造化データとOGPメタタグを自動生成してSEO最適化
 * Version: 1.0.0
 * Author: Marutake AudioBook Library
 * License: GPL v2 or later
 */

if (!defined('ABSPATH')) {
    exit; // 直接アクセスを防止
}

/**
 * Schema.org JSON-LD構造化データを出力
 * 
 * bookdataから自動的にSchema.org Book形式のJSON-LDを生成し、
 * Google等の検索エンジンに構造化データを提供
 */
function rao_output_schema_org_jsonld() {
    if (!is_single()) return;
    if (!in_category('reading_application')) return;
    
    global $post;
    
    // immersive_readerショートコードからbookdataを抽出
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return;
    
    // Schema.org Book構造化データ
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Book',
        'name' => $bookdata['title'] ?? '',
        'author' => array(
            '@type' => 'Person',
            'name' => $bookdata['author'] ?? '',
            'description' => $bookdata['author_info']['biography'] ?? ''
        ),
        'inLanguage' => 'ja-JP',
        'url' => get_permalink(),
        'genre' => $bookdata['genre'] ?? $bookdata['japanese_genre'] ?? '',
        'abstract' => $bookdata['synopsis'] ?? '',
        'description' => $bookdata['synopsis'] ?? ''
    );
    
    // キーワード
    if (!empty($bookdata['keywords'])) {
        $schema['keywords'] = is_array($bookdata['keywords']) 
            ? implode(', ', $bookdata['keywords'])
            : $bookdata['keywords'];
    }
    
    // 発表年
    if (!empty($bookdata['year'])) {
        $schema['datePublished'] = $bookdata['year'];
    }
    
    // 時代設定
    if (!empty($bookdata['era'])) {
        $schema['temporalCoverage'] = $bookdata['era'];
    }
    
    // 登場人物
    if (!empty($bookdata['characters'])) {
        $schema['character'] = array();
        foreach ($bookdata['characters'] as $char) {
            $schema['character'][] = array(
                '@type' => 'Person',
                'name' => $char['name'] ?? '',
                'description' => $char['desc'] ?? $char['description'] ?? ''
            );
        }
    }
    
    // 日本文学特化メタデータ（拡張プロパティ）
    $additional_properties = array();
    
    if (!empty($bookdata['japanese_genre'])) {
        $additional_properties[] = array(
            '@type' => 'PropertyValue',
            'name' => 'japanese_genre',
            'value' => $bookdata['japanese_genre']
        );
    }
    
    if (!empty($bookdata['sub_genre'])) {
        $additional_properties[] = array(
            '@type' => 'PropertyValue',
            'name' => 'sub_genre',
            'value' => $bookdata['sub_genre']
        );
    }
    
    if (!empty($bookdata['themes'])) {
        $additional_properties[] = array(
            '@type' => 'PropertyValue',
            'name' => 'themes',
            'value' => $bookdata['themes']
        );
    }
    
    if (!empty($bookdata['emotions'])) {
        $additional_properties[] = array(
            '@type' => 'PropertyValue',
            'name' => 'emotions',
            'value' => $bookdata['emotions']
        );
    }
    
    if (!empty($additional_properties)) {
        $schema['additionalProperty'] = $additional_properties;
    }
    
    // JSON-LD出力
    echo '<script type="application/ld+json">' . "\n";
    echo json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    echo "\n" . '</script>' . "\n";
}
add_action('wp_head', 'rao_output_schema_org_jsonld');

/**
 * OGP (Open Graph Protocol) メタタグ出力
 * 
 * SNSシェア時の表示を最適化
 */
function rao_output_ogp_tags() {
    if (!is_single()) return;
    if (!in_category('reading_application')) return;
    
    global $post;
    
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return;
    
    $title = esc_attr($bookdata['title'] ?? '');
    $author = esc_attr($bookdata['author'] ?? '');
    $synopsis = esc_attr(mb_substr($bookdata['synopsis'] ?? '', 0, 200));
    $url = esc_url(get_permalink());
    $site_name = esc_attr(get_bloginfo('name'));
    
    // 基本OGPタグ
    echo '<meta property="og:type" content="book" />' . "\n";
    echo '<meta property="og:title" content="' . $title . '" />' . "\n";
    echo '<meta property="og:url" content="' . $url . '" />' . "\n";
    echo '<meta property="og:description" content="' . $synopsis . '" />' . "\n";
    echo '<meta property="og:site_name" content="' . $site_name . '" />' . "\n";
    echo '<meta property="og:locale" content="ja_JP" />' . "\n";
    
    // アイキャッチ画像
    if (has_post_thumbnail()) {
        $thumbnail_url = esc_url(get_the_post_thumbnail_url(null, 'large'));
        echo '<meta property="og:image" content="' . $thumbnail_url . '" />' . "\n";
        echo '<meta property="og:image:width" content="1200" />' . "\n";
        echo '<meta property="og:image:height" content="630" />' . "\n";
    }
    
    // 書籍固有のOGPタグ
    echo '<meta property="book:author" content="' . $author . '" />' . "\n";
    
    if (!empty($bookdata['year'])) {
        echo '<meta property="book:release_date" content="' . esc_attr($bookdata['year']) . '" />' . "\n";
    }
    
    // タグ（キーワード）
    if (!empty($bookdata['keywords'])) {
        $keywords = is_array($bookdata['keywords']) ? $bookdata['keywords'] : [$bookdata['keywords']];
        foreach ($keywords as $keyword) {
            echo '<meta property="book:tag" content="' . esc_attr($keyword) . '" />' . "\n";
        }
    }
    
    // ジャンルタグ
    if (!empty($bookdata['japanese_genre'])) {
        echo '<meta property="book:tag" content="' . esc_attr($bookdata['japanese_genre']) . '" />' . "\n";
    }
}
add_action('wp_head', 'rao_output_ogp_tags');

/**
 * Twitter Card メタタグ出力
 */
function rao_output_twitter_card_tags() {
    if (!is_single()) return;
    if (!in_category('reading_application')) return;
    
    global $post;
    
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return;
    
    $title = esc_attr($bookdata['title'] ?? '');
    $synopsis = esc_attr(mb_substr($bookdata['synopsis'] ?? '', 0, 200));
    
    echo '<meta name="twitter:card" content="summary_large_image" />' . "\n";
    echo '<meta name="twitter:title" content="' . $title . '" />' . "\n";
    echo '<meta name="twitter:description" content="' . $synopsis . '" />' . "\n";
    
    if (has_post_thumbnail()) {
        $thumbnail_url = esc_url(get_the_post_thumbnail_url(null, 'large'));
        echo '<meta name="twitter:image" content="' . $thumbnail_url . '" />' . "\n";
    }
}
add_action('wp_head', 'rao_output_twitter_card_tags');

/**
 * メタディスクリプション最適化
 * 
 * 検索結果のスニペット表示を改善
 */
function rao_optimize_meta_description() {
    if (!is_single()) return;
    if (!in_category('reading_application')) return;
    
    global $post;
    
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return;
    if (empty($bookdata['synopsis'])) return;
    
    // Google推奨は155-160文字
    $description = esc_attr(mb_substr($bookdata['synopsis'], 0, 160));
    echo '<meta name="description" content="' . $description . '" />' . "\n";
    
    // キーワードメタタグ（SEO効果は低いが念のため）
    if (!empty($bookdata['keywords'])) {
        $keywords = is_array($bookdata['keywords']) 
            ? implode(', ', $bookdata['keywords'])
            : $bookdata['keywords'];
        echo '<meta name="keywords" content="' . esc_attr($keywords) . '" />' . "\n";
    }
}
add_action('wp_head', 'rao_optimize_meta_description');

/**
 * タイトルタグ最適化
 */
function rao_optimize_title_tag($title, $sep) {
    if (!is_single()) return $title;
    if (!in_category('reading_application')) return $title;
    
    global $post;
    
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return $title;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return $title;
    
    $book_title = $bookdata['title'] ?? '';
    $author = $bookdata['author'] ?? '';
    $japanese_genre = $bookdata['japanese_genre'] ?? '';
    
    if ($book_title && $author) {
        // 「作品名 - 著者名 - ジャンル」形式
        if ($japanese_genre) {
            return $book_title . ' ' . $sep . ' ' . $author . ' ' . $sep . ' ' . $japanese_genre;
        } else {
            return $book_title . ' ' . $sep . ' ' . $author;
        }
    }
    
    return $title;
}
add_filter('wp_title', 'rao_optimize_title_tag', 10, 2);

/**
 * パンくずリスト Schema.org BreadcrumbList
 */
function rao_output_breadcrumb_schema() {
    if (!is_single()) return;
    if (!in_category('reading_application')) return;
    
    global $post;
    
    preg_match('/\[immersive_reader\](.+?)\[\/immersive_reader\]/s', 
               $post->post_content, $matches);
    
    if (!isset($matches[1])) return;
    
    $bookdata = json_decode($matches[1], true);
    if (!$bookdata || json_last_error() !== JSON_ERROR_NONE) return;
    
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'BreadcrumbList',
        'itemListElement' => array(
            array(
                '@type' => 'ListItem',
                'position' => 1,
                'name' => 'ホーム',
                'item' => home_url()
            ),
            array(
                '@type' => 'ListItem',
                'position' => 2,
                'name' => '読書アプリ',
                'item' => get_category_link(get_cat_ID('reading_application'))
            ),
            array(
                '@type' => 'ListItem',
                'position' => 3,
                'name' => $bookdata['title'] ?? '',
                'item' => get_permalink()
            )
        )
    );
    
    echo '<script type="application/ld+json">' . "\n";
    echo json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    echo "\n" . '</script>' . "\n";
}
add_action('wp_head', 'rao_output_breadcrumb_schema');
