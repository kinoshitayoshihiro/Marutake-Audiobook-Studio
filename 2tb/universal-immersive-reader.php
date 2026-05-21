<?php
/*
Plugin Name: Universal Immersive Reader
Description: ショートコード [immersive_reader] を使用。検索機能、あらすじ・解説・作者紹介・用語集のタブ切り替え機能を提供します。管理画面からJSONファイルをアップロードして投稿を自動作成・更新できます。SEO対策完備。
Version: 7.1
Author: Gemini & Marutake AudioBook Library
License: GPL2
*/

if ( ! defined( 'ABSPATH' ) ) exit;

// 1. スクリプトの読み込み
function uir_enqueue_scripts() {
    global $post;
    if ( is_a( $post, 'WP_Post' ) && ( has_shortcode( $post->post_content, 'immersive_reader' ) || has_shortcode( $post->post_content, 'reader_library' ) ) ) {
        wp_enqueue_script( 'react', 'https://unpkg.com/react@18/umd/react.production.min.js', array(), '18.0', true );
        wp_enqueue_script( 'react-dom', 'https://unpkg.com/react-dom@18/umd/react-dom.production.min.js', array('react'), '18.0', true );
        wp_enqueue_script( 'babel', 'https://unpkg.com/@babel/standalone/babel.min.js', array(), '7.0', true );
        wp_enqueue_script( 'tailwindcss', 'https://cdn.tailwindcss.com', array(), '3.4', false );
        wp_enqueue_style( 'google-fonts-noto', 'https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;500;700&display=swap', array(), null );
    }
}
add_action( 'wp_enqueue_scripts', 'uir_enqueue_scripts' );

// 2. サイト内の全ストーリー構造を取得
function uir_get_site_structure() {
    $library = array();
    $args_posts = array(
        'post_type' => 'post',
        'post_status' => 'publish',
        'posts_per_page' => -1,
        'category_name' => 'reading_application',
        'orderby' => 'date',
        'order' => 'DESC'
    );
    $query_posts = new WP_Query($args_posts);
    if ($query_posts->have_posts()) {
        while ($query_posts->have_posts()) {
            $query_posts->the_post();
            $cats = get_the_category();
            $series = !empty($cats) ? $cats[0]->name : '未分類';
            $tags = get_the_tags();
            $author = !empty($tags) ? $tags[0]->name : '編集部';
            $library[] = array(
                'id' => get_the_ID(),
                'title' => get_the_title(),
                'url' => get_permalink(),
                'series' => $series,
                'author' => $author,
                'genre' => $series,
                'date' => get_the_date('Y.m.d'),
                'thumbnail' => get_the_post_thumbnail_url(get_the_ID(), 'medium')
            );
        }
        wp_reset_postdata();
    }
    return $library;
}

// wpautop対策
function uir_preserve_shortcode_content( $content ) {
    if ( strpos( $content, '[immersive_reader]' ) !== false ) {
        $content = preg_replace_callback(
            '/\[immersive_reader\](.*?)\[\/immersive_reader\]/s',
            function( $matches ) {
                $json = $matches[1];
                $json = preg_replace( '/<p[^>]*>/', '', $json );
                $json = preg_replace( '/<\/p>/', '', $json );
                $json = preg_replace( '/<br\s*\/?>/', '', $json );
                return '[immersive_reader]' . $json . '[/immersive_reader]';
            },
            $content
        );
    }
    return $content;
}
add_filter( 'the_content', 'uir_preserve_shortcode_content', 9 );

// 3. ショートコードハンドラ
function uir_shortcode_handler( $atts, $content = null ) {
    $atts = shortcode_atts( array( 'file' => '' ), $atts, 'immersive_reader' );
    $json_content = '';
    
    if ( !empty( $atts['file'] ) ) {
        $file_url = esc_url( $atts['file'] );
        $upload_dir = wp_upload_dir();
        $file_path = str_replace( $upload_dir['baseurl'], $upload_dir['basedir'], $file_url );
        
        if ( file_exists( $file_path ) ) {
            $json_content = file_get_contents( $file_path );
        } else {
            $response = wp_remote_get( $file_url );
            if ( !is_wp_error( $response ) ) $json_content = wp_remote_retrieve_body( $response );
        }
    } elseif ( !empty( $content ) ) {
        $json_content = $content;
        $json_content = preg_replace( '/<p[^>]*>/', '', $json_content );
        $json_content = preg_replace( '/<\/p>/', '', $json_content );
        $json_content = preg_replace( '/<br\s*\/?>/', '', $json_content );
        $json_content = strip_tags( $json_content );
        $json_content = html_entity_decode($json_content, ENT_QUOTES, 'UTF-8');
        $json_content = str_replace(array('&#8220;', '&#8221;', "\xe2\x80\x9c", "\xe2\x80\x9d", '「', '」'), '"', $json_content);
        $json_content = str_replace(array('&nbsp;', "\xC2\xA0"), ' ', $json_content);
    }

    $json_content = trim( $json_content );
    $decoded_data = json_decode($json_content, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        $safe_json_data = '{}';
    } else {
        $safe_json_data = json_encode($decoded_data, JSON_UNESCAPED_UNICODE);
    }
    
    $library = uir_get_site_structure();
    $library_json = json_encode($library, JSON_UNESCAPED_UNICODE);
    $uid = 'reader-' . uniqid();

    $upload_dir = wp_upload_dir();
    $utabon_manifest_url = '';
    $utabon_asset_base_url = '';
    if ( function_exists( 'utabon_get_archive_manifest_url' ) ) {
        $utabon_manifest_url = (string) utabon_get_archive_manifest_url();
    }
    if ( ! $utabon_manifest_url && is_array( $upload_dir ) && empty( $upload_dir['error'] ) ) {
        $utabon_manifest_url = trailingslashit( $upload_dir['baseurl'] ) . 'themesong-library/archive_manifest.json';
    }
    if ( is_array( $upload_dir ) && empty( $upload_dir['error'] ) ) {
        $utabon_asset_base_url = trailingslashit( $upload_dir['baseurl'] ) . 'themesong-library/audio/';
    }
    $asset_base_opt = function_exists( 'get_option' ) ? get_option( 'themesong_asset_base_url', '' ) : '';
    if ( is_string( $asset_base_opt ) && $asset_base_opt ) {
        $utabon_asset_base_url = trailingslashit( $asset_base_opt );
    }
    $utabon_config = array(
        'label'        => 'Utabon（唄本）',
        'manifestUrl'  => $utabon_manifest_url,
        'assetBaseUrl' => $utabon_asset_base_url,
    );
    $utabon_config_json = function_exists( 'wp_json_encode' )
        ? wp_json_encode( $utabon_config, JSON_UNESCAPED_UNICODE )
        : json_encode( $utabon_config, JSON_UNESCAPED_UNICODE );

    ob_start();
    ?>
    
    <div id="<?php echo esc_attr($uid); ?>" class="immersive-reader-app" style="width:100%; min-height:600px; background:#f7f4e9; border:1px solid #ddd; display:flex; align-items:center; justify-content:center;">
        読み込み中...
    </div>

    <script>
        window.immersiveCurrentData = <?php echo $safe_json_data; ?>;
        window.immersiveLibrary = <?php echo $library_json ?: '[]'; ?>;
        window.immersiveCurrentPostId = <?php echo get_the_ID(); ?>;
        window.utabonConfig = <?php echo $utabon_config_json ?: '{}'; ?>;
    </script>

    <style>
        .immersive-reader-app { font-family: 'Noto Serif JP', serif; }
        .immersive-reader-app ::-webkit-scrollbar { width: 8px; height: 8px; }
        .immersive-reader-app ::-webkit-scrollbar-track { background: #f1f1f1; }
        .immersive-reader-app ::-webkit-scrollbar-thumb { background: #d6d3d1; border-radius: 4px; }
        .writing-vertical-rl { writing-mode: vertical-rl; -ms-writing-mode: tb-rl; }
        .writing-horizontal-tb { writing-mode: horizontal-tb; -ms-writing-mode: lr-tb; }
        /* Hide scrollbar for immersive experience */
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        /* Trivia Widget Styles */
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in-up { animation: fadeInUp 0.3s ease-out forwards; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 3px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: rgba(0, 0, 0, 0.2); }
    </style>

    <script type="text/babel">
    (function() {
        const { useState, useEffect, useMemo } = React;
        
        // --- Icons ---
            const Icons = {
            Search: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
            List: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>,
            ChevronDown: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>,
            Map: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>,
            FileText: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>,
            Type: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>,
            Music: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>,
            Headphones: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>,
            Volume2: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>,
            Pause: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>,
            Play: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
            ExternalLink: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>,
            Home: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
            ChevronLeft: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>,
            ChevronRight: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>,
            X: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
            BookOpen: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
            Info: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>,
            Feather: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/></svg>,
            User: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
            Book: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>,
            Minus: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>,
            Plus: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
            Layout: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
        };        // --- Search Component ---
        const LibraryNavigator = ({ library, currentId }) => {
            const [isOpen, setIsOpen] = useState(false);
            const [filterType, setFilterType] = useState('series');
            const [selectedFilter, setSelectedFilter] = useState('all');
            const [searchTerm, setSearchTerm] = useState('');

            const seriesList = useMemo(() => [...new Set(library.map(item => item.series))].sort(), [library]);
            const authorList = useMemo(() => [...new Set(library.map(item => item.author))].sort(), [library]);

            const filteredStories = useMemo(() => {
                const byFacet = (selectedFilter === 'all')
                    ? library
                    : library.filter(item =>
                        filterType === 'series' ? item.series === selectedFilter : item.author === selectedFilter
                    );

                if (!searchTerm.trim()) return byFacet;
                const term = searchTerm.toLowerCase();
                return byFacet.filter(item =>
                    item.title?.toLowerCase().includes(term) ||
                    item.author?.toLowerCase().includes(term) ||
                    item.series?.toLowerCase().includes(term) ||
                    item.genre?.toLowerCase().includes(term)
                );
            }, [library, filterType, selectedFilter, searchTerm]);

            return (
                <div className="relative z-50">
                    <button onClick={() => setIsOpen(!isOpen)} className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-stone-50 rounded-lg text-sm text-stone-800 font-bold transition-all border border-stone-200 shadow-sm whitespace-nowrap">
                        <Icons.Search width="16" className="text-indigo-600" />
                        <span className="hidden sm:inline">探す</span>
                        <Icons.ChevronDown width="14" className="text-stone-400" />
                    </button>
                    {isOpen && (
                        <>
                            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
                            <div className="absolute top-full left-0 mt-2 w-72 sm:w-96 bg-white rounded-xl shadow-2xl border border-stone-200 overflow-hidden z-50">
                                <div className="flex border-b border-stone-100 bg-stone-50">
                                    <button onClick={() => { setFilterType('series'); setSelectedFilter('all'); }} className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 ${filterType === 'series' ? 'bg-white text-indigo-700 border-t-2 border-indigo-600' : 'text-stone-500 hover:bg-stone-100'}`}><Icons.List width="16" /> シリーズ</button>
                                    <button onClick={() => { setFilterType('author'); setSelectedFilter('all'); }} className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 ${filterType === 'author' ? 'bg-white text-indigo-700 border-t-2 border-indigo-600' : 'text-stone-500 hover:bg-stone-100'}`}><Icons.User width="16" /> 作者</button>
                                </div>
                                <div className="p-3 bg-white border-b border-stone-100">
                                    <input
                                        type="text"
                                        placeholder="タイトル・作者・シリーズで検索..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="w-full p-2 border border-stone-200 rounded bg-white text-stone-700 text-sm focus:outline-none"
                                    />
                                </div>
                                <div className="p-3 bg-white border-b border-stone-100">
                                    <select className="w-full p-2 border border-stone-200 rounded bg-stone-50 text-stone-700 text-sm focus:outline-none" value={selectedFilter} onChange={(e) => setSelectedFilter(e.target.value)}>
                                        <option value="all">すべて表示</option>
                                        {(filterType === 'series' ? seriesList : authorList).map(item => (<option key={item} value={item}>{item}</option>))}
                                    </select>
                                </div>
                                <div className="max-h-80 overflow-y-auto bg-white">
                                    {filteredStories.length === 0 ? (
                                        <div className="p-4 text-center text-stone-400 text-sm">見つかりませんでした</div>
                                    ) : filteredStories.map((story) => (
                                        <a key={story.id} href={story.url} className={`block px-4 py-3 border-b border-stone-50 hover:bg-indigo-50 transition-colors ${story.id === currentId ? 'bg-indigo-50' : ''}`}>
                                            <div className={`text-sm font-bold mb-1 ${story.id === currentId ? 'text-indigo-700' : 'text-stone-800'}`}>{story.title}</div>
                                            <div className="flex justify-between text-xs text-stone-500"><span>{story.series}</span><span>{story.author}</span></div>
                                        </a>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            );
        };

        // --- Components ---
        const CharacterMap = ({ data }) => {
            return (
                <div className="space-y-8 max-w-4xl mx-auto">
                    {/* メタデータ */}
                    {(data.genre || data.keywords || data.highlights) && (
                        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-6 rounded-lg border border-indigo-200">
                            <h3 className="text-lg font-bold text-indigo-900 flex items-center gap-2 mb-4">
                                <Icons.FileText width="20" /> 作品情報
                            </h3>
                            <div className="grid gap-4">
                                {(data.genre || data.sub_genre) && (
                                    <div className="bg-white/80 p-4 rounded-md">
                                        <h4 className="font-bold text-sm text-indigo-800 mb-2">ジャンル</h4>
                                        <div className="flex flex-wrap gap-2">
                                            {data.genre && <span className="px-3 py-1 bg-indigo-600 text-white text-xs rounded-full">{data.genre}</span>}
                                            {data.japanese_genre && <span className="px-3 py-1 bg-purple-600 text-white text-xs rounded-full">{data.japanese_genre}</span>}
                                        </div>
                                    </div>
                                )}
                                {data.highlights && (
                                    <div className="bg-white/80 p-4 rounded-md">
                                        <h4 className="font-bold text-sm text-indigo-800 mb-2">見どころ</h4>
                                        <ul className="space-y-1.5 text-sm text-stone-700">{data.highlights.map((h, i) => <li key={i}>▸ {h}</li>)}</ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* 登場人物 */}
                    {data.characters && data.characters.length > 0 && (
                        <div className="bg-white p-6 rounded-lg border border-stone-200">
                            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b border-slate-200 pb-3 mb-4">
                                <Icons.User width="20" /> 登場人物
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {data.characters.map((char, idx) => (
                                    <div key={idx} className="bg-stone-50 p-4 rounded-lg border border-stone-200 flex gap-3">
                                        <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 text-indigo-600 font-bold text-sm">{char.name[0]}</div>
                                        <div className="flex-1">
                                            <div className="font-bold text-slate-900">{char.name}</div>
                                            {/* description または desc の両方に対応 */}
                                            <div className="text-sm text-slate-600 mt-1">{char.description || char.desc || ''}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            );
        };

        // 新規追加: 用語集コンポーネント
        const GlossaryList = ({ data }) => {
            const glossary = data.glossary || [];
            if (glossary.length === 0) return <div className="p-8 text-center text-stone-500">用語情報がありません</div>;

            return (
                <div className="max-w-3xl mx-auto bg-white p-8 rounded-lg shadow-sm border border-stone-200">
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-6 border-b border-slate-200 pb-2">
                        <Icons.Book width="20" /> 用語集
                    </h3>
                    <div className="grid gap-4">
                        {glossary.map((item, idx) => (
                            <div key={idx} className="p-4 bg-stone-50 rounded border border-stone-100">
                                <div className="font-bold text-indigo-800 mb-1 flex items-baseline gap-2">
                                    {item.term}
                                    {item.reading && <span className="text-xs text-stone-500 font-normal">({item.reading})</span>}
                                </div>
                                <div className="text-sm text-stone-700 leading-relaxed">
                                    {item.desc || item.description}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        };

        const Synopsis = ({ data }) => (
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-sm border border-stone-200">
                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-6 border-b border-slate-200 pb-2"><Icons.BookOpen width="20" /> あらすじ</h3>
                <div className="leading-loose text-stone-700 whitespace-pre-wrap">{data.synopsis || "あらすじ情報がありません"}</div>
            </div>
        );

        const AuthorProfile = ({ data }) => {
            const profile = data.authorProfile || { name: data.author, desc: "" };
            return (
                <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-sm border border-stone-200">
                    <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-6 border-b border-slate-200 pb-2"><Icons.Feather width="20" /> 作者紹介</h3>
                    <div className="flex flex-col sm:flex-row gap-6 items-start">
                        <div className="w-24 h-24 rounded-full bg-stone-200 flex items-center justify-center flex-shrink-0 mx-auto sm:mx-0">
                            <Icons.User width="40" className="text-stone-400" />
                        </div>
                        <div>
                            <h4 className="text-xl font-bold text-stone-900 mb-2">{profile.name}</h4>
                            {/* description または desc の両方に対応 */}
                            <div className="leading-loose text-stone-700 whitespace-pre-wrap">{profile.description || profile.desc || "詳細情報がありません"}</div>
                        </div>
                    </div>
                </div>
            );
        };

        const TableOfContents = ({ chapters, currentIdx, onSelect }) => (
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-sm border border-stone-200">
                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-6 border-b border-slate-200 pb-2"><Icons.List width="20" /> 目次</h3>
                <div className="flex flex-col">
                    {chapters.map((c, i) => (
                        <button key={i} onClick={() => onSelect(i)} className={`text-left px-4 py-4 border-b border-stone-100 hover:bg-stone-50 transition-colors flex items-center gap-3 ${currentIdx === i ? 'bg-amber-50 text-amber-900 font-bold' : 'text-stone-700'}`}>
                            <span className={`flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full text-xs ${currentIdx === i ? 'bg-amber-200 text-amber-800' : 'bg-stone-100 text-stone-500'}`}>{i + 1}</span>
                            <span>{c.title}</span>
                        </button>
                    ))}
                </div>
            </div>
        );

        // --- Trivia Widget Component ---
        const TriviaIcons = {
            Lightbulb: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z"/></svg>,
            Clock: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
            Close: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        };

        const EdoClock = ({ data }) => {
            return (
                <div className="space-y-4">
                    <div className="bg-amber-50 p-4 rounded-lg border border-amber-200 text-amber-900 text-base leading-relaxed">
                        {data.description}
                    </div>
                    <div className="grid gap-3 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
                        {data.hours.map((hour, idx) => (
                            <div key={idx} className="flex items-center gap-4 p-3 bg-white rounded shadow-sm border border-stone-100 hover:shadow-md transition-shadow">
                                <div className="w-12 h-12 rounded-full bg-indigo-900 text-white flex flex-col items-center justify-center flex-shrink-0">
                                    <span className="text-sm font-bold">{hour.zodiac}</span>
                                    <span className="text-xs opacity-80">{hour.bell_count}つ</span>
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-baseline mb-1">
                                        <h4 className="font-bold text-stone-800">{hour.name}</h4>
                                        <span className="text-sm font-mono text-stone-500 bg-stone-100 px-2 py-0.5 rounded">{hour.modern_approx}</span>
                                    </div>
                                    <p className="text-sm text-stone-600">{hour.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        };

        const TriviaWidget = () => {
            const [isOpen, setIsOpen] = useState(false);
            const [data, setData] = useState(null);
            const [loading, setLoading] = useState(false);

            useEffect(() => {
                if (isOpen && !data) {
                    setLoading(true);
                    // Hardcoded data for prototype
                    const edoData = {
                        "title": "江戸の時刻制度（不定時法）",
                        "description": "江戸時代は、日の出と日の入りを基準に昼と夜をそれぞれ6等分する「不定時法」が使われていました。季節によって一刻（いっとき）の長さが変わります。",
                        "hours": [
                            { "name": "明け六つ", "zodiac": "卯", "modern_approx": "06:00 (Sunrise)", "bell_count": 6, "description": "日の出の時刻。城門が開き、一日が始まります。「六つ」の鐘が鳴ります。" },
                            { "name": "朝五つ", "zodiac": "辰", "modern_approx": "08:00", "bell_count": 5, "description": "朝食の時間帯。武士が出仕する時間でもあります。" },
                            { "name": "昼四つ", "zodiac": "巳", "modern_approx": "10:00", "bell_count": 4, "description": "仕事が本格化する時間。" },
                            { "name": "昼九つ", "zodiac": "午", "modern_approx": "12:00 (Noon)", "bell_count": 9, "description": "正午。太陽が最も高い位置にあります。「九つ」の鐘が鳴ります。" },
                            { "name": "昼八つ", "zodiac": "未", "modern_approx": "14:00", "bell_count": 8, "description": "「おやつ」の語源。午後の間食の時間。" },
                            { "name": "夕七つ", "zodiac": "申", "modern_approx": "16:00", "bell_count": 7, "description": "仕事終わりの時間。銭湯が開く頃。" },
                            { "name": "暮れ六つ", "zodiac": "酉", "modern_approx": "18:00 (Sunset)", "bell_count": 6, "description": "日の入り。城門が閉まり、夜が始まります。" },
                            { "name": "夜五つ", "zodiac": "戌", "modern_approx": "20:00", "bell_count": 5, "description": "夜のくつろぎの時間。" },
                            { "name": "夜四つ", "zodiac": "亥", "modern_approx": "22:00", "bell_count": 4, "description": "就寝の時間。夜回りが始まります。" },
                            { "name": "夜九つ", "zodiac": "子", "modern_approx": "00:00 (Midnight)", "bell_count": 9, "description": "真夜中。草木も眠る丑三つ時の前。" },
                            { "name": "夜八つ", "zodiac": "丑", "modern_approx": "02:00", "bell_count": 8, "description": "「丑三つ時」はこの刻の真ん中（2:00〜2:30頃）。幽霊が出ると言われる。" },
                            { "name": "暁七つ", "zodiac": "寅", "modern_approx": "04:00", "bell_count": 7, "description": "夜明け前。市場などが動き出す準備の時間。" }
                        ]
                    };
                    setTimeout(() => {
                        setData(edoData);
                        setLoading(false);
                    }, 500);
                }
            }, [isOpen]);

            return (
                <React.Fragment>
                    <button 
                        onClick={() => setIsOpen(true)}
                        className={"p-2 rounded-full transition-colors " + (isOpen ? "bg-amber-100 text-amber-700" : "hover:bg-black/5")}
                        aria-label="雑学を開く"
                        title="雑学（江戸の時刻）"
                    >
                        <TriviaIcons.Lightbulb width="18" />
                    </button>

                    {isOpen && ReactDOM.createPortal(
                        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 font-sans">
                            <div 
                                className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
                                onClick={() => setIsOpen(false)}
                            ></div>
                            <div className="relative bg-white w-full max-w-3xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-fade-in-up">
                                <div className="bg-indigo-600 p-4 flex justify-between items-center text-white">
                                    <h3 className="font-bold text-lg sm:text-xl flex items-center gap-2">
                                        <TriviaIcons.Clock width="20" />
                                        {data ? data.title : '読み込み中...'}
                                    </h3>
                                    <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-white/20 rounded-full transition-colors">
                                        <TriviaIcons.Close width="20" />
                                    </button>
                                </div>
                                <div className="p-6 overflow-y-auto bg-stone-50 flex-1 text-base">
                                    {loading ? (
                                        <div className="flex justify-center py-8">
                                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                                        </div>
                                    ) : (
                                        data && <EdoClock data={data} />
                                    )}
                                </div>
                                <div className="p-3 bg-stone-100 border-t border-stone-200 text-center text-sm text-stone-500">
                                    丸竹書房 雑学アプリ
                                </div>
                            </div>
                        </div>,
                        document.body
                    )}
                </React.Fragment>
            );
        };

        // --- Main App ---
        const App = () => {
            const [activeTab, setActiveTab] = useState('read'); // read, synopsis, analysis, glossary, author
            const [idx, setIdx] = useState(0);
            const [mode, setMode] = useState('horizontal');
            const [fontSizeIdx, setFontSizeIdx] = useState(1); // 0: small, 1: medium, 2: large, 3: xl
            const [marginIdx, setMarginIdx] = useState(1); // 0: small, 1: medium, 2: large
            const [showMiniPlayer, setShowMiniPlayer] = useState(false);
            const [isPlayerMinimized, setIsPlayerMinimized] = useState(false);
            const [showSidebar, setShowSidebar] = useState(false);
            const [theme, setTheme] = useState('light');
            const [showUI, setShowUI] = useState(true); // UI visibility state
            const [showAppNav, setShowAppNav] = useState(false);
            const contentRef = React.useRef(null);
            const lastHashRef = React.useRef('');

            // Utabon (唄本) ミニプレイヤー設定
            const utabon = window.utabonConfig || {};
            const [utabonTracks, setUtabonTracks] = useState([]);
            const [utabonError, setUtabonError] = useState('');
            const [utabonSelected, setUtabonSelected] = useState(0);
            const [utabonRandom, setUtabonRandom] = useState(false);
            const audioRef = React.useRef(null);
            
            const data = window.immersiveCurrentData || { title: "読込エラー", chapters: [] };
            const library = window.immersiveLibrary || [];
            const currentId = window.immersiveCurrentPostId || 0;
            const chapters = data.chapters || [];

            // Bookmark Logic
            useEffect(() => {
                const savedData = localStorage.getItem(`uir_save_${currentId}`);
                if (savedData) {
                    try { const parsed = JSON.parse(savedData); if(parsed.idx !== undefined) setIdx(parsed.idx); } catch(e){}
                }
            }, [currentId]);

            useEffect(() => {
                localStorage.setItem(`uir_save_${currentId}`, JSON.stringify({ idx }));
                // チャプター変更時にスクロール位置をリセット
                if (contentRef.current) {
                    contentRef.current.scrollTop = 0;
                    // 縦書きの場合、ブラウザによってはscrollLeftの初期値が異なるが、0に設定することで多くのブラウザで初期位置（右端）になる
                    contentRef.current.scrollLeft = 0;
                }
            }, [idx, currentId, mode]);

            // テーマ設定（ダークモードのテキスト色を修正）
            const themeStyles = {
                light: { bg: 'bg-[#f7f4e9]', text: 'text-stone-800', ui: 'bg-white/95', border: 'border-stone-200', activeTab: 'bg-white text-indigo-700', inactiveTab: 'text-stone-500 hover:text-stone-700' },
                dark:  { bg: 'bg-[#1a1a1a]', text: 'text-stone-200',  ui: 'bg-[#2d2d2d]/95', border: 'border-gray-700', activeTab: 'bg-[#2d2d2d] text-indigo-400', inactiveTab: 'text-gray-400 hover:text-gray-200' },
                sepia: { bg: 'bg-[#f4ecd8]', text: 'text-[#5b4636]', ui: 'bg-[#e9e0d1]/95', border: 'border-[#d7cbb5]', activeTab: 'bg-[#e9e0d1] text-[#8c6b5d]', inactiveTab: 'text-[#8c6b5d]/70 hover:text-[#8c6b5d]' }
            };
            const currentTheme = themeStyles[theme];

            const buildAssetUrl = (baseUrl, relPath) => {
                if (!baseUrl || !relPath) return '';
                const base = baseUrl.replace(/\/+$/, '') + '/';
                const encoded = relPath.split('/').map(seg => encodeURIComponent(seg)).join('/');
                return base + encoded;
            };

            const buildUtabonTracks = (manifest, audioBaseUrl) => {
                if (!Array.isArray(manifest)) return [];
                const tracks = [];
                manifest.forEach(entry => {
                    const files = Array.isArray(entry?.related_files) ? entry.related_files : [];
                    const mp3s = files.filter(p => typeof p === 'string' && p.toLowerCase().endsWith('.mp3'));
                    if (mp3s.length === 0) return;

                    mp3s.forEach((p, i) => {
                        const fileName = p.split('/').pop() || p;
                        const label = mp3s.length === 1
                            ? (entry?.title || fileName)
                            : ((entry?.title || 'Untitled') + ' / ' + fileName);
                        tracks.push({
                            key: (entry?.slug || 'entry') + ':' + i,
                            label,
                            src: buildAssetUrl(audioBaseUrl, p)
                        });
                    });
                });
                return tracks;
            };

            useEffect(() => {
                const manifestUrl = utabon?.manifestUrl;
                const baseUrl = utabon?.assetBaseUrl;
                if (!manifestUrl || !baseUrl) {
                    setUtabonError('唄本（Utabon）の設定が未設定です（manifestUrl/assetBaseUrl）。');
                    return;
                }
                fetch(manifestUrl, { cache: 'no-store' })
                    .then(r => {
                        if (!r.ok) throw new Error('HTTP ' + r.status);
                        return r.json();
                    })
                    .then(json => {
                        const tracks = buildUtabonTracks(json, baseUrl);
                        setUtabonTracks(tracks);
                        if (tracks.length === 0) {
                            setUtabonError('唄本（Utabon）: 再生できるMP3が見つかりません（archive_manifest.json の related_files を確認してください）。');
                        } else {
                            setUtabonError('');
                        }
                    })
                    .catch(err => {
                        setUtabonError('唄本（Utabon）: manifest の読み込みに失敗しました（' + (err?.message || 'unknown') + '）。');
                    });
            }, []);
            
            const handleMusicToggle = () => {
                setShowMiniPlayer(prev => !prev);
                setIsPlayerMinimized(false); // 開くときは展開状態で
            };

            const playUtabonIndex = (nextIndex) => {
                const maxIndex = utabonTracks.length - 1;
                if (maxIndex < 0) return;
                const normalized = Math.max(0, Math.min(maxIndex, nextIndex));
                setUtabonSelected(normalized);
                setTimeout(() => {
                    if (audioRef.current) {
                        audioRef.current.load();
                        audioRef.current.play?.().catch(() => {});
                    }
                }, 0);
            };

            const pickRandomUtabonIndex = (currentIndex) => {
                const n = utabonTracks.length;
                if (n <= 1) return 0;
                let r = Math.floor(Math.random() * n);
                if (r === currentIndex) r = (r + 1) % n;
                return r;
            };
            
            // アプリナビゲーション用URL
            const appLinks = {
                reading: '/reading_library/',
                audiobook: '/audiobook_library/',
                themesong: '/themesong_library/'
            };

            // Glossary Tooltip Renderer
            const renderContentWithGlossary = (text, glossary) => {
                if (!glossary || glossary.length === 0 || !text) return text;
                const sortedTerms = [...glossary].sort((a, b) => b.term.length - a.term.length);
                const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const pattern = new RegExp(`(${sortedTerms.map(t => escapeRegExp(t.term)).join('|')})`, 'g');
                
                return text.split(pattern).map((part, i) => {
                    const item = sortedTerms.find(t => t.term === part);
                    if (item) {
                        return (
                            <span key={i} className="group relative inline-block border-b-2 border-dotted border-stone-400 cursor-help mx-0.5 z-10 text-inherit">
                                {part}
                                <span className="writing-horizontal-tb absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-[250px] sm:max-w-sm p-3 bg-stone-800 text-white text-sm rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 text-left leading-relaxed whitespace-normal font-sans">
                                    <span className="block font-bold text-amber-400 mb-1 text-base">{item.term} {item.reading && <span className="text-stone-400 font-normal text-sm">({item.reading})</span>}</span>
                                    {item.desc || item.description}
                                    <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-800"></span>
                                </span>
                            </span>
                        );
                    }
                    return part;
                });
            };

            const splitTextByAnchor = (text, anchor) => {
                if (!text || !anchor?.text) return [{ type: 'text', value: text }];
                const parts = [];
                let cursor = 0;
                let idx = text.indexOf(anchor.text);
                while (idx !== -1) {
                    if (idx > cursor) {
                        parts.push({ type: 'text', value: text.slice(cursor, idx) });
                    }
                    parts.push({ type: 'anchor', value: anchor.text, id: anchor.id });
                    cursor = idx + anchor.text.length;
                    idx = text.indexOf(anchor.text, cursor);
                }
                if (cursor < text.length) {
                    parts.push({ type: 'text', value: text.slice(cursor) });
                }
                return parts;
            };

            const renderContentWithGlossaryAndAnchors = (text, glossary, anchors) => {
                if (!anchors || anchors.length === 0) {
                    return renderContentWithGlossary(text, glossary);
                }
                let parts = [{ type: 'text', value: text }];
                anchors.forEach((anchor) => {
                    parts = parts.flatMap((part) => {
                        if (part.type !== 'text') return [part];
                        return splitTextByAnchor(part.value, anchor);
                    });
                });

                return parts.map((part, i) => {
                    if (part.type === 'anchor') {
                        return (
                            <span key={`anchor-${part.id}-${i}`} id={part.id} className="scroll-mt-24">
                                {renderContentWithGlossary(part.value, glossary)}
                            </span>
                        );
                    }
                    return (
                        <React.Fragment key={`text-${i}`}>
                            {renderContentWithGlossary(part.value, glossary)}
                        </React.Fragment>
                    );
                });
            };

            const fontSizes = ['small', 'medium', 'large', 'xl'];
            const getSize = () => {
                switch(fontSizes[fontSizeIdx]) {
                    case 'small': return 'text-sm leading-loose';
                    case 'medium': return 'text-base leading-loose';
                    case 'large': return 'text-xl leading-loose';
                    case 'xl': return 'text-2xl leading-loose';
                    default: return 'text-base leading-loose';
                }
            };

            const margins = ['small', 'medium', 'large'];
            const getMargin = () => {
                switch(margins[marginIdx]) {
                    case 'small': return 'p-4 sm:p-6';
                    case 'medium': return 'p-8 sm:p-12';
                    case 'large': return 'p-12 sm:p-20';
                    default: return 'p-8 sm:p-12';
                }
            };

            // 用語集データのマージ
            const mergedGlossary = [
                ...(data.glossary || []),
                ...(data.characters || []).map(c => ({ term: c.name, desc: c.description || c.desc, reading: c.role }))
            ];

            const anchors = React.useMemo(() => {
                return Array.isArray(data.anchors) ? data.anchors : [];
            }, [data]);

            useEffect(() => {
                if (activeTab !== 'read') return;
                const hash = window.location.hash ? window.location.hash.replace('#', '') : '';
                if (!hash || lastHashRef.current === `${hash}:${idx}`) return;
                const target = document.getElementById(hash);
                if (!target) return;
                lastHashRef.current = `${hash}:${idx}`;
                setTimeout(() => {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start',
                        inline: mode === 'vertical' ? 'center' : 'nearest'
                    });
                }, 50);
            }, [activeTab, idx, mode, anchors]);

            // Click Handler for Immersive UI
            const handleContentClick = (e) => {
                // インタラクティブな要素（ボタン、リンク、ツールチップなど）へのクリックは無視
                if (e.target.closest('button') || e.target.closest('a') || e.target.closest('.group')) return;

                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const width = rect.width;
                const el = contentRef.current;
                if (!el) return;

                // 画面の左25%
                if (x < width * 0.25) {
                    if (mode === 'vertical') {
                        // 縦書き（右から左）：左クリックは「次へ」
                        // 左端に到達しているか判定 (Chrome/Safari等でscrollLeftが負になる場合に対応)
                        // 右端が0、左に行くほどマイナスの場合、左端は -(scrollWidth - clientWidth)
                        const maxScroll = el.scrollWidth - el.clientWidth;
                        const currentAbs = Math.abs(el.scrollLeft);
                        
                        // 余裕を持って判定 (1px)
                        if (currentAbs >= maxScroll - 2) {
                            // 次のチャプターへ
                            setIdx(i => Math.min(chapters.length - 1, i + 1));
                        } else {
                            // 左へスクロール (負の方向)
                            el.scrollBy({ left: -width * 0.9, behavior: 'smooth' });
                        }
                    } else {
                        // 横書き（左から右）：左クリックは「前へ」
                        if (el.scrollTop <= 1) {
                            setIdx(i => Math.max(0, i - 1));
                        } else {
                            el.scrollBy({ top: -el.clientHeight * 0.9, behavior: 'smooth' });
                        }
                    }
                } 
                // 画面の右25%
                else if (x > width * 0.75) {
                    if (mode === 'vertical') {
                        // 縦書き（右から左）：右クリックは「前へ」
                        // 右端にいるかチェック (0に近いか)
                        if (Math.abs(el.scrollLeft) <= 1) {
                            setIdx(i => Math.max(0, i - 1));
                        } else {
                            el.scrollBy({ left: width * 0.9, behavior: 'smooth' });
                        }
                    } else {
                        // 横書き（左から右）：右クリックは「次へ」
                        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 1) {
                            setIdx(i => Math.min(chapters.length - 1, i + 1));
                        } else {
                            el.scrollBy({ top: el.clientHeight * 0.9, behavior: 'smooth' });
                        }
                    }
                } 
                // 中央エリア
                else {
                    setShowUI(prev => !prev);
                }
            };

            return (
                <div className={`w-full h-[85vh] min-h-[600px] ${currentTheme.bg} ${currentTheme.text} relative overflow-hidden font-serif transition-colors duration-300 border ${currentTheme.border} rounded-lg`}>
                    
                    {/* Header (Overlay) */}
                    <header className={`absolute top-0 left-0 right-0 z-40 transition-transform duration-300 ${showUI ? 'translate-y-0' : '-translate-y-full'} ${currentTheme.ui} border-b ${currentTheme.border} flex flex-col shadow-md`}>
                        <div className="px-4 py-2 flex items-center justify-between border-b border-stone-100/10">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                <LibraryNavigator library={library} currentId={currentId} />
                                <h1 className="font-bold text-sm sm:text-base m-0 truncate hidden sm:block">{data.title}</h1>
                            </div>
                            <div className="flex items-center gap-1">
                                <button onClick={()=>setMode(m=>m==='horizontal'?'vertical':'horizontal')} className="p-2 hover:bg-black/5 rounded"><Icons.FileText className={mode==='vertical'?'rotate-90':''} width="18" /></button>
                                <div className="flex items-center bg-black/5 rounded-lg p-0.5 gap-0.5 mx-1">
                                    <button onClick={()=>setFontSizeIdx(i=>Math.max(0,i-1))} disabled={fontSizeIdx===0} className="p-1.5 hover:bg-white/50 rounded disabled:opacity-30"><Icons.Minus width="14"/></button>
                                    <button onClick={()=>setFontSizeIdx(i=>Math.min(3,i+1))} disabled={fontSizeIdx===3} className="p-1.5 hover:bg-white/50 rounded disabled:opacity-30"><Icons.Plus width="14"/></button>
                                </div>
                                <button onClick={()=>setMarginIdx(i=>(i+1)%3)} className="p-2 hover:bg-black/5 rounded" title="余白サイズ変更"><Icons.Layout width="18" /></button>
                                <button onClick={() => setTheme(t => t === 'light' ? 'dark' : t === 'dark' ? 'sepia' : 'light')} className="p-2 hover:bg-black/5 rounded">{theme === 'light' ? '☀' : theme === 'dark' ? '☾' : '☕'}</button>
                                <TriviaWidget />
                                <button onClick={handleMusicToggle} className={`p-2 rounded-full ${showMiniPlayer?'bg-green-100 text-green-600':'hover:bg-black/5'}`} title="唄本（Utabon）"><Icons.Music width="18" /></button>
                            </div>
                        </div>

                        <nav className={`flex items-center justify-start md:justify-center overflow-x-auto border-b ${currentTheme.border} hide-scrollbar`}>
                            {[
                                { id: 'read', icon: Icons.BookOpen, label: '読む' },
                                { id: 'toc', icon: Icons.List, label: '目次' },
                                { id: 'synopsis', icon: Icons.Info, label: 'あらすじ' },
                                { id: 'analysis', icon: Icons.Map, label: '解説' },
                                { id: 'glossary', icon: Icons.Book, label: '用語集' },
                                { id: 'author', icon: Icons.Feather, label: '作者紹介' }
                            ].map(tab => (
                                <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${activeTab === activeTab ? '' : ''} ${activeTab === tab.id ? `border-indigo-600 ${currentTheme.activeTab}` : `border-transparent ${currentTheme.inactiveTab}`}`}>
                                    <tab.icon width="16" /> {tab.label}
                                </button>
                            ))}
                        </nav>
                    </header>

                    {/* Main Content */}
                    <div className="w-full h-full flex relative overflow-hidden">
                        <main className="flex-1 relative overflow-hidden flex flex-col w-full h-full">
                            {activeTab === 'read' && (
                                <>
                                    <div className={`absolute inset-y-0 left-0 w-64 bg-white border-r border-stone-200 transform transition-transform duration-300 z-50 shadow-xl ${showSidebar ? 'translate-x-0' : '-translate-x-full'}`}>
                                        <div className="p-4 flex justify-between items-center border-b"><span className="font-bold text-stone-800">目次</span><button onClick={()=>setShowSidebar(false)}><Icons.X width="20" className="text-stone-500"/></button></div>
                                        <div className="overflow-y-auto flex-1 pb-20">
                                            {chapters.map((c, i) => (
                                                <button key={i} onClick={()=>{setIdx(i);setShowSidebar(false);}} className={`w-full text-left px-4 py-3 border-b border-stone-100 text-sm ${idx===i? 'bg-amber-50 text-amber-900 font-bold border-r-4 border-r-amber-400': 'text-stone-600'}`}>{c.title}</button>
                                            ))}
                                        </div>
                                    </div>
                                    
                                    <div 
                                        ref={contentRef}
                                        className={`flex-1 ${getMargin()} transition-all duration-500 ${theme === 'light' ? "bg-[url('https://www.transparenttextures.com/patterns/rice-paper-2.png')]" : ""} 
                                        ${mode==='vertical' ? 'overflow-x-auto overflow-y-hidden h-full writing-vertical-rl' : 'overflow-y-auto w-full'}
                                        cursor-pointer hide-scrollbar`}
                                        style={mode==='vertical'?{writingMode:'vertical-rl',textOrientation:'upright'}:{}}
                                        onClick={handleContentClick}
                                    >
                                        <div className={`font-bold text-xl ${theme==='dark'?'text-amber-500':'text-amber-900'} mb-8 ${mode==='vertical'?'ml-6 mb-0 py-4 border-l-2 border-amber-200 pl-4':'pb-4 border-b-2 border-amber-200'}`}>
                                            {chapters[idx]?.title}
                                        </div>
                                        <div className={`${getSize()} ${currentTheme.text} ${theme==='dark'?'font-medium':''} tracking-wide whitespace-pre-wrap ${mode==='vertical'?'h-full py-4':''}`}>
                                            {renderContentWithGlossaryAndAnchors(
                                                mode === 'vertical' 
                                                    ? (chapters[idx]?.content || '').replace(/——/g, '︱︱').replace(/—/g, '︱').replace(/―/g, '︱').replace(/…/g, '︙').replace(/‥/g, '︰')
                                                    : chapters[idx]?.content,
                                                mergedGlossary,
                                                anchors
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* <button onClick={()=>setShowSidebar(!showSidebar)} className={`absolute bottom-20 left-6 p-3 bg-white rounded-full shadow-lg border border-stone-200 text-stone-600 hover:bg-stone-50 z-30 transition-transform duration-300 ${showUI ? 'translate-y-0' : 'translate-y-20'}`}><Icons.List width="20" /></button> */}
                                </>
                            )}
                            {activeTab !== 'read' && (
                                <div className="flex-1 overflow-y-auto p-4 sm:p-8 pt-32">
                                    <div className="max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2 duration-500">
                                        {activeTab === 'toc' && <TableOfContents chapters={chapters} currentIdx={idx} onSelect={(i) => { setIdx(i); setActiveTab('read'); }} />}
                                        {activeTab === 'synopsis' && <Synopsis data={data} />}
                                        {activeTab === 'analysis' && <CharacterMap data={data} />}
                                        {activeTab === 'glossary' && <GlossaryList data={data} />}
                                        {activeTab === 'author' && <AuthorProfile data={data} />}
                                    </div>
                                </div>
                            )}
                        </main>
                    </div>

                    {/* Footer (Overlay) */}
                    <footer className={`absolute bottom-0 left-0 right-0 z-40 transition-transform duration-300 ${showUI ? 'translate-y-0' : 'translate-y-full'} ${currentTheme.ui} border-t ${currentTheme.border} p-4 flex justify-between items-center shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]`}>
                        <button disabled={idx===0} onClick={()=>setIdx(i=>Math.max(0,i-1))} className="flex items-center gap-2 px-4 py-2 rounded hover:bg-black/5 disabled:opacity-30 transition-colors">
                            <Icons.ChevronLeft width="20" /> 前へ
                        </button>
                        <span className="font-bold text-sm">{idx+1} / {chapters.length}</span>
                        <button disabled={idx===chapters.length-1} onClick={()=>setIdx(i=>Math.min(chapters.length-1,i+1))} className="flex items-center gap-2 px-4 py-2 rounded hover:bg-black/5 disabled:opacity-30 transition-colors">
                            次へ <Icons.ChevronRight width="20" />
                        </button>
                    </footer>

                    {/* Mini Music Player - フローティング（最小化対応） */}
                    {showMiniPlayer && (
                        <div 
                            className="fixed bottom-24 z-50 transition-all duration-300"
                            style={{
                                right: isPlayerMinimized ? '-280px' : '16px'
                            }}
                        >
                            {/* 最小化時のタブ（左側に表示） */}
                            {isPlayerMinimized && (
                                <button
                                    onClick={() => setIsPlayerMinimized(false)}
                                    className="absolute -left-12 top-1/2 -translate-y-1/2 w-10 h-20 bg-gradient-to-r from-green-600 to-green-700 rounded-l-xl shadow-lg flex flex-col items-center justify-center gap-1 hover:from-green-500 hover:to-green-600 transition-colors"
                                >
                                    <Icons.Music width="18" className="text-white" />
                                    <Icons.ChevronLeft width="14" className="text-white/80" />
                                </button>
                            )}
                            
                            <div className="bg-gradient-to-br from-gray-900 to-black rounded-2xl shadow-2xl overflow-hidden" style={{width: '320px'}}>
                                {/* ヘッダー */}
                                <div className="p-2 flex items-center justify-between bg-black/50">
                                    <div className="flex items-center gap-2 min-w-0">
                                        <span className="text-white text-base font-bold truncate">🎵 {utabon?.label || 'Utabon（唄本）'}</span>
                                        <span className="text-white/50 text-xs">{utabonTracks?.length ? utabonTracks.length + ' tracks' : ''}</span>
                                    </div>
                                    <div className="flex gap-1">
                                        <button 
                                            onClick={() => setIsPlayerMinimized(true)} 
                                            className="text-white/60 hover:text-white p-1" 
                                            title="最小化"
                                        >
                                            <Icons.ChevronRight width="18" />
                                        </button>
                                        <button 
                                            onClick={() => setShowMiniPlayer(false)} 
                                            className="text-white/60 hover:text-white p-1"
                                            title="閉じる"
                                        >
                                            <Icons.X width="18" />
                                        </button>
                                    </div>
                                </div>

                                {/* Utabon (ローカルMP3) プレイヤー */}
                                <div>
                                    {utabonError ? (
                                        <div className="p-3 text-xs text-white/80">
                                            <div className="font-bold text-amber-300 mb-1">唄本（Utabon）</div>
                                            <div className="text-white/70">{utabonError}</div>
                                            {utabon?.manifestUrl ? (
                                                <a href={utabon.manifestUrl} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-white/60 hover:text-white">
                                                    manifest を開く <Icons.ExternalLink width="10" />
                                                </a>
                                            ) : null}
                                        </div>
                                    ) : (
                                        <div>
                                            <div className="p-2 bg-amber-900/20 flex flex-wrap gap-1">
                                                <select
                                                    value={String(utabonSelected)}
                                                    onChange={(e) => {
                                                        const next = parseInt(e.target.value, 10);
                                                        playUtabonIndex(Number.isFinite(next) ? next : 0);
                                                    }}
                                                    className="flex-1 bg-gray-800 text-white text-sm rounded px-2 py-1 border-none"
                                                >
                                                    {utabonTracks.map((t, i) => (
                                                        <option key={t.key || i} value={String(i)}>{t.label}</option>
                                                    ))}
                                                </select>
                                                <button
                                                    onClick={() => setUtabonRandom(v => !v)}
                                                    className={"px-2 py-1 rounded text-sm font-bold " + (utabonRandom ? "bg-amber-500 text-black" : "bg-gray-800 text-white/80 hover:text-white")}
                                                    title={utabonRandom ? "ランダム再生: ON" : "ランダム再生: OFF"}
                                                >
                                                    RND
                                                </button>
                                            </div>
                                            <div className="px-2 pb-2">
                                                <audio
                                                    ref={audioRef}
                                                    controls
                                                    preload="metadata"
                                                    controlsList="nodownload noplaybackrate"
                                                    onContextMenu={(e) => e.preventDefault()}
                                                    style={{ width: '100%' }}
                                                    src={utabonTracks[utabonSelected]?.src || ''}
                                                    onEnded={() => {
                                                        if (!utabonTracks.length) return;
                                                        if (utabonRandom) {
                                                            playUtabonIndex(pickRandomUtabonIndex(utabonSelected));
                                                            return;
                                                        }
                                                        if (utabonSelected < utabonTracks.length - 1) {
                                                            playUtabonIndex(utabonSelected + 1);
                                                        }
                                                    }}
                                                />
                                            </div>
                                            <div className="px-3 py-2 bg-amber-900/30 flex justify-between items-center">
                                                <span className="text-amber-100 text-sm sm:text-base font-semibold truncate">{utabonTracks[utabonSelected]?.label || ''}</span>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => playUtabonIndex(utabonSelected - 1)}
                                                        disabled={utabonSelected <= 0}
                                                        className="text-white/60 hover:text-white disabled:opacity-30"
                                                        title="前へ"
                                                    >
                                                        <Icons.ChevronLeft width="14" />
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            if (utabonRandom) {
                                                                playUtabonIndex(pickRandomUtabonIndex(utabonSelected));
                                                                return;
                                                            }
                                                            playUtabonIndex(utabonSelected + 1);
                                                        }}
                                                        disabled={utabonSelected >= utabonTracks.length - 1}
                                                        className="text-white/60 hover:text-white disabled:opacity-30"
                                                        title={utabonRandom ? "次へ（ランダム）" : "次へ"}
                                                    >
                                                        <Icons.ChevronRight width="14" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* App Navigation - 左下に配置（読書中邪魔にならない位置） */}
                    <div className="fixed bottom-4 left-4 z-50">
                        <button 
                            onClick={() => setShowAppNav(!showAppNav)}
                            className={"w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 " + (showAppNav ? "bg-indigo-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50")}
                            style={showAppNav ? {transform: 'rotate(45deg)'} : {}}
                        >
                            <Icons.Plus width="24" />
                        </button>
                        
                        {showAppNav && (
                            <div className="absolute bottom-16 left-0 flex flex-col gap-2">
                                <a href="/audiobook_library/" className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-lg hover:bg-amber-50 hover:text-amber-700 transition-colors whitespace-nowrap">
                                    <span className="text-lg">🎧</span>
                                    <span className="text-sm font-medium">朗読を聴く</span>
                                </a>
                                <a href="/themesong_library/" className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-lg hover:bg-green-50 hover:text-green-700 transition-colors whitespace-nowrap">
                                    <span className="text-lg">🎵</span>
                                    <span className="text-sm font-medium">唄本</span>
                                </a>
                                <a href="/" className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-lg hover:bg-blue-50 hover:text-blue-700 transition-colors whitespace-nowrap">
                                    <span className="text-lg">🏠</span>
                                    <span className="text-sm font-medium">ホーム</span>
                                </a>
                            </div>
                        )}
                    </div>

                </div>
            );
        };
        const root = ReactDOM.createRoot(document.getElementById('<?php echo $uid; ?>'));
        root.render(<App />);
    })();
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode( 'immersive_reader', 'uir_shortcode_handler' );


// =============================================================================
// [trivia_app] ショートコード - 雑学アプリ（スタンドアロンモード）
// =============================================================================

// wpautop による <p> タグ挿入を trivia_app ショートコードに対して回避
function tao_trivia_shortcode_unautop( $content ) {
    // [trivia_app ...] の周囲から余計な <p>, </p>, <br> を除去
    $content = preg_replace( '/<p>\s*(\[trivia_app[^\]]*\])\s*<\/p>/i', '$1', $content );
    $content = preg_replace( '/<br\s*\/?>\s*(\[trivia_app)/i', '$1', $content );
    return $content;
}
add_filter( 'the_content', 'tao_trivia_shortcode_unautop', 9 );

function trivia_app_shortcode_handler( $atts ) {
    $atts = shortcode_atts( array( 'file' => '' ), $atts, 'trivia_app' );

    // テンプレ内で利用するデータを事前に構築（includeのスコープで参照できる）
    $trivia_file_url = '';
    if (!empty($atts['file'])) {
        $trivia_file_url = esc_url_raw($atts['file']);
    }
    $app_data = tao_trivia_load_app_data_from_file_url($trivia_file_url);

    // スタンドアロンテンプレートを読み込んで終了（ヘッダー・フッターを出力させない）
    // 配置ゆれに対応：
    // - このプラグイン配下（plugin_dir_path）
    // - 通常プラグイン配下（WP_PLUGIN_DIR）
    // - mu-plugins 配下（WPMU_PLUGIN_DIR）
    // 例: wp-content/plugins/Reading_library/trivia-widget/trivia-app-template.php
    $plugin_dir = trailingslashit( plugin_dir_path( __FILE__ ) );
    $candidate_paths = array(
        // このファイルと同じプラグイン配下
        $plugin_dir . 'Reading_library/trivia-widget/trivia-app-template.php',
        $plugin_dir . 'trivia-app-template.php',
        $plugin_dir . 'trivia-widget/trivia-app-template.php',
    );

    if ( defined( 'WP_PLUGIN_DIR' ) ) {
        $wp_plugin_dir = trailingslashit( WP_PLUGIN_DIR );
        $candidate_paths[] = $wp_plugin_dir . 'Reading_library/trivia-widget/trivia-app-template.php';
        $candidate_paths[] = $wp_plugin_dir . 'reading_library/trivia-widget/trivia-app-template.php';
        $candidate_paths[] = $wp_plugin_dir . 'trivia-widget/trivia-app-template.php';
    }

    if ( defined( 'WPMU_PLUGIN_DIR' ) ) {
        $wpmu_plugin_dir = trailingslashit( WPMU_PLUGIN_DIR );
        $candidate_paths[] = $wpmu_plugin_dir . 'Reading_library/trivia-widget/trivia-app-template.php';
        $candidate_paths[] = $wpmu_plugin_dir . 'reading_library/trivia-widget/trivia-app-template.php';
        $candidate_paths[] = $wpmu_plugin_dir . 'trivia-widget/trivia-app-template.php';
    }

    // 外部から上書きできるように
    if ( function_exists( 'apply_filters' ) ) {
        $candidate_paths = apply_filters( 'tao_trivia_app_template_candidates', $candidate_paths, $app_data, $atts );
    }

    foreach ( $candidate_paths as $template_path ) {
        if ( $template_path && file_exists( $template_path ) ) {
            include $template_path;
            exit;
        }
    }

    return 'エラー: Trivia App テンプレートが見つかりません。' .
        ' テンプレートを wp-content/plugins/Reading_library/trivia-widget/trivia-app-template.php に配置するか、' .
        'フィルタ tao_trivia_app_template_candidates でパスを追加してください。';
}
add_shortcode( 'trivia_app', 'trivia_app_shortcode_handler' );


// =============================================================================
// 管理画面: 雑学アプリ JSON アップロード
// =============================================================================

function tao_trivia_uploader_page() {
    $message = '';
    $message_type = '';

    if (isset($_POST['tao_trivia_upload_json']) && wp_verify_nonce($_POST['tao_trivia_nonce'], 'tao_trivia_json_upload')) {
        $result = tao_trivia_process_json_upload();
        $message = $result['message'];
        $message_type = $result['type'];
    }

    // カテゴリを取得/作成
    $category = get_category_by_slug('trivia_application');
    if (!$category) {
        $cat_id = wp_create_category('trivia_application');
        $category = get_category($cat_id);
    }
    ?>
    <div class="wrap">
        <h1><span class="dashicons dashicons-lightbulb" style="font-size:30px;margin-right:10px;"></span>雑学アプリ用 JSON アップロード</h1>

        <?php if ($message): ?>
            <div class="notice notice-<?php echo esc_attr($message_type); ?> is-dismissible">
                <p><?php echo wp_kses_post($message); ?></p>
            </div>
        <?php endif; ?>

        <div class="card" style="max-width:800px;margin-top:20px;">
            <h2>JSONファイルをアップロード</h2>
            <p>雑学アプリ用の <code>.json</code> ファイルをアップロードして、投稿を自動作成・更新します。</p>

            <form method="post" enctype="multipart/form-data" style="margin-top:20px;">
                <?php wp_nonce_field('tao_trivia_json_upload', 'tao_trivia_nonce'); ?>

                <table class="form-table">
                    <tr>
                        <th scope="row"><label for="json_file">JSONファイル</label></th>
                        <td>
                            <input type="file" name="json_file" id="json_file" accept=".json" required style="margin-bottom:10px;">
                            <p class="description">例: <code>{"title":"...","description":"...","hours":[...]}</code></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="post_status">投稿ステータス</label></th>
                        <td>
                            <select name="post_status" id="post_status">
                                <option value="draft">下書き</option>
                                <option value="publish">公開</option>
                                <option value="private">非公開</option>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="topic_tag">タグ（任意）</label></th>
                        <td>
                            <input type="text" name="topic_tag" id="topic_tag" class="regular-text" placeholder="例: 江戸, 文化, 歴史">
                            <p class="description">空欄でもOK（投稿は作成されます）</p>
                        </td>
                    </tr>
                </table>

                <p class="submit">
                    <input type="submit" name="tao_trivia_upload_json" class="button button-primary button-large" value="アップロードして投稿作成">
                </p>
            </form>
        </div>

        <div class="card" style="max-width:800px;margin-top:20px;">
            <h2>最近の雑学アプリ投稿</h2>
            <?php
            $recent_posts = get_posts(array(
                'post_type' => 'post',
                'category_name' => 'trivia_application',
                'numberposts' => -1,
                'post_status' => array('publish', 'draft', 'private'),
                'orderby' => 'date',
                'order' => 'DESC'
            ));

            if ($recent_posts): ?>
                <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                    <input
                        type="text"
                        id="tao-trivia-post-search"
                        class="regular-text"
                        placeholder="タイトル・タグで検索..."
                        style="max-width:420px;"
                    />
                    <span id="tao-trivia-post-search-count" style="color:#666;font-size:12px;">全<?php echo esc_html( count($recent_posts) ); ?>件</span>
                </div>
                <table class="widefat striped" style="margin-top:10px;">
                    <thead>
                        <tr>
                            <th>タイトル</th>
                            <th>タグ</th>
                            <th>日時</th>
                            <th>ステータス</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($recent_posts as $post):
                            $tags = get_the_tags($post->ID);
                            $tag_text = $tags ? implode(', ', array_map(function($t){ return $t->name; }, $tags)) : '-';
                        ?>
                            <tr>
                                <td><strong><?php echo esc_html($post->post_title); ?></strong></td>
                                <td><?php echo esc_html($tag_text); ?></td>
                                <td><?php echo get_the_date('Y/m/d H:i', $post); ?></td>
                                <td>
                                    <?php
                                    $status_labels = array('publish' => '公開', 'draft' => '下書き', 'private' => '非公開');
                                    echo esc_html($status_labels[$post->post_status] ?? $post->post_status);
                                    ?>
                                </td>
                                <td>
                                    <a href="<?php echo admin_url('admin.php?page=tao-trivia-editor&post_id=' . $post->ID); ?>" class="button button-small button-primary">データ編集</a>
                                    <a href="<?php echo get_edit_post_link($post->ID); ?>" class="button button-small">WP編集</a>
                                    <a href="<?php echo get_permalink($post->ID); ?>" class="button button-small" target="_blank">表示</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                <script>
                (function() {
                    const input = document.getElementById('tao-trivia-post-search');
                    const table = input ? input.closest('.card')?.querySelector('table') : null;
                    const countEl = document.getElementById('tao-trivia-post-search-count');
                    if (!input || !table) return;
                    const rows = Array.from(table.querySelectorAll('tbody tr'));
                    const update = () => {
                        const term = (input.value || '').trim().toLowerCase();
                        let visible = 0;
                        rows.forEach(tr => {
                            const text = (tr.innerText || '').toLowerCase();
                            const show = !term || text.includes(term);
                            tr.style.display = show ? '' : 'none';
                            if (show) visible += 1;
                        });
                        if (countEl) countEl.textContent = term ? `${visible}件 / ${rows.length}件` : `全${rows.length}件`;
                    };
                    input.addEventListener('input', update);
                    update();
                })();
                </script>
            <?php else: ?>
                <p>まだ雑学アプリ用の投稿がありません。</p>
            <?php endif; ?>
        </div>
    </div>
    <?php
}

/**
 * 雑学データ編集ページ（JSON生データを直接編集して保存）
 */
function tao_trivia_editor_page() {
    $post_id = isset($_GET['post_id']) ? intval($_GET['post_id']) : 0;
    $post = get_post($post_id);

    if (!$post) {
        echo '<div class="wrap"><div class="notice notice-error"><p>投稿が見つかりません。</p></div></div>';
        return;
    }

    $message = '';
    $message_type = '';

    // JSONファイルURL（メタ優先、なければ本文ショートコードから抽出）
    $file_url = (string) get_post_meta($post_id, '_tao_trivia_file', true);
    if ($file_url === '' && preg_match('/\[trivia_app\s+file="([^"]+)"\]/', (string)$post->post_content, $m)) {
        $file_url = (string) $m[1];
    }

    $upload_dir = wp_upload_dir();
    $baseurl = $upload_dir['baseurl'] ?? '';
    $basedir = $upload_dir['basedir'] ?? '';

    // URL -> ローカルパス変換（uploads配下のみ）
    $file_path = '';
    if ($file_url && $baseurl && $basedir && strpos($file_url, $baseurl) === 0) {
        $relative = ltrim(substr($file_url, strlen($baseurl)), '/');
        $file_path = rtrim($basedir, '/') . '/' . $relative;
    }

    // 削除処理（投稿 + JSONファイル）
    if (isset($_POST['tao_trivia_delete_post']) && wp_verify_nonce($_POST['tao_trivia_delete_nonce'] ?? '', 'tao_trivia_delete_post_' . $post_id)) {
        if (!current_user_can('delete_post', $post_id)) {
            $message = '削除権限がありません。';
            $message_type = 'error';
        } else {
            // uploads配下のJSONファイルだけ削除対象にする
            if ($file_path && $basedir && strpos($file_path, rtrim($basedir, '/') . '/') === 0 && file_exists($file_path)) {
                @unlink($file_path);
            }

            wp_delete_post($post_id, true);
            wp_safe_redirect(admin_url('admin.php?page=tao-trivia-uploader'));
            exit;
        }
    }

    // 保存処理
    if (isset($_POST['tao_trivia_save_data']) && check_admin_referer('tao_trivia_save_data_' . $post_id)) {
        $raw_json = wp_unslash($_POST['raw_json'] ?? '');
        $decoded = json_decode($raw_json, true);

        if (!is_array($decoded) || json_last_error() !== JSON_ERROR_NONE) {
            $message = 'JSONの形式が正しくありません: ' . json_last_error_msg();
            $message_type = 'error';
        } else {
            $trivia_title = sanitize_text_field($decoded['title'] ?? '');
            if ($trivia_title === '') {
                $message = 'JSONに title フィールドがありません。';
                $message_type = 'error';
            } else {
                // 保存先が未設定なら、uploads/trivia-app-data に新規作成し、投稿本文も file 付きショートコードに更新
                if ($file_url === '' || $file_path === '') {
                    $json_dir = rtrim($basedir, '/') . '/trivia-app-data';
                    if (!file_exists($json_dir)) {
                        wp_mkdir_p($json_dir);
                        @file_put_contents($json_dir . '/.htaccess', 'Options -Indexes');
                    }

                    $safe_filename = sanitize_file_name($trivia_title) . '_' . time() . '.json';
                    $file_path = $json_dir . '/' . $safe_filename;
                    $file_url = rtrim($baseurl, '/') . '/trivia-app-data/' . $safe_filename;

                    wp_update_post(array(
                        'ID' => $post_id,
                        'post_content' => '[trivia_app file="' . esc_attr($file_url) . '"]',
                    ));
                } else {
                    $dir = dirname($file_path);
                    if (!file_exists($dir)) {
                        wp_mkdir_p($dir);
                    }
                }

                $json_string = json_encode($decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
                $saved = (is_string($file_path) && $file_path !== '') ? @file_put_contents($file_path, $json_string) : false;

                if ($saved === false) {
                    $message = 'JSONファイルの保存に失敗しました。書き込み権限やパスを確認してください。';
                    $message_type = 'error';
                } else {
                    $description = '';
                    if (!empty($decoded['description'])) {
                        $description = sanitize_textarea_field($decoded['description']);
                    }
                    $meta_description = mb_substr(str_replace(array("\r", "\n"), ' ', $description), 0, 160);
                    $post_title = sprintf('雑学　%s　発行元丸竹書房', $trivia_title);

                    wp_update_post(array(
                        'ID' => $post_id,
                        'post_title' => $post_title,
                    ));

                    update_post_meta($post_id, '_tao_trivia_title', $trivia_title);
                    update_post_meta($post_id, '_tao_trivia_file', $file_url);
                    update_post_meta($post_id, '_tao_trivia_seo_title', $post_title);
                    update_post_meta($post_id, '_tao_trivia_meta_description', $meta_description);

                    // THE THOR/他SEOプラグイン用
                    update_post_meta($post_id, 'title', $post_title);
                    update_post_meta($post_id, 'description', $meta_description);

                    $message = 'データを保存しました。';
                    $message_type = 'success';
                }
            }
        }
    }

    // 読み込み
    $json_string = '';
    if ($file_path && file_exists($file_path)) {
        $json_string = file_get_contents($file_path);
    } elseif ($file_url) {
        $resp = wp_remote_get($file_url, array('timeout' => 10));
        if (!is_wp_error($resp)) {
            $code = wp_remote_retrieve_response_code($resp);
            $body = wp_remote_retrieve_body($resp);
            if ($code >= 200 && $code < 300 && is_string($body)) {
                $json_string = $body;
            }
        }
    }

    $data = null;
    if (is_string($json_string) && trim($json_string) !== '') {
        $data = json_decode($json_string, true);
    }
    if (!is_array($data)) {
        $data = array();
        if (!$message) {
            $message = 'JSONデータの読み込みに失敗しました。まずはJSONを貼り付けて保存してください。';
            $message_type = 'warning';
        }
    }

    $raw_json_default = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if (!is_string($raw_json_default) || $raw_json_default === '') {
        $raw_json_default = "{\n  \"title\": \"\",\n  \"description\": \"\",\n  \"hours\": []\n}";
    }

    ?>
    <div class="wrap">
        <h1>雑学データ編集: <?php echo esc_html($post->post_title); ?></h1>

        <?php if ($message): ?>
            <div class="notice notice-<?php echo esc_attr($message_type); ?> is-dismissible">
                <p><?php echo esc_html($message); ?></p>
            </div>
        <?php endif; ?>

        <div class="card" style="max-width:980px;margin-top:20px;">
            <p>
                <strong>JSONファイル:</strong>
                <?php if ($file_url): ?>
                    <a href="<?php echo esc_url($file_url); ?>" target="_blank" rel="noopener noreferrer"><?php echo esc_html($file_url); ?></a>
                <?php else: ?>
                    <span style="color:#666;">（未作成：保存時に自動作成されます）</span>
                <?php endif; ?>
            </p>

            <p style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                <a class="button" href="<?php echo esc_url(get_permalink($post_id)); ?>" target="_blank" rel="noopener noreferrer">表示（プレビュー）</a>
                <a class="button" href="<?php echo esc_url(get_edit_post_link($post_id)); ?>">WP編集</a>
            </p>
        </div>

        <form method="post" style="max-width:980px;">
            <?php wp_nonce_field('tao_trivia_save_data_' . $post_id); ?>
            <?php wp_nonce_field('tao_trivia_delete_post_' . $post_id, 'tao_trivia_delete_nonce'); ?>

            <div class="postbox" style="margin-top:20px;">
                <div class="postbox-header"><h2 class="hndle">JSON生データ編集</h2></div>
                <div class="inside">
                    <p>JSONを直接編集して「変更を保存」を押すと、uploads配下のJSONファイルに保存されます（投稿タイトル/SEOメタも同期します）。</p>
                    <textarea name="raw_json" rows="22" class="large-text code" style="font-family:monospace; background:#f0f0f1;"><?php echo esc_textarea($raw_json_default); ?></textarea>
                </div>
            </div>

            <p class="submit" style="margin-top:10px;">
                <input type="submit" name="tao_trivia_save_data" class="button button-primary button-large" value="変更を保存">
                <button
                    type="submit"
                    name="tao_trivia_delete_post"
                    class="button button-large"
                    formaction="<?php echo esc_url(admin_url('admin.php?page=tao-trivia-editor&post_id=' . $post_id)); ?>"
                    formmethod="post"
                    onclick="return confirm('この雑学投稿を削除しますか？\n（JSONファイルも削除されます）');"
                    style="margin-left:8px; color:#b32d2e; border-color:#b32d2e;"
                >削除</button>
                <a href="<?php echo admin_url('admin.php?page=tao-trivia-uploader'); ?>" class="button button-large" style="margin-left:8px;">一覧に戻る</a>
            </p>
        </form>
    </div>
    <?php
}

function tao_trivia_process_json_upload() {
    if (!isset($_FILES['json_file']) || $_FILES['json_file']['error'] !== UPLOAD_ERR_OK) {
        return array('type' => 'error', 'message' => 'ファイルのアップロードに失敗しました。');
    }

    $file = $_FILES['json_file'];
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if ($ext !== 'json') {
        return array('type' => 'error', 'message' => 'JSONファイル (.json) のみアップロードできます。');
    }

    $content = file_get_contents($file['tmp_name']);
    if ($content === false) {
        return array('type' => 'error', 'message' => 'ファイルの読み込みに失敗しました。');
    }

    $content = trim($content);
    $data = json_decode($content, true);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($data)) {
        return array(
            'type' => 'error',
            'message' => 'JSONの解析に失敗しました: ' . json_last_error_msg() . '<br>ファイル: ' . esc_html($file['name'])
        );
    }

    if (empty($data['title'])) {
        return array('type' => 'error', 'message' => 'JSONに title フィールドがありません。');
    }

    $trivia_title = sanitize_text_field($data['title']);
    $post_title = sprintf('雑学　%s　発行元丸竹書房', $trivia_title);

    $description = '';
    if (!empty($data['description'])) {
        $description = sanitize_textarea_field($data['description']);
    }
    $meta_description = mb_substr(str_replace(array("\r", "\n"), ' ', $description), 0, 160);

    // ===== JSONファイルをサーバーに保存 =====
    $upload_dir = wp_upload_dir();
    $json_dir = $upload_dir['basedir'] . '/trivia-app-data';

    if (!file_exists($json_dir)) {
        wp_mkdir_p($json_dir);
        file_put_contents($json_dir . '/.htaccess', 'Options -Indexes');
    }

    $safe_filename = sanitize_file_name($trivia_title) . '_' . time() . '.json';
    $json_file_path = $json_dir . '/' . $safe_filename;
    $json_file_url = $upload_dir['baseurl'] . '/trivia-app-data/' . $safe_filename;

    $json_string = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if (file_put_contents($json_file_path, $json_string) === false) {
        return array('type' => 'error', 'message' => 'JSONファイルの保存に失敗しました。');
    }

    $post_content = '[trivia_app file="' . esc_attr($json_file_url) . '"]';

    // カテゴリ
    $category = get_category_by_slug('trivia_application');
    $category_id = $category ? $category->term_id : 0;
    if (!$category_id) {
        $category_id = wp_create_category('trivia_application');
    }

    $post_status = sanitize_text_field($_POST['post_status'] ?? 'draft');
    $topic_tag = sanitize_text_field($_POST['topic_tag'] ?? '');

    // 既存投稿（title一致）を検索
    $existing_posts = get_posts(array(
        'post_type' => 'post',
        'meta_key' => '_tao_trivia_title',
        'meta_value' => $trivia_title,
        'posts_per_page' => 1
    ));

    global $wpdb;
    if (!empty($existing_posts)) {
        $post_id = $existing_posts[0]->ID;

        $wpdb->update(
            $wpdb->posts,
            array(
                'post_title' => $post_title,
                'post_status' => $post_status,
            ),
            array('ID' => $post_id),
            array('%s', '%s'),
            array('%d')
        );

        $wpdb->update(
            $wpdb->posts,
            array('post_content' => $post_content),
            array('ID' => $post_id),
            array('%s'),
            array('%d')
        );

        $action = '更新';
    } else {
        $post_data = array(
            'post_title'    => $post_title,
            'post_content'  => '',
            'post_status'   => $post_status,
            'post_type'     => 'post',
            'post_category' => array($category_id),
        );

        $post_id = wp_insert_post($post_data, true);

        if (!is_wp_error($post_id) && $post_id > 0) {
            $wpdb->update(
                $wpdb->posts,
                array('post_content' => $post_content),
                array('ID' => $post_id),
                array('%s'),
                array('%d')
            );
        }
        $action = '作成';
    }

    if (is_wp_error($post_id)) {
        return array('type' => 'error', 'message' => '投稿の作成に失敗しました: ' . $post_id->get_error_message());
    }
    if (empty($post_id) || $post_id === 0) {
        return array('type' => 'error', 'message' => '投稿の作成に失敗しました。投稿IDが取得できませんでした。');
    }

    update_post_meta($post_id, '_tao_trivia_title', $trivia_title);
    update_post_meta($post_id, '_tao_trivia_file', $json_file_url);
    update_post_meta($post_id, '_tao_trivia_seo_title', $post_title);
    update_post_meta($post_id, '_tao_trivia_meta_description', $meta_description);

    // THE THOR/他SEOプラグイン用（読書アプリと同じ思想）
    update_post_meta($post_id, 'title', $post_title);
    update_post_meta($post_id, 'description', $meta_description);

    if (!empty($topic_tag)) {
        $tags = array_filter(array_map('trim', preg_split('/[,、]/u', $topic_tag)));
        if (!empty($tags)) wp_set_post_tags($post_id, $tags, false);
    }

    $edit_link = admin_url('post.php?post=' . $post_id . '&action=edit');
    $view_link = get_permalink($post_id);
    if (empty($view_link)) $view_link = home_url('?p=' . $post_id);

    return array(
        'type' => 'success',
        'message' => sprintf(
            '<strong>「%s」を%sしました！</strong><br>' .
            '<strong>投稿タイトル:</strong> %s<br>' .
            '<strong>meta description:</strong> %s...<br>' .
            '<a href="%s" class="button button-small">編集</a> ' .
            '<a href="%s" class="button button-small" target="_blank">表示</a>',
            esc_html($trivia_title),
            $action,
            esc_html($post_title),
            esc_html(mb_substr($meta_description, 0, 50)),
            esc_url($edit_link),
            esc_url($view_link)
        )
    );
}

// =============================================================================
// [reader_library] ショートコード - オーディオブックライブラリ専用検索ページ
// =============================================================================
function reader_library_shortcode_handler( $atts ) {
    $library = uir_get_site_structure();
    $library_json = json_encode($library, JSON_UNESCAPED_UNICODE);
    $uid = 'reader-library-' . uniqid();

    ob_start();
    ?>
    <div id="<?php echo esc_attr($uid); ?>" class="reader-library-app" style="width:100%; min-height:500px;">
        読み込み中...
    </div>

    <style>
        .reader-library-app { font-family: 'Noto Serif JP', serif; }
        .reader-library-app ::-webkit-scrollbar { width: 8px; height: 8px; }
        .reader-library-app ::-webkit-scrollbar-track { background: #f1f1f1; }
        .reader-library-app ::-webkit-scrollbar-thumb { background: #d6d3d1; border-radius: 4px; }
        .reader-library-grid h3 {
            font-size: 11px !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            line-height: 1.3 !important;
        }
    </style>

    <script type="text/babel">
    (function() {
        const { useState, useMemo } = React;
        const library = <?php echo $library_json ?: '[]'; ?>;

        // --- Icons ---
        const Icons = {
            Search: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
            BookOpen: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
            X: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
            User: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
            Calendar: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
            Grid: (p) => <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
        };

        const App = () => {
            const [searchTerm, setSearchTerm] = useState('');
            const [sortMode, setSortMode] = useState('author'); // 'author', 'date', 'title'
            
            const filteredLibrary = useMemo(() => {
                if (!searchTerm.trim()) return library;
                const term = searchTerm.toLowerCase();
                return library.filter(book => 
                    book.title?.toLowerCase().includes(term) ||
                    book.author?.toLowerCase().includes(term) ||
                    book.genre?.toLowerCase().includes(term) ||
                    book.series?.toLowerCase().includes(term)
                );
            }, [searchTerm]);

            // 作家ごとにグループ化（作家名でソート）
            const groupedByAuthor = useMemo(() => {
                const groups = {};
                filteredLibrary.forEach(book => {
                    const author = book.author || '編集部';
                    if (!groups[author]) groups[author] = [];
                    groups[author].push(book);
                });
                // 作家名をソートし、各グループ内は日付順
                const sortedAuthors = Object.keys(groups).sort((a, b) => a.localeCompare(b, 'ja'));
                return sortedAuthors.map(author => ({
                    author,
                    books: groups[author].sort((a, b) => (b.date || '').localeCompare(a.date || ''))
                }));
            }, [filteredLibrary]);

            // 日付順（フラット表示）
            const sortedByDate = useMemo(() => {
                return [...filteredLibrary].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
            }, [filteredLibrary]);

            // タイトル順（フラット表示）
            const sortedByTitle = useMemo(() => {
                return [...filteredLibrary].sort((a, b) => (a.title || '').localeCompare(b.title || '', 'ja'));
            }, [filteredLibrary]);

            return (
                <div className="bg-stone-50 rounded-xl shadow-lg overflow-hidden">
                    {/* Header with Search */}
                    <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 sm:px-6 py-4">
                        <div className="flex items-center gap-3 mb-4">
                            <Icons.BookOpen width="24" className="text-white/90"/>
                            <h2 className="text-lg sm:text-xl font-bold text-white" style={{margin: 0, padding: 0, border: 'none'}}>
                                丸竹書房ライブラリ
                            </h2>
                        </div>
                        <div className="relative">
                            <Icons.Search width="18" className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"/>
                            <input
                                type="text"
                                placeholder="タイトル・著者・ジャンル・シリーズで検索..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-10 pr-10 py-3 rounded-lg border-0 bg-white text-stone-800 placeholder-stone-400 focus:ring-2 focus:ring-indigo-300 outline-none text-sm"
                            />
                            {searchTerm && (
                                <button 
                                    onClick={() => setSearchTerm('')}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                                >
                                    <Icons.X width="18"/>
                                </button>
                            )}
                        </div>
                        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                            <div className="text-indigo-100 text-sm">
                                {searchTerm ? (
                                    <span>{filteredLibrary.length}件 / {library.length}件</span>
                                ) : (
                                    <span>全{library.length}作品 / {groupedByAuthor.length}名の作家</span>
                                )}
                            </div>
                            {/* Sort Buttons */}
                            <div className="flex gap-1">
                                <button
                                    onClick={() => setSortMode('author')}
                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                                        sortMode === 'author' 
                                            ? 'bg-white text-indigo-700' 
                                            : 'bg-indigo-500/30 text-white hover:bg-indigo-500/50'
                                    }`}
                                >
                                    <Icons.User width="12"/>
                                    <span>作家別</span>
                                </button>
                                <button
                                    onClick={() => setSortMode('date')}
                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                                        sortMode === 'date' 
                                            ? 'bg-white text-indigo-700' 
                                            : 'bg-indigo-500/30 text-white hover:bg-indigo-500/50'
                                    }`}
                                >
                                    <Icons.Calendar width="12"/>
                                    <span>新着順</span>
                                </button>
                                <button
                                    onClick={() => setSortMode('title')}
                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                                        sortMode === 'title' 
                                            ? 'bg-white text-indigo-700' 
                                            : 'bg-indigo-500/30 text-white hover:bg-indigo-500/50'
                                    }`}
                                >
                                    <Icons.Grid width="12"/>
                                    <span>タイトル順</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Library Content */}
                    <div className="p-4 sm:p-6 max-h-[70vh] overflow-y-auto">
                        {filteredLibrary.length > 0 ? (
                            sortMode === 'author' ? (
                                /* 作家別グループ表示 */
                                <div className="space-y-6">
                                    {groupedByAuthor.map(group => (
                                        <div key={group.author} className="border-b border-stone-200 pb-4 last:border-b-0">
                                            <div className="flex items-center gap-2 mb-3">
                                                <Icons.User width="16" className="text-indigo-500"/>
                                                <h3 className="font-bold text-stone-700 text-sm" style={{margin: 0, padding: 0, border: 'none'}}>
                                                    {group.author}
                                                </h3>
                                                <span className="text-xs text-stone-400">({group.books.length}作品)</span>
                                            </div>
                                            <div className="reader-library-grid grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3 sm:gap-4">
                                                {group.books.map(book => (
                                                    <a key={book.id} href={book.url} className="group block">
                                                        <div className="aspect-video bg-stone-200 rounded shadow-sm group-hover:shadow-md transition-all duration-300 overflow-hidden relative">
                                                            {book.thumbnail ? (
                                                                <img src={book.thumbnail} alt={book.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                            ) : (
                                                                <div className="w-full h-full flex items-center justify-center bg-stone-100 p-2">
                                                                    <div className="text-stone-500 font-bold text-[10px] text-center leading-tight line-clamp-2">
                                                                        {book.title}
                                                                    </div>
                                                                </div>
                                                            )}
                                                            <div className="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                                                        </div>
                                                        <div className="mt-1.5 px-0.5">
                                                            <h3 className="font-bold text-stone-700 text-[10px] sm:text-[11px] leading-tight line-clamp-2 group-hover:text-indigo-600 transition-colors">
                                                                {book.title}
                                                            </h3>
                                                        </div>
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                /* フラット表示（日付順・タイトル順） */
                                <div className="reader-library-grid grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3 sm:gap-4">
                                    {(sortMode === 'date' ? sortedByDate : sortedByTitle).map(book => (
                                        <a key={book.id} href={book.url} className="group block">
                                            <div className="aspect-video bg-stone-200 rounded shadow-sm group-hover:shadow-md transition-all duration-300 overflow-hidden relative">
                                                {book.thumbnail ? (
                                                    <img src={book.thumbnail} alt={book.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center bg-stone-100 p-2">
                                                        <div className="text-stone-500 font-bold text-[10px] text-center leading-tight line-clamp-2">
                                                            {book.title}
                                                        </div>
                                                    </div>
                                                )}
                                                <div className="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                                            </div>
                                            <div className="mt-1.5 px-0.5">
                                                <h3 className="font-bold text-stone-700 text-[10px] sm:text-[11px] leading-tight line-clamp-2 group-hover:text-indigo-600 transition-colors">
                                                    {book.title}
                                                </h3>
                                                <div className="text-[9px] text-stone-400 mt-0.5 truncate">
                                                    {book.author}
                                                </div>
                                            </div>
                                        </a>
                                    ))}
                                </div>
                            )
                        ) : (
                            <div className="text-center py-12 text-stone-500">
                                <Icons.Search width="48" className="mx-auto mb-4 opacity-30"/>
                                <p className="text-lg font-bold mb-1">見つかりませんでした</p>
                                <p className="text-sm">別のキーワードで検索してみてください</p>
                            </div>
                        )}
                    </div>
                </div>
            );
        };
        
        const root = ReactDOM.createRoot(document.getElementById('<?php echo $uid; ?>'));
        root.render(<App />);
    })();
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode( 'reader_library', 'reader_library_shortcode_handler' );


// =============================================================================
// 管理画面: JSONファイルアップロード機能 (上書き機能強化版)
// =============================================================================

/**
 * 管理メニューに「読書アプリ投稿」を追加
 */
function uir_admin_menu() {
    add_menu_page(
        '読書アプリ投稿',           // ページタイトル
        '読書アプリ投稿',           // メニュータイトル
        'edit_posts',               // 権限
        'uir-json-uploader',        // スラッグ
        'uir_json_uploader_page',   // コールバック
        'dashicons-book-alt',       // アイコン
        25                          // 位置
    );

    // 雑学アプリ投稿（JSONアップロード）
    add_menu_page(
        '雑学アプリ投稿',
        '雑学アプリ投稿',
        'edit_posts',
        'tao-trivia-uploader',
        'tao_trivia_uploader_page',
        'dashicons-lightbulb',
        26
    );

    // 雑学データ編集（メニューには表示しない）
    add_submenu_page(
        null,
        '雑学データ編集',
        '雑学データ編集',
        'edit_posts',
        'tao-trivia-editor',
        'tao_trivia_editor_page'
    );
    // データ編集用ページ（メニューには表示しない）
    add_submenu_page(
        null,
        'ブックデータ編集',
        'ブックデータ編集',
        'edit_posts',
        'uir-book-editor',
        'uir_book_editor_page'
    );
}
add_action('admin_menu', 'uir_admin_menu');

// =============================================================================
// 雑学アプリ: ショートコード/テンプレ用ユーティリティ
// =============================================================================

function tao_trivia_default_app_data() {
    return array(
        'title' => '江戸の時刻制度（不定時法）',
        'description' => '江戸時代は、日の出と日の入りを基準に昼と夜をそれぞれ6等分する「不定時法」が使われていました。季節によって一刻（いっとき）の長さが変わります。',
        'hours' => array(
            array('name' => '明け六つ', 'zodiac' => '卯', 'modern_approx' => '06:00 (Sunrise)', 'bell_count' => 6, 'description' => '日の出の時刻。城門が開き、一日が始まります。「六つ」の鐘が鳴ります。'),
            array('name' => '朝五つ', 'zodiac' => '辰', 'modern_approx' => '08:00', 'bell_count' => 5, 'description' => '朝食の時間帯。武士が出仕する時間でもあります。'),
            array('name' => '昼四つ', 'zodiac' => '巳', 'modern_approx' => '10:00', 'bell_count' => 4, 'description' => '仕事が本格化する時間。'),
            array('name' => '昼九つ', 'zodiac' => '午', 'modern_approx' => '12:00 (Noon)', 'bell_count' => 9, 'description' => '正午。太陽が最も高い位置にあります。「九つ」の鐘が鳴ります。'),
            array('name' => '昼八つ', 'zodiac' => '未', 'modern_approx' => '14:00', 'bell_count' => 8, 'description' => '「おやつ」の語源。午後の間食の時間。'),
            array('name' => '夕七つ', 'zodiac' => '申', 'modern_approx' => '16:00', 'bell_count' => 7, 'description' => '仕事終わりの時間。銭湯が開く頃。'),
            array('name' => '暮れ六つ', 'zodiac' => '酉', 'modern_approx' => '18:00 (Sunset)', 'bell_count' => 6, 'description' => '日の入り。城門が閉まり、夜が始まります。'),
            array('name' => '夜五つ', 'zodiac' => '戌', 'modern_approx' => '20:00', 'bell_count' => 5, 'description' => '夜のくつろぎの時間。'),
            array('name' => '夜四つ', 'zodiac' => '亥', 'modern_approx' => '22:00', 'bell_count' => 4, 'description' => '就寝の時間。夜回りが始まります。'),
            array('name' => '夜九つ', 'zodiac' => '子', 'modern_approx' => '00:00 (Midnight)', 'bell_count' => 9, 'description' => '真夜中。草木も眠る丑三つ時の前。'),
            array('name' => '夜八つ', 'zodiac' => '丑', 'modern_approx' => '02:00', 'bell_count' => 8, 'description' => '「丑三つ時」はこの刻の真ん中（2:00〜2:30頃）。幽霊が出ると言われる。'),
            array('name' => '暁七つ', 'zodiac' => '寅', 'modern_approx' => '04:00', 'bell_count' => 7, 'description' => '夜明け前。市場などが動き出す準備の時間。'),
        ),
    );
}

function tao_trivia_load_app_data_from_file_url( $file_url ) {
    $file_url = trim((string)$file_url);
    if ($file_url === '') return tao_trivia_default_app_data();

    $upload_dir = wp_upload_dir();
    $baseurl = $upload_dir['baseurl'] ?? '';
    $basedir = $upload_dir['basedir'] ?? '';

    $json_string = '';

    // uploads配下ならローカルパスに変換して読む（高速・安定）
    if ($baseurl && $basedir && strpos($file_url, $baseurl) === 0) {
        $relative = ltrim(substr($file_url, strlen($baseurl)), '/');
        // URLデコード（日本語ファイル名対応）
        $relative = rawurldecode($relative);
        $local_path = rtrim($basedir, '/') . '/' . $relative;
        if (file_exists($local_path)) {
            $json_string = file_get_contents($local_path);
        }
    }

    // フォールバック: HTTPで取得
    if ($json_string === '' || $json_string === false) {
        $resp = wp_remote_get($file_url, array('timeout' => 10));
        if (!is_wp_error($resp)) {
            $code = wp_remote_retrieve_response_code($resp);
            $body = wp_remote_retrieve_body($resp);
            if ($code >= 200 && $code < 300 && is_string($body) && $body !== '') {
                $json_string = $body;
            }
        }
    }

    if (!is_string($json_string) || trim($json_string) === '') {
        // エラー: データが読み込めなかった
        return array(
            'title' => 'エラー: データを読み込めませんでした',
            'description' => 'JSONファイルの読み込みに失敗しました。URLまたはファイルパスを確認してください。指定URL: ' . esc_html($file_url),
            'hours' => array(),
            '_error' => true,
        );
    }

    $data = json_decode($json_string, true);
    if (!is_array($data) || json_last_error() !== JSON_ERROR_NONE) {
        // エラー: JSONパース失敗
        return array(
            'title' => 'エラー: JSONの解析に失敗しました',
            'description' => 'JSONファイルの形式が正しくありません。エラー: ' . json_last_error_msg(),
            'hours' => array(),
            '_error' => true,
        );
    }

    // 最低限の形を整える
    if (empty($data['title'])) $data['title'] = '雑学';
    if (empty($data['description'])) $data['description'] = '';
    if (empty($data['hours']) || !is_array($data['hours'])) $data['hours'] = array();

    return $data;
}

/**
 * JSON アップロードページの表示
 */
function uir_json_uploader_page() {
    // 投稿処理
    $message = '';
    $message_type = '';
    
    if (isset($_POST['uir_upload_json']) && wp_verify_nonce($_POST['uir_nonce'], 'uir_json_upload')) {
        $result = uir_process_json_upload();
        $message = $result['message'];
        $message_type = $result['type'];
    }
    
    // reading_application カテゴリを取得または作成
    $category = get_category_by_slug('reading_application');
    if (!$category) {
        $cat_id = wp_create_category('reading_application');
        $category = get_category($cat_id);
    }
    
    ?>
    <div class="wrap">
        <h1><span class="dashicons dashicons-book-alt" style="font-size:30px;margin-right:10px;"></span>読書アプリ用 JSON アップロード</h1>
        
        <?php if ($message): ?>
            <div class="notice notice-<?php echo esc_attr($message_type); ?> is-dismissible">
                <p><?php echo wp_kses_post($message); ?></p>
            </div>
        <?php endif; ?>
        
        <div class="card" style="max-width:800px;margin-top:20px;">
            <h2>JSONファイルをアップロード</h2>
            <p>Python変換ツールで生成した <code>.json</code> ファイルをアップロードして、読書アプリ用の投稿を自動作成します。</p>
            
            <form method="post" enctype="multipart/form-data" style="margin-top:20px;">
                <?php wp_nonce_field('uir_json_upload', 'uir_nonce'); ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row"><label for="json_file">JSONファイル</label></th>
                        <td>
                            <input type="file" name="json_file" id="json_file" accept=".json" required style="margin-bottom:10px;">
                            <p class="description">
                                <code>[immersive_reader]...[\immersive_reader]</code> 形式のJSONファイル<br>
                                または、ショートコードなしの純粋なJSONファイル
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="post_status">投稿ステータス</label></th>
                        <td>
                            <select name="post_status" id="post_status">
                                <option value="draft">下書き</option>
                                <option value="publish">公開</option>
                                <option value="private">非公開</option>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row"><label for="author_tag">著者タグ</label></th>
                        <td>
                            <input type="text" name="author_tag" id="author_tag" class="regular-text" placeholder="自動取得（JSONのauthorから）">
                            <p class="description">空欄の場合、JSONの author フィールドをタグとして設定します</p>
                        </td>
                    </tr>
                </table>
                
                <p class="submit">
                    <input type="submit" name="uir_upload_json" class="button button-primary button-large" value="アップロードして投稿作成">
                </p>
            </form>
        </div>
        
        <div class="card" style="max-width:800px;margin-top:20px;">
            <h2>対応JSONフォーマット</h2>
            <p>以下の形式のJSONファイルに対応しています：</p>
            <pre style="background:#f5f5f5;padding:15px;border-radius:5px;overflow-x:auto;font-size:12px;">{
  "title": "作品タイトル",
  "author": "著者名",
  "genre": "ジャンル",
  "synopsis": "あらすじ",
  "authorProfile": { "name": "著者名", "desc": "プロフィール" },
  "characters": [
    { "name": "名前", "role": "役割", "desc": "説明" }
  ],
  "chapters": [
    { "title": "第一章", "content": "本文..." }
  ]
}</pre>
            <p><strong>注意:</strong> <code>[immersive_reader]...[/immersive_reader]</code> で囲まれたファイルも自動的に処理されます。</p>
        </div>
        
        <div class="card" style="max-width:800px;margin-top:20px;">
            <h2>最近の読書アプリ投稿</h2>
            <?php
            $recent_posts = get_posts(array(
                'post_type' => 'post',
                'category_name' => 'reading_application',
                // すべての読書データを表示
                'numberposts' => -1,
                // 管理画面では公開/下書き/非公開も含めて一覧したい
                'post_status' => array('publish', 'draft', 'private'),
                'orderby' => 'date',
                'order' => 'DESC'
            ));
            
            if ($recent_posts): ?>
                <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                    <input
                        type="text"
                        id="uir-post-search"
                        class="regular-text"
                        placeholder="タイトル・著者タグで検索..."
                        style="max-width:420px;"
                    />
                    <span id="uir-post-search-count" style="color:#666;font-size:12px;">全<?php echo esc_html( count($recent_posts) ); ?>件</span>
                </div>
                <table class="widefat striped" style="margin-top:10px;">
                    <thead>
                        <tr>
                            <th>タイトル</th>
                            <th>著者タグ</th>
                            <th>日時</th>
                            <th>ステータス</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($recent_posts as $post): 
                            $tags = get_the_tags($post->ID);
                            $author_tag = $tags ? $tags[0]->name : '-';
                        ?>
                            <tr>
                                <td><strong><?php echo esc_html($post->post_title); ?></strong></td>
                                <td><?php echo esc_html($author_tag); ?></td>
                                <td><?php echo get_the_date('Y/m/d H:i', $post); ?></td>
                                <td>
                                    <?php 
                                    $status_labels = array('publish' => '公開', 'draft' => '下書き', 'private' => '非公開');
                                    echo esc_html($status_labels[$post->post_status] ?? $post->post_status);
                                    ?>
                                </td>
                                <td>
                                    <a href="<?php echo admin_url('admin.php?page=uir-book-editor&post_id=' . $post->ID); ?>" class="button button-small button-primary">データ編集</a>
                                    <a href="<?php echo get_edit_post_link($post->ID); ?>" class="button button-small">WP編集</a>
                                    <a href="<?php echo get_permalink($post->ID); ?>" class="button button-small" target="_blank">表示</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                <script>
                (function() {
                    const input = document.getElementById('uir-post-search');
                    const table = input ? input.closest('.card')?.querySelector('table') : null;
                    const countEl = document.getElementById('uir-post-search-count');
                    if (!input || !table) return;
                    const rows = Array.from(table.querySelectorAll('tbody tr'));

                    const update = () => {
                        const term = (input.value || '').trim().toLowerCase();
                        let visible = 0;
                        rows.forEach(tr => {
                            const text = (tr.innerText || '').toLowerCase();
                            const show = !term || text.includes(term);
                            tr.style.display = show ? '' : 'none';
                            if (show) visible += 1;
                        });
                        if (countEl) {
                            countEl.textContent = term ? `${visible}件 / ${rows.length}件` : `全${rows.length}件`;
                        }
                    };

                    input.addEventListener('input', update);
                    update();
                })();
                </script>
            <?php else: ?>
                <p>まだ読書アプリ用の投稿がありません。</p>
            <?php endif; ?>
        </div>
    </div>
    <?php
}

/**
 * ブックデータ編集ページ
 */
function uir_book_editor_page() {
    $post_id = isset($_GET['post_id']) ? intval($_GET['post_id']) : 0;
    $post = get_post($post_id);
    
    if (!$post) {
        echo '<div class="wrap"><div class="notice notice-error"><p>投稿が見つかりません。</p></div></div>';
        return;
    }

    $message = '';
    $message_type = '';

    // データ保存処理
    if (isset($_POST['uir_save_book_data']) && check_admin_referer('uir_save_book_data_' . $post_id)) {
        // POSTデータを整形
        $new_data = array(
            'title' => sanitize_text_field($_POST['book_title']),
            'author' => sanitize_text_field($_POST['book_author']),
            'genre' => sanitize_text_field($_POST['book_genre']),
            'synopsis' => sanitize_textarea_field($_POST['book_synopsis']),
            'authorProfile' => array(
                'name' => sanitize_text_field($_POST['author_profile_name']),
                'desc' => sanitize_textarea_field($_POST['author_profile_desc']),
            ),
            'characters' => array(),
            'glossary' => array(),
            'chapters' => array(),
        );

        // 登場人物
        if (isset($_POST['characters']) && is_array($_POST['characters'])) {
            foreach ($_POST['characters'] as $char) {
                if (!empty($char['name'])) {
                    $new_data['characters'][] = array(
                        'name' => sanitize_text_field($char['name']),
                        'role' => sanitize_text_field($char['role']),
                        'desc' => sanitize_textarea_field($char['desc']),
                    );
                }
            }
        }

        // 用語集
        if (isset($_POST['glossary']) && is_array($_POST['glossary'])) {
            foreach ($_POST['glossary'] as $term) {
                if (!empty($term['term'])) {
                    $new_data['glossary'][] = array(
                        'term' => sanitize_text_field($term['term']),
                        'reading' => sanitize_text_field($term['reading']),
                        'desc' => sanitize_textarea_field($term['desc']),
                    );
                }
            }
        }

        // チャプター
        if (isset($_POST['chapters']) && is_array($_POST['chapters'])) {
            foreach ($_POST['chapters'] as $chap) {
                if (!empty($chap['title'])) {
                    $new_data['chapters'][] = array(
                        'title' => sanitize_text_field($chap['title']),
                        'content' => $_POST['allow_html'] ? wp_kses_post($chap['content']) : sanitize_textarea_field($chap['content']),
                    );
                }
            }
        }

        // JSONエンコード
        $json_string = json_encode($new_data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);

        // 保存先を特定（ファイル or インライン）
        $content = $post->post_content;
        $saved = false;

        if (preg_match('/\[immersive_reader\s+file="([^"]+)"\]/', $content, $matches)) {
            // ファイル保存
            $file_url = $matches[1];
            $upload_dir = wp_upload_dir();
            $file_path = str_replace($upload_dir['baseurl'], $upload_dir['basedir'], $file_url);
            
            if (file_put_contents($file_path, $json_string) !== false) {
                $saved = true;
            }
        } else {
            // インライン保存（ショートコードの中身を置換）
            $new_content = preg_replace(
                '/(\[immersive_reader\])(.*?)(\[\/immersive_reader\])/s',
                '$1' . $json_string . '$3',
                $content
            );
            
            // 投稿を更新
            $updated_post = array(
                'ID' => $post_id,
                'post_content' => $new_content
            );
            if (wp_update_post($updated_post)) {
                $saved = true;
            }
        }

        if ($saved) {
            // メタデータも更新
            update_post_meta($post_id, '_uir_work_title', $new_data['title']);
            update_post_meta($post_id, '_uir_author', $new_data['author']);
            
            $message = 'データを保存しました。';
            $message_type = 'success';
        } else {
            $message = '保存に失敗しました。';
            $message_type = 'error';
        }
    }

    // データ読み込み
    $content = $post->post_content;
    $data = array();
    $source_type = 'unknown';

    if (preg_match('/\[immersive_reader\s+file="([^"]+)"\]/', $content, $matches)) {
        $source_type = 'file';
        $file_url = $matches[1];
        $upload_dir = wp_upload_dir();
        $file_path = str_replace($upload_dir['baseurl'], $upload_dir['basedir'], $file_url);
        if (file_exists($file_path)) {
            $data = json_decode(file_get_contents($file_path), true);
        }
    } elseif (preg_match('/\[immersive_reader\](.*?)\[\/immersive_reader\]/s', $content, $matches)) {
        $source_type = 'inline';
        $json_str = $matches[1];
        $json_str = strip_tags($json_str);
        $json_str = html_entity_decode($json_str, ENT_QUOTES, 'UTF-8');
        $data = json_decode($json_str, true);
    }

    if (!$data) {
        $data = array();
        if (!$message) {
            $message = 'JSONデータの読み込みに失敗しました。';
            $message_type = 'warning';
        }
    }

    // JSON反映処理（保存はしない）
    if (isset($_POST['uir_load_json']) && check_admin_referer('uir_save_book_data_' . $post_id)) {
        $raw_json = wp_unslash($_POST['raw_json']);
        $decoded = json_decode($raw_json, true);
        if ($decoded) {
            $data = array_merge($data, $decoded);
            $message = 'JSONデータをフォームに反映しました。（保存するには「変更を保存」を押してください）';
            $message_type = 'info';
        } else {
            $message = 'JSONの形式が正しくありません: ' . json_last_error_msg();
            $message_type = 'error';
        }
    }

    // メタデータ注入処理
    if (isset($_POST['uir_inject_metadata']) && check_admin_referer('uir_save_book_data_' . $post_id)) {
        $meta_json = wp_unslash($_POST['meta_json_input']);
        $meta_decoded = json_decode($meta_json, true);
        if ($meta_decoded) {
            $data = array_merge($data, $meta_decoded);
            $message = 'メタデータを注入しました。（保存するには「変更を保存」を押してください）';
            $message_type = 'success';
        } else {
            $message = 'メタデータJSONの形式が正しくありません。';
            $message_type = 'error';
        }
    }

    // デフォルト値
    $data = array_merge(array(
        'title' => '', 'author' => '', 'genre' => '', 'synopsis' => '',
        'authorProfile' => array('name' => '', 'desc' => ''),
        'characters' => array(),
        'glossary' => array(),
        'chapters' => array()
    ), $data);

    ?>
    <div class="wrap">
        <h1>ブックデータ編集: <?php echo esc_html($post->post_title); ?></h1>
        
        <?php if ($message): ?>
            <div class="notice notice-<?php echo esc_attr($message_type); ?> is-dismissible">
                <p><?php echo esc_html($message); ?></p>
            </div>
        <?php endif; ?>

        <form method="post">
            <?php wp_nonce_field('uir_save_book_data_' . $post_id); ?>
            <input type="hidden" name="allow_html" value="0">

            <div id="poststuff">
                <div id="post-body" class="metabox-holder columns-2">
                    <div id="post-body-content">
                        
                        <!-- 基本情報 -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">基本情報</h2></div>
                            <div class="inside">
                                <table class="form-table">
                                    <tr>
                                        <th><label>タイトル</label></th>
                                        <td><input type="text" name="book_title" value="<?php echo esc_attr($data['title']); ?>" class="large-text"></td>
                                    </tr>
                                    <tr>
                                        <th><label>著者</label></th>
                                        <td><input type="text" name="book_author" value="<?php echo esc_attr($data['author']); ?>" class="regular-text"></td>
                                    </tr>
                                    <tr>
                                        <th><label>ジャンル</label></th>
                                        <td><input type="text" name="book_genre" value="<?php echo esc_attr($data['genre']); ?>" class="regular-text"></td>
                                    </tr>
                                    <tr>
                                        <th><label>あらすじ</label></th>
                                        <td><textarea name="book_synopsis" rows="5" class="large-text"><?php echo esc_textarea($data['synopsis']); ?></textarea></td>
                                    </tr>
                                </table>
                            </div>
                        </div>

                        <!-- チャプター -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">チャプター (本文)</h2></div>
                            <div class="inside">
                                <div id="chapters-container">
                                    <?php foreach ($data['chapters'] as $i => $chap): ?>
                                        <div class="chapter-item" style="border:1px solid #ddd; padding:15px; margin-bottom:15px; background:#f9f9f9;">
                                            <p>
                                                <label>章タイトル:</label>
                                                <input type="text" name="chapters[<?php echo $i; ?>][title]" value="<?php echo esc_attr($chap['title']); ?>" class="large-text">
                                            </p>
                                            <p>
                                                <label>本文:</label>
                                                <textarea name="chapters[<?php echo $i; ?>][content]" rows="10" class="large-text"><?php echo esc_textarea($chap['content']); ?></textarea>
                                            </p>
                                            <button type="button" class="button button-link-delete" onclick="removeRow(this)">この章を削除</button>
                                        </div>
                                    <?php endforeach; ?>
                                </div>
                                <button type="button" class="button" onclick="addChapter()">＋ 章を追加</button>
                            </div>
                        </div>

                        <!-- JSON生データ編集 -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">JSON生データ編集</h2></div>
                            <div class="inside">
                                <p>JSONを直接編集して「JSONをフォームに反映」を押すと、上の各項目に内容が反映されます（保存はされません）。<br>
                                逆に、上のフォームを変更して「変更を保存」を押すと、このJSONも更新されて保存されます。</p>
                                <textarea name="raw_json" id="raw_json" rows="15" class="large-text code" style="font-family:monospace; background:#f0f0f1;"><?php echo esc_textarea(json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)); ?></textarea>
                                <div style="margin-top:10px;">
                                    <input type="submit" name="uir_load_json" class="button" value="JSONをフォームに反映">
                                </div>
                            </div>
                        </div>

                        <!-- SEO / メタデータ一括注入 -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">SEO / メタデータ一括注入</h2></div>
                            <div class="inside">
                                <p>ここにメタデータ（genre, keywords, themes, synopsisなど）を含むJSONを貼り付けて「メタデータを注入」を押すと、既存のデータにマージされます。<br>
                                ※既存のキーと同じものがある場合は上書きされます。</p>
                                <textarea name="meta_json_input" rows="10" class="large-text code" style="font-family:monospace; background:#f9f9f9;" placeholder='{
  "genre": "時代小説",
  "keywords": ["キーワード1", "キーワード2"],
  "themes": ["テーマ1", "テーマ2"]
}'></textarea>
                                <div style="margin-top:10px;">
                                    <input type="submit" name="uir_inject_metadata" class="button" value="メタデータを注入">
                                </div>
                            </div>
                        </div>

                    </div>

                    <div id="postbox-container-1" class="postbox-container">
                        
                        <!-- 保存アクション -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">公開</h2></div>
                            <div class="inside">
                                <p>データソース: <strong><?php echo $source_type === 'file' ? 'JSONファイル' : '投稿内埋め込み'; ?></strong></p>
                                <div id="major-publishing-actions">
                                    <div id="publishing-action">
                                        <input type="submit" name="uir_save_book_data" class="button button-primary button-large" value="変更を保存">
                                    </div>
                                    <div class="clear"></div>
                                </div>
                                <p style="margin-top:10px;"><a href="<?php echo admin_url('admin.php?page=uir-json-uploader'); ?>">一覧に戻る</a></p>
                            </div>
                        </div>

                        <!-- 作者プロフィール -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">作者プロフィール</h2></div>
                            <div class="inside">
                                <p>
                                    <label>名前:</label>
                                    <input type="text" name="author_profile_name" value="<?php echo esc_attr($data['authorProfile']['name'] ?? $data['author']); ?>" class="widefat">
                                </p>
                                <p>
                                    <label>紹介文:</label>
                                    <textarea name="author_profile_desc" rows="4" class="widefat"><?php echo esc_textarea($data['authorProfile']['desc'] ?? ''); ?></textarea>
                                </p>
                            </div>
                        </div>

                        <!-- 登場人物 -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">登場人物</h2></div>
                            <div class="inside">
                                <div id="characters-container">
                                    <?php 
                                    $characters = is_array($data['characters']) ? $data['characters'] : array();
                                    foreach ($characters as $i => $char): 
                                        if (!is_array($char)) continue; // 壊れたデータをスキップ
                                    ?>
                                        <div class="item-row" style="border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:10px;">
                                            <input type="text" name="characters[<?php echo $i; ?>][name]" value="<?php echo esc_attr($char['name'] ?? ''); ?>" placeholder="名前" class="widefat" style="margin-bottom:5px;">
                                            <input type="text" name="characters[<?php echo $i; ?>][role]" value="<?php echo esc_attr($char['role'] ?? ''); ?>" placeholder="役割・読み" class="widefat" style="margin-bottom:5px;">
                                            <textarea name="characters[<?php echo $i; ?>][desc]" placeholder="説明" rows="2" class="widefat"><?php echo esc_textarea($char['desc'] ?? $char['description'] ?? ''); ?></textarea>
                                            <button type="button" class="button button-link-delete" onclick="removeRow(this)">削除</button>
                                        </div>
                                    <?php endforeach; ?>
                                </div>
                                <button type="button" class="button" onclick="addCharacter()">＋ 追加</button>
                            </div>
                        </div>

                        <!-- 用語集 -->
                        <div class="postbox">
                            <div class="postbox-header"><h2 class="hndle">用語集</h2></div>
                            <div class="inside">
                                <div id="glossary-container">
                                    <?php 
                                    $glossary = is_array($data['glossary']) ? $data['glossary'] : array();
                                    foreach ($glossary as $i => $item): 
                                        if (!is_array($item)) continue; // 壊れたデータをスキップ
                                    ?>
                                        <div class="item-row" style="border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:10px;">
                                            <input type="text" name="glossary[<?php echo $i; ?>][term]" value="<?php echo esc_attr($item['term'] ?? ''); ?>" placeholder="用語" class="widefat" style="margin-bottom:5px;">
                                            <input type="text" name="glossary[<?php echo $i; ?>][reading]" value="<?php echo esc_attr($item['reading'] ?? ''); ?>" placeholder="読み" class="widefat" style="margin-bottom:5px;">
                                            <textarea name="glossary[<?php echo $i; ?>][desc]" placeholder="説明" rows="2" class="widefat"><?php echo esc_textarea($item['desc'] ?? $item['description'] ?? ''); ?></textarea>
                                            <button type="button" class="button button-link-delete" onclick="removeRow(this)">削除</button>
                                        </div>
                                    <?php endforeach; ?>
                                </div>
                                <button type="button" class="button" onclick="addGlossary()">＋ 追加</button>

                                <?php
                                // 主要雑学（登録済み）をリンク表示し、用語集へ追加できるようにする
                                $trivia_posts = get_posts(array(
                                    'post_type' => 'post',
                                    'category_name' => 'trivia_application',
                                    'numberposts' => 30,
                                    'post_status' => array('publish', 'draft', 'private'),
                                    'orderby' => 'date',
                                    'order' => 'DESC',
                                ));
                                ?>

                                <div style="margin-top:14px; padding-top:12px; border-top:1px solid #eee;">
                                    <div style="font-weight:600; margin-bottom:6px;">主要雑学（リンク）</div>
                                    <div style="color:#666; font-size:12px; margin-bottom:10px;">登録済みの雑学から、用語集にワンクリックで追加できます。</div>

                                    <?php if (!empty($trivia_posts)): ?>
                                        <table class="widefat striped" style="max-width:100%;">
                                            <thead>
                                                <tr>
                                                    <th>雑学</th>
                                                    <th style="width:260px;">操作</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <?php foreach ($trivia_posts as $tp):
                                                    $term = (string) get_post_meta($tp->ID, '_tao_trivia_title', true);
                                                    if ($term === '') {
                                                        $term = (string) $tp->post_title;
                                                        $term = preg_replace('/^雑学\s*/u', '', $term);
                                                        $term = preg_replace('/\s*発行元.*$/u', '', $term);
                                                    }
                                                    $t_desc = (string) get_post_meta($tp->ID, '_tao_trivia_meta_description', true);
                                                    $t_url = get_permalink($tp->ID);
                                                ?>
                                                    <tr>
                                                        <td>
                                                            <strong><?php echo esc_html($term); ?></strong>
                                                            <div style="color:#666; font-size:12px; margin-top:2px;">
                                                                <?php echo esc_html(mb_substr($t_desc, 0, 80)); ?>
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <a class="button button-small" href="<?php echo esc_url($t_url); ?>" target="_blank" rel="noopener noreferrer">開く</a>
                                                            <button
                                                                type="button"
                                                                class="button button-small button-primary"
                                                                onclick="addGlossaryFromTrivia(this)"
                                                                data-term="<?php echo esc_attr($term); ?>"
                                                                data-desc="<?php echo esc_attr($t_desc); ?>"
                                                                data-url="<?php echo esc_url($t_url); ?>"
                                                            >用語集に追加</button>
                                                        </td>
                                                    </tr>
                                                <?php endforeach; ?>
                                            </tbody>
                                        </table>
                                    <?php else: ?>
                                        <div style="color:#666; font-size:12px;">まだ雑学アプリ投稿がありません。</div>
                                    <?php endif; ?>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </form>
    </div>

    <script>
    function removeRow(btn) {
        if(confirm('本当に削除しますか？')) {
            btn.closest('div').remove();
        }
    }

    function addChapter() {
        const container = document.getElementById('chapters-container');
        const index = new Date().getTime(); // Unique ID
        const html = `
            <div class="chapter-item" style="border:1px solid #ddd; padding:15px; margin-bottom:15px; background:#f9f9f9;">
                <p>
                    <label>章タイトル:</label>
                    <input type="text" name="chapters[${index}][title]" value="" class="large-text">
                </p>
                <p>
                    <label>本文:</label>
                    <textarea name="chapters[${index}][content]" rows="10" class="large-text"></textarea>
                </p>
                <button type="button" class="button button-link-delete" onclick="removeRow(this)">この章を削除</button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    }

    function addCharacter() {
        const container = document.getElementById('characters-container');
        const index = new Date().getTime();
        const html = `
            <div class="item-row" style="border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:10px;">
                <input type="text" name="characters[${index}][name]" value="" placeholder="名前" class="widefat" style="margin-bottom:5px;">
                <input type="text" name="characters[${index}][role]" value="" placeholder="役割・読み" class="widefat" style="margin-bottom:5px;">
                <textarea name="characters[${index}][desc]" placeholder="説明" rows="2" class="widefat"></textarea>
                <button type="button" class="button button-link-delete" onclick="removeRow(this)">削除</button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    }

    function addGlossary(prefill) {
        const container = document.getElementById('glossary-container');
        const index = new Date().getTime();
        const html = `
            <div class="item-row" style="border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:10px;">
                <input type="text" name="glossary[${index}][term]" value="" placeholder="用語" class="widefat" style="margin-bottom:5px;">
                <input type="text" name="glossary[${index}][reading]" value="" placeholder="読み" class="widefat" style="margin-bottom:5px;">
                <textarea name="glossary[${index}][desc]" placeholder="説明" rows="2" class="widefat"></textarea>
                <button type="button" class="button button-link-delete" onclick="removeRow(this)">削除</button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);

        if (prefill && typeof prefill === 'object') {
            const row = container.lastElementChild;
            if (!row) return;
            const termEl = row.querySelector('input[placeholder="用語"]');
            const readingEl = row.querySelector('input[placeholder="読み"]');
            const descEl = row.querySelector('textarea[placeholder="説明"]');
            if (termEl && prefill.term) termEl.value = prefill.term;
            if (readingEl && prefill.reading) readingEl.value = prefill.reading;
            if (descEl && prefill.desc) descEl.value = prefill.desc;
        }
    }

    function addGlossaryFromTrivia(btn) {
        const term = btn?.dataset?.term || '';
        const desc = btn?.dataset?.desc || '';
        const url = btn?.dataset?.url || '';

        const lines = [];
        if (desc) lines.push(desc);
        if (url) lines.push('リンク: ' + url);
        addGlossary({ term, reading: '', desc: lines.join('\n') });
    }
    </script>
    <?php
}

/**
 * JSONファイルのアップロード処理
 */
function uir_process_json_upload() {
    // ファイルチェック
    if (!isset($_FILES['json_file']) || $_FILES['json_file']['error'] !== UPLOAD_ERR_OK) {
        return array('type' => 'error', 'message' => 'ファイルのアップロードに失敗しました。');
    }
    
    $file = $_FILES['json_file'];
    
    // 拡張子チェック
    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if ($ext !== 'json') {
        return array('type' => 'error', 'message' => 'JSONファイル (.json) のみアップロードできます。');
    }
    
    // ファイル内容を読み込み
    $content = file_get_contents($file['tmp_name']);
    if ($content === false) {
        return array('type' => 'error', 'message' => 'ファイルの読み込みに失敗しました。');
    }
    
    // ショートコードタグを除去
    $content = trim($content);
    $content = preg_replace('/^\[immersive_reader\]\s*/i', '', $content);
    $content = preg_replace('/\s*\[\/immersive_reader\]$/i', '', $content);
    $content = trim($content);
    
    // JSONパース
    $data = json_decode($content, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        return array(
            'type' => 'error', 
            'message' => 'JSONの解析に失敗しました: ' . json_last_error_msg() . '<br>ファイル: ' . esc_html($file['name'])
        );
    }
    
    // 必須フィールドチェック
    if (empty($data['title'])) {
        return array('type' => 'error', 'message' => 'JSONに title フィールドがありません。');
    }
    
    // 著者名取得
    $author_name = !empty($data['author']) ? $data['author'] : '不明';
    $work_title = $data['title'];
    
    // 投稿タイトルを生成: 著者名　タイトル　ナレーター七味春五郎　発行元丸竹書房
    $post_title = sprintf('%s　%s　ナレーター七味春五郎　発行元丸竹書房', $author_name, $work_title);
    
    // ===== JSONファイルをサーバーに保存 =====
    $upload_dir = wp_upload_dir();
    $json_dir = $upload_dir['basedir'] . '/immersive-reader-data';
    
    // ディレクトリがなければ作成
    if (!file_exists($json_dir)) {
        wp_mkdir_p($json_dir);
        // .htaccessでディレクトリリスティングを防止
        file_put_contents($json_dir . '/.htaccess', 'Options -Indexes');
    }
    
    // ファイル名を生成（タイトルをサニタイズ）
    $safe_filename = sanitize_file_name($work_title) . '_' . time() . '.json';
    $json_file_path = $json_dir . '/' . $safe_filename;
    $json_file_url = $upload_dir['baseurl'] . '/immersive-reader-data/' . $safe_filename;
    
    // JSONファイルを保存
    $json_string = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if (file_put_contents($json_file_path, $json_string) === false) {
        return array('type' => 'error', 'message' => 'JSONファイルの保存に失敗しました。');
    }
    
    // 投稿コンテンツはファイルパスを参照するショートコードのみ（軽量）
    $post_content = '[immersive_reader file="' . esc_attr($json_file_url) . '"]';
    
    // カテゴリIDを取得
    $category = get_category_by_slug('reading_application');
    $category_id = $category ? $category->term_id : 0;
    
    // カテゴリがなければ作成
    if (!$category_id) {
        $category_id = wp_create_category('reading_application');
    }
    
    // 投稿データ
    $post_status = sanitize_text_field($_POST['post_status'] ?? 'draft');
    $author_tag = sanitize_text_field($_POST['author_tag'] ?? '');
    
    // 著者タグが空の場合、JSONから取得
    if (empty($author_tag) && !empty($data['author'])) {
        $author_tag = $data['author'];
    }
    
    // あらすじを取得（SEO用）
    $synopsis = !empty($data['synopsis']) ? $data['synopsis'] : '';
    // 改行を除去し、160文字に制限（meta description用）
    $meta_description = mb_substr(str_replace(array("\r", "\n"), ' ', $synopsis), 0, 160);
    
    // HTMLフィルターを一時的に無効化（ショートコード内のJSONが破壊されるのを防ぐ）
    kses_remove_filters();
    
    // 作品タイトル（JSONのtitle）で既存投稿を検索
    $existing_posts = get_posts(array(
        'post_type' => 'post',
        'meta_key' => '_uir_work_title',
        'meta_value' => $work_title,
        'posts_per_page' => 1
    ));
    
    global $wpdb;
    
    if (!empty($existing_posts)) {
        // 既存投稿を更新
        $post_id = $existing_posts[0]->ID;
        
        // タイトルとステータスを更新
        $wpdb->update(
            $wpdb->posts,
            array(
                'post_title' => $post_title,
                'post_status' => $post_status,
            ),
            array('ID' => $post_id),
            array('%s', '%s'),
            array('%d')
        );
        
        // コンテンツを直接DBに書き込み（大きなデータ対応）
        $wpdb->update(
            $wpdb->posts,
            array('post_content' => $post_content),
            array('ID' => $post_id),
            array('%s'),
            array('%d')
        );
        
        $action = '更新';
    } else {
        // 新規作成：まず空の投稿を作成
        $post_data = array(
            'post_title'    => $post_title,
            'post_content'  => '', // 空で作成
            'post_status'   => $post_status,
            'post_type'     => 'post',
            'post_category' => array($category_id),
        );
        
        $post_id = wp_insert_post($post_data, true);
        
        if (!is_wp_error($post_id) && $post_id > 0) {
            // 投稿作成成功後、コンテンツを直接DBに書き込み
            $wpdb->update(
                $wpdb->posts,
                array('post_content' => $post_content),
                array('ID' => $post_id),
                array('%s'),
                array('%d')
            );
        }
        
        $action = '作成';
    }
    
    // HTMLフィルターを再有効化
    kses_init_filters();
    
    // エラーチェック（WP_Errorまたは0の場合）
    if (is_wp_error($post_id)) {
        return array('type' => 'error', 'message' => '投稿の作成に失敗しました: ' . $post_id->get_error_message());
    }
    
    if (empty($post_id) || $post_id === 0) {
        return array('type' => 'error', 'message' => '投稿の作成に失敗しました。投稿IDが取得できませんでした。データサイズ: ' . strlen($post_content) . ' bytes');
    }
    
    // カスタムフィールドを保存（作品タイトル、SEO情報）
    update_post_meta($post_id, '_uir_work_title', $work_title);
    update_post_meta($post_id, '_uir_author', $author_name);
    update_post_meta($post_id, '_uir_seo_title', $post_title);
    update_post_meta($post_id, '_uir_meta_description', $meta_description);
    // 検索・一覧用の追加メタ（golden_template準拠のキーを優先）
    $genre = '';
    if (!empty($data['japanese_genre'])) {
        $genre = $data['japanese_genre'];
    } elseif (!empty($data['genre'])) {
        $genre = $data['genre'];
    }
    $keywords = '';
    if (!empty($data['keywords']) && is_array($data['keywords'])) {
        $keywords = implode(',', array_map('strval', $data['keywords']));
    }
    update_post_meta($post_id, '_uir_genre', $genre);
    update_post_meta($post_id, '_uir_keywords', $keywords);
    
    // ===== THE THOR テーマ用SEOフィールド =====
    // THE THORの実際のSEO設定メタキー（確認済み）
    update_post_meta($post_id, 'title', $post_title);
    update_post_meta($post_id, 'description', $meta_description);
    
    // ===== その他のSEOプラグイン用 =====
    // Yoast SEO
    update_post_meta($post_id, '_yoast_wpseo_title', $post_title);
    update_post_meta($post_id, '_yoast_wpseo_metadesc', $meta_description);
    // All in One SEO
    update_post_meta($post_id, '_aioseo_title', $post_title);
    update_post_meta($post_id, '_aioseo_description', $meta_description);
    // Rank Math
    update_post_meta($post_id, 'rank_math_title', $post_title);
    update_post_meta($post_id, 'rank_math_description', $meta_description);
    // SEO SIMPLE PACK
    update_post_meta($post_id, 'ssp_meta_title', $post_title);
    update_post_meta($post_id, 'ssp_meta_description', $meta_description);
    
    // 著者タグを設定
    if (!empty($author_tag)) {
        wp_set_post_tags($post_id, array($author_tag), false);
    }
    
    // get_edit_post_link()はコンテキストによってはnullを返すため、直接構築
    $edit_link = admin_url('post.php?post=' . $post_id . '&action=edit');
    $view_link = get_permalink($post_id);
    
    // パーマリンクが取得できない場合のフォールバック
    if (empty($view_link)) {
        $view_link = home_url('?p=' . $post_id);
    }
    
    $chapters_count = isset($data['chapters']) ? count($data['chapters']) : 0;
    $chars_count = 0;
    if (isset($data['chapters'])) {
        foreach ($data['chapters'] as $ch) {
            $chars_count += mb_strlen($ch['content'] ?? '');
        }
    }
    
    return array(
        'type' => 'success',
        'message' => sprintf(
            '<strong>「%s」を%sしました！</strong><br>' .
            '<strong>投稿タイトル:</strong> %s<br>' .
            '<strong>SEO title:</strong> %s<br>' .
            '<strong>meta description:</strong> %s...<br>' .
            '著者タグ: %s / 章数: %d / 文字数: %s<br>' .
            '<a href="%s" class="button button-small">編集</a> ' .
            '<a href="%s" class="button button-small" target="_blank">表示</a>',
            esc_html($work_title),
            $action,
            esc_html($post_title),
            esc_html($post_title),
            esc_html(mb_substr($meta_description, 0, 50)),
            esc_html($author_tag ?: '（なし）'),
            $chapters_count,
            number_format($chars_count),
            esc_url($edit_link),
            esc_url($view_link)
        )
    );
}

/**
 * 管理画面用スタイル
 */
function uir_admin_styles() {
    $screen = get_current_screen();
    if ($screen && $screen->id === 'toplevel_page_uir-json-uploader') {
        echo '<style>
            .wrap .card { padding: 20px; background: #fff; border: 1px solid #ccd0d4; box-shadow: 0 1px 1px rgba(0,0,0,.04); }
            .wrap .card h2 { margin-top: 0; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .wrap .card pre { margin: 0; }
        </style>';
    }
}
add_action('admin_head', 'uir_admin_styles');

/**
 * 投稿コンテンツのwpautop（自動段落）を無効化
 * immersive_readerショートコードを含む投稿で<br>や<p>タグが挿入されるのを防ぐ
 */
function uir_disable_autop_for_shortcode($content) {
    if (has_shortcode($content, 'immersive_reader')) {
        remove_filter('the_content', 'wpautop');
        remove_filter('the_content', 'wptexturize');
    }
    return $content;
}
add_filter('the_content', 'uir_disable_autop_for_shortcode', 0);

/**
 * 投稿保存時にimmersive_readerショートコード内のHTMLタグを除去
 */
function uir_sanitize_shortcode_content($data, $postarr) {
    if (!empty($data['post_content']) && strpos($data['post_content'], '[immersive_reader]') !== false) {
        // ショートコード内のJSONを抽出して再整形
        $data['post_content'] = preg_replace_callback(
            '/\[immersive_reader\](.*?)\[\/immersive_reader\]/s',
            function($matches) {
                $json_content = $matches[1];
                // HTMLタグを除去
                $json_content = strip_tags($json_content);
                // HTMLエンティティをデコード
                $json_content = html_entity_decode($json_content, ENT_QUOTES, 'UTF-8');
                // 特殊な引用符を標準に変換
                $json_content = str_replace(['&#8220;', '&#8221;', '"', '"', '「', '」'], '"', $json_content);
                // 制御文字を除去（改行以外）
                $json_content = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', '', $json_content);
                // 前後の空白を除去
                $json_content = trim($json_content);
                
                // JSONとして有効かチェック
                $decoded = json_decode($json_content, true);
                if (json_last_error() === JSON_ERROR_NONE) {
                    // 有効なJSONなら再エンコード（整形なし、1行）
                    $json_content = json_encode($decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
                }
                
                return '[immersive_reader]' . $json_content . '[/immersive_reader]';
            },
            $data['post_content']
        );
    }
    return $data;
}
add_filter('wp_insert_post_data', 'uir_sanitize_shortcode_content', 10, 2);

/**
 * SEOメタタグの出力（テーマがサポートしていない場合のフォールバック）
 */
function uir_output_seo_meta() {
    if (!is_single()) return;
    
    global $post;
    if (!$post) return;
    
    // カスタムフィールドからSEO情報を取得
    $seo_title = get_post_meta($post->ID, '_uir_seo_title', true);
    $meta_desc = get_post_meta($post->ID, '_uir_meta_description', true);
    
    // すでにSEOプラグインが出力している場合はスキップ
    // Yoast SEO、All in One SEOなどがある場合は出力しない
    if (defined('WPSEO_VERSION') || class_exists('AIOSEO\\Plugin\\AIOSEO')) {
        return;
    }
    
    if ($meta_desc) {
        echo '<meta name="description" content="' . esc_attr($meta_desc) . '">' . "\n";
    }
}
add_action('wp_head', 'uir_output_seo_meta', 1);

/**
 * ドキュメントタイトルのフィルター（SEOタイトル用）
 */
function uir_filter_document_title($title) {
    if (!is_single()) return $title;
    
    global $post;
    if (!$post) return $title;
    
    $seo_title = get_post_meta($post->ID, '_uir_seo_title', true);
    if ($seo_title) {
        return $seo_title;
    }
    
    return $title;
}
add_filter('pre_get_document_title', 'uir_filter_document_title', 10);

/**
 * ページネーションを横並びにするCSS
 */
function uir_pagination_styles() {
    echo '<style>
    /* WordPress標準のページネーションを横並びに */
    .nav-links,
    .page-numbers,
    nav.navigation.pagination .nav-links {
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.5rem !important;
        list-style: none !important;
        padding: 0 !important;
        margin: 1rem 0 !important;
    }
    .nav-links a,
    .nav-links span,
    .page-numbers li {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .page-numbers li a,
    .page-numbers li span {
        padding: 0.5rem 0.75rem !important;
        border: 1px solid #d1d5db !important;
        border-radius: 0.375rem !important;
        text-decoration: none !important;
    }
    .page-numbers li span.current,
    .nav-links span.current {
        background-color: #292524 !important;
        color: white !important;
        border-color: #292524 !important;
    }
    </style>';
}
add_action('wp_head', 'uir_pagination_styles');

// ========================================
// 🆕 Schema.org構造化データ & OGP拡張
// (拡張メタデータ対応版 - v6.6追加)
// ========================================

/**
 * Schema.org JSON-LD構造化データを出力
 * 
 * bookdataから自動的にSchema.org Book形式のJSON-LDを生成し、
 * Google等の検索エンジンに構造化データを提供
 */
function uir_output_schema_org_jsonld() {
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
add_action('wp_head', 'uir_output_schema_org_jsonld');

/**
 * OGP (Open Graph Protocol) メタタグ出力
 * 
 * SNSシェア時の表示を最適化
 */
function uir_output_ogp_tags() {
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
add_action('wp_head', 'uir_output_ogp_tags');

/**
 * Twitter Card メタタグ出力
 */
function uir_output_twitter_card_tags() {
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
add_action('wp_head', 'uir_output_twitter_card_tags');

/**
 * メタディスクリプション最適化
 * 
 * 検索結果のスニペット表示を改善
 */
function uir_optimize_meta_description() {
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
add_action('wp_head', 'uir_optimize_meta_description');

/**
 * タイトルタグ最適化
 */
function uir_optimize_title_tag($title, $sep) {
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
add_filter('wp_title', 'uir_optimize_title_tag', 10, 2);

/**
 * パンくずリスト Schema.org BreadcrumbList
 */
function uir_output_breadcrumb_schema() {
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
add_action('wp_head', 'uir_output_breadcrumb_schema');
