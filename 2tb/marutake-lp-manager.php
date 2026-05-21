<?php
/**
 * Plugin Name: Marutake LP Manager
 * Description: 固定ページ用LPテンプレート管理プラグイン。AudioBook、Reading App、唄本（Utabon）の専用デザインと、アプリ間移動用のフローティングボタンを提供します。
 * Version: 3.1
 * Author: Marutake Shobo
 */

if ( ! defined( 'ABSPATH' ) ) exit;

// クラスの再定義を防ぐ
if ( ! class_exists( 'Marutake_LP_Manager' ) ) :

class Marutake_LP_Manager {
	
	// テンプレート定義
	private $templates = array(
		'marutake-audiobook-lp.php'      => 'Marutake AudioBook LP',
		'marutake-reading-app-lp.php'    => 'Marutake Reading App LP',
		'marutake-themesong-lp.php'      => 'Marutake Utabon LP',
		'marutake-otobon-playlist.php'   => 'Marutake Otobon Playlist LP',
	);
	
	// アプリのURL設定（環境に合わせて修正してください）
	private $links = array(
		'home'      => '/',
		'audiobook' => '/audiobook-library/',
		'reading'   => '/readerlibrary/',
		'themesong' => '/themesong-library/',
	);
	
	public function __construct() {
		add_filter( 'theme_page_templates', array( $this, 'add_templates_to_dropdown' ), 10, 4 );
		add_filter( 'template_include', array( $this, 'load_template_file' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_lp_assets' ) );
	}
	
	public function add_templates_to_dropdown( $post_templates, $wp_theme, $post, $post_type ) {
		foreach ( $this->templates as $slug => $name ) {
			$post_templates[ $slug ] = $name;
		}
		return $post_templates;
	}
	
	public function load_template_file( $template ) {
		global $post;
		if ( ! $post ) return $template;
		
		$saved_template = get_post_meta( $post->ID, '_wp_page_template', true );
		
		if ( $saved_template === 'marutake-audiobook-lp.php' ) {
			$this->render_audiobook_lp();
			exit;
		} elseif ( $saved_template === 'marutake-reading-app-lp.php' ) {
			$this->render_reading_lp();
			exit;
		} elseif ( $saved_template === 'marutake-themesong-lp.php' ) {
			$this->render_themesong_lp();
			exit;
		} elseif ( $saved_template === 'marutake-otobon-playlist.php' ) {
			$this->render_otobon_playlist_lp();
			exit;
		}
		
		return $template;
	}
	
	public function enqueue_lp_assets() {
		// 共通アセットがあればここに記述
	}
	
	// =================================================================
	// 共通パーツ：フローティング・アプリランチャー
	// =================================================================
	private function render_app_launcher() {
		?>
		<!-- Floating App Launcher -->
		<div id="marutake-app-fab" class="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-4 group">
			
			<!-- Menu Items (Hoverで表示 / スマホはClickで表示制御) -->
			<div id="marutake-fab-menu" class="flex flex-col gap-3 transition-all duration-300 opacity-0 translate-y-10 invisible group-hover:opacity-100 group-hover:translate-y-0 group-hover:visible">
				
				<!-- Home -->
				<a href="<?php echo esc_url( home_url('/') ); ?>" class="flex items-center gap-3 pl-4 pr-1 py-1 rounded-full bg-white shadow-lg hover:scale-105 transition transform origin-right group/item no-underline">
					<span class="text-xs font-bold text-gray-500 group-hover/item:text-gray-800 whitespace-nowrap">TOPへ</span>
					<div class="w-10 h-10 rounded-full bg-gray-600 text-white flex items-center justify-center shadow-md">
						<span class="material-icons text-lg">home</span>
					</div>
				</a>
				
				<!-- Utabon (唄本) -->
				<a href="<?php echo esc_url( home_url($this->links['themesong']) ); ?>" class="flex items-center gap-3 pl-4 pr-1 py-1 rounded-full bg-white shadow-lg hover:scale-105 transition transform origin-right group/item no-underline">
					<span class="text-xs font-bold text-gray-500 group-hover/item:text-pink-600 whitespace-nowrap">唄本</span>
					<div class="w-10 h-10 rounded-full bg-gradient-to-br from-[#E91E63] to-[#4A148C] text-white flex items-center justify-center shadow-md">
						<span class="material-icons text-lg">music_note</span>
					</div>
				</a>
				
				<!-- Reading App -->
				<a href="<?php echo esc_url( home_url($this->links['reading']) ); ?>" class="flex items-center gap-3 pl-4 pr-1 py-1 rounded-full bg-white shadow-lg hover:scale-105 transition transform origin-right group/item no-underline">
					<span class="text-xs font-bold text-gray-500 group-hover/item:text-brown-800 whitespace-nowrap">本を読む</span>
					<div class="w-10 h-10 rounded-full bg-[#3E2723] text-white flex items-center justify-center shadow-md">
						<span class="material-icons text-lg">book</span>
					</div>
				</a>
				
				<!-- AudioBook -->
				<a href="<?php echo esc_url( home_url($this->links['audiobook']) ); ?>" class="flex items-center gap-3 pl-4 pr-1 py-1 rounded-full bg-white shadow-lg hover:scale-105 transition transform origin-right group/item no-underline">
					<span class="text-xs font-bold text-gray-500 group-hover/item:text-indigo-800 whitespace-nowrap">朗読を聴く</span>
					<div class="w-10 h-10 rounded-full bg-[#1A237E] text-white flex items-center justify-center shadow-md">
						<span class="material-icons text-lg">headphones</span>
					</div>
				</a>
			</div>
			
			<!-- Main Button -->
			<button onclick="toggleFabMenu(this)" class="w-14 h-14 rounded-full bg-[#FFC107] text-[#1A237E] shadow-xl flex items-center justify-center transition-transform duration-200 hover:scale-110 focus:outline-none z-50">
				<span class="material-icons text-3xl">apps</span>
			</button>
		</div>
		
		<script>
			// スマホ用: タップでメニュー固定表示を切り替え
			function toggleFabMenu(btn) {
				const menu = document.getElementById('marutake-fab-menu');
				// クラス操作で表示状態をトグル（CSSのgroup-hoverとは別に制御）
				if (menu.style.opacity === '1') {
					menu.style.opacity = '';
					menu.style.visibility = '';
					menu.style.transform = '';
				} else {
					menu.style.opacity = '1';
					menu.style.visibility = 'visible';
					menu.style.transform = 'translateY(0)';
				}
			}
		</script>
		<?php
	}
	
	// =================================================================
	// 共通ヘッダー（CSS設定など）
	// =================================================================
	private function print_common_head() {
		?>
		<!-- Google Fonts -->
		<link rel="preconnect" href="https://fonts.googleapis.com">
		<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
		<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@600;900&display=swap" rel="stylesheet">
		<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
		
		<!-- Tailwind CSS -->
		<script src="https://cdn.tailwindcss.com"></script>
		<script>
			tailwind.config = {
				theme: {
					extend: {
						colors: {
							primary: '#1A237E',      /* Indigo */
							accent: '#FFC107',       /* Amber */
							musicPrimary: '#4A148C', /* Deep Purple */
							musicAccent: '#E91E63',  /* Pink */
							textMain: '#212121',
							textSub: '#757575',
							bgBase: '#F5F5F5',
						},
						fontFamily: {
							sans: ['"Noto Sans JP"', 'sans-serif'],
							serif: ['"Noto Serif JP"', 'serif'],
						},
						animation: {
							'bounce-slow': 'bounce 3s infinite',
						}
					}
				}
			}
		</script>
		
		<style>
			html { margin-top: 0 !important; }
			body { background-color: #F5F5F5; color: #212121; line-height: 1.8; margin: 0; padding: 0; }
			html { scroll-behavior: smooth; }
			
			/* 背景設定 */
			.hero-bg-audio { background: linear-gradient(rgba(26, 35, 126, 0.85), rgba(26, 35, 126, 0.95)), url('https://images.unsplash.com/photo-1507842217121-9e8023d58371?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80') center/cover; }
			.hero-bg-reading { background: linear-gradient(rgba(26, 35, 126, 0.9), rgba(62, 39, 35, 0.9)), url('https://images.unsplash.com/photo-1524985069026-dd778a71c7b4?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80') center/cover; }
			.hero-bg-music { background: linear-gradient(135deg, rgba(74, 20, 140, 0.9), rgba(233, 30, 99, 0.8)), url('https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80') center/cover; }
			.hero-title-outline {
				color: transparent;
				-webkit-text-stroke: 2px rgba(255,255,255,0.95);
				text-shadow: 0 0 18px rgba(0,0,0,0.6);
			}
			
			/* カード */
			.md-card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s ease; }
			.md-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
			
			/* ボタン */
			.btn-primary { background-color: #FFC107; color: #1A237E; font-weight: 700; padding: 12px 32px; border-radius: 50px; box-shadow: 0 3px 5px rgba(0,0,0,0.2); transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; }
			.btn-primary:hover { background-color: #FFD54F; transform: scale(1.05); text-decoration: none; }
			
			.btn-music { background: linear-gradient(45deg, #E91E63, #FF4081); color: white; font-weight: 700; padding: 12px 32px; border-radius: 50px; box-shadow: 0 3px 5px rgba(0,0,0,0.3); transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; }
			.btn-music:hover { background: linear-gradient(45deg, #C2185B, #F50057); transform: scale(1.05); text-decoration: none; }
			
			/* FAQ */
			details > summary { list-style: none; }
			details > summary::-webkit-details-marker { display: none; }
			details[open] summary ~ * { animation: sweep .3s ease-in-out; }
			@keyframes sweep { 0% {opacity: 0; transform: translateY(-10px)} 100% {opacity: 1; transform: translateY(0)} }
			.rotate-icon { transition: transform 0.3s; }
			details[open] .rotate-icon { transform: rotate(180deg); }
			
			/* テーマ干渉対策 */
			#footer, .site-footer, .footer-wrap, .footer-container, #colophon, .copyright, .footer-bottom { display: none !important; }
			#marutake-lp-footer { display: block !important; }
			#library-app-container, #reader-app-container, #themesong-app-container { min-height: 600px; }
		</style>
		<?php
	}
	
	// =================================================================
	// 1. AudioBook Library LP
	// =================================================================
	private function render_audiobook_lp() {
		global $post;
		?>
		<!DOCTYPE html>
		<html lang="ja">
			<head>
				<meta charset="UTF-8">
				<meta name="viewport" content="width=device-width, initial-scale=1.0">
				<title><?php wp_title('|', true, 'right'); ?><?php bloginfo('name'); ?></title>
				<?php if ( function_exists('has_post_thumbnail') && has_post_thumbnail( $post->ID ) ): ?>
				<meta property="og:image" content="<?php echo get_the_post_thumbnail_url( $post->ID, 'large' ); ?>">
				<?php endif; ?>
				<script type="application/ld+json">
					{
						"@context": "https://schema.org",
						"@type": "WebApplication",
						"name": "Marutake AudioBook Library",
						"url": "<?php echo esc_url( get_permalink() ); ?>",
						"applicationCategory": "MultimediaApplication",
						"operatingSystem": "WebBrowser",
						"provider": { "@type": "Organization", "name": "丸竹書房" }
					}
				</script>
				<?php $this->print_common_head(); ?>
				<?php wp_head(); ?>
			</head>
			<body class="font-sans text-textMain bg-bgBase antialiased">
				<?php wp_body_open(); ?>
				
				<header class="hero-bg-audio text-white min-h-[70vh] flex flex-col items-center justify-center text-center px-4 relative">
					<div class="max-w-4xl z-10">
						<span class="block text-accent font-bold tracking-widest mb-4 uppercase text-sm md:text-base">Marutake Shobou Presents</span>
						<h1 class="text-3xl md:text-5xl lg:text-6xl font-serif font-black mb-6 leading-tight">Marutake AudioBook Library</h1>
						<p class="text-lg md:text-2xl font-serif mb-8 text-gray-200">朗読と物語のための<br class="md:hidden">オーディオブック・ライブラリ</p>
						<div class="w-16 h-1 bg-accent mx-auto mb-8"></div>
						<a href="#library-app" class="btn-primary gap-2 text-lg hover:no-underline"><span class="material-icons">play_circle</span>ライブラリを使う</a>
						<p class="mt-4 text-sm opacity-80 text-white">※ブラウザですぐに使えます</p>
					</div>
					<div class="absolute bottom-8 animate-bounce-slow opacity-70"><span class="material-icons text-4xl">expand_more</span></div>
				</header>
				
				<section class="py-16 px-4 bg-white shadow-sm relative z-10 -mt-8 mx-4 md:mx-auto max-w-5xl rounded-lg md:rounded-t-lg">
					<div class="max-w-3xl mx-auto text-center">
						<p class="text-lg leading-loose text-textMain">
							<span class="font-serif font-bold text-primary text-xl">Marutake AudioBook Library</span> は、<br>
							丸竹書房が運営する、歴史小説・文豪作品を中心とした<br>
							<span class="border-b-4 border-accent/30">朗読オーディオブック専用ライブラリ</span> です。<br><br>
							YouTube・Spotify と連携しながら、<br>
							「物語」「朗読」「主題歌」をひとつの棚に並べるように整理しました。<br>
							お気に入りの物語を、いつでも・どこでも、耳から楽しんでください。
						</p>
					</div>
				</section>
				
				<section class="py-20 px-4 bg-bgBase">
					<div class="max-w-6xl mx-auto">
						<h2 class="text-center text-3xl font-serif font-bold text-primary mb-12">このアプリでできること</h2>
						<div class="grid md:grid-cols-3 gap-8">
							<div class="md-card p-8 flex flex-col items-center text-center">
								<div class="bg-indigo-50 p-4 rounded-full mb-6 text-primary"><span class="material-icons text-4xl">search</span></div>
								<h3 class="text-xl font-bold mb-4">1. 探す</h3>
								<p class="text-textSub text-sm leading-relaxed">「作者」「ジャンル」「雰囲気」から、今の気分に合う物語を検索できます。AIによるキーワード抽出にも対応。</p>
							</div>
							<div class="md-card p-8 flex flex-col items-center text-center relative overflow-hidden">
								<div class="absolute top-0 left-0 w-full h-1 bg-accent"></div>
								<div class="bg-indigo-50 p-4 rounded-full mb-6 text-primary"><span class="material-icons text-4xl">headphones</span></div>
								<h3 class="text-xl font-bold mb-4">2. 聴く</h3>
								<p class="text-textSub text-sm leading-relaxed">朗読は <strong>YouTube</strong> で再生。<br>主題歌は <strong>Spotify</strong> 等へリンク。<br>作品ページからワンクリックで物語の世界へ。</p>
							</div>
							<div class="md-card p-8 flex flex-col items-center text-center">
								<div class="bg-indigo-50 p-4 rounded-full mb-6 text-primary"><span class="material-icons text-4xl">history_edu</span></div>
								<h3 class="text-xl font-bold mb-4">3. 知る</h3>
								<p class="text-textSub text-sm leading-relaxed">あらすじ、時代背景、シリーズ順序などを網羅。「次は何を聴けばいい？」がすぐに分かります。</p>
							</div>
						</div>
					</div>
				</section>

				<section class="py-20 px-4 bg-white">
					<div class="max-w-6xl mx-auto">
						<h2 class="text-3xl font-serif font-bold text-musicPrimary text-center mb-10">OtobonSong ランキング</h2>
						<?php echo do_shortcode( '[themesong_ranking period="monthly" limit="6"]' ); ?>
						<?php echo do_shortcode( '[themesong_ranking period="yearly" limit="6"]' ); ?>
					</div>
				</section>
				
				
				<div id="library-app" class="bg-white py-20 px-4 border-t border-gray-200">
					<div class="max-w-7xl mx-auto">
						<div class="text-center mb-10">
							<span class="text-accent font-bold tracking-widest uppercase">Library</span>
							<h2 class="text-3xl md:text-4xl font-serif font-bold text-primary mt-2">オーディオブックを探す</h2>
						</div>
						<div id="library-app-container" class="min-h-[400px]">
							<?php echo do_shortcode('[marutake_library]'); ?>
						</div>
					</div>
				</div>
				
				<!-- FAQ -->
				<section class="py-20 px-4 bg-gray-50">
					<div class="max-w-3xl mx-auto">
						<h2 class="text-center text-2xl font-serif font-bold text-primary mb-10">よくある質問</h2>
						<div class="space-y-4">
							
							<!-- Q1 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. 無料で利用できますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. はい。YouTubeで公開されている朗読作品へのリンク集ですので、無料でお楽しみいただけます。
								</div>
							</details>
							
							<!-- Q2 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. アプリのインストールは必要ですか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. いいえ、不要です。このページ自体がWebアプリケーションとして機能しています。ブックマークしてご利用ください。
								</div>
							</details>
							
							<!-- Q3 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. 通信量はかかりますか？オフラインで聴けますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. 動画のストリーミング再生を行うため通信量がかかります。<strong>Wi-Fi環境でのご利用を推奨</strong>いたします。<br />
									なお、YouTube Premium会員の方は、YouTubeアプリ側の機能としてオフライン再生が可能です。
								</div>
							</details>
							
							<!-- Q4 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. スマホで他のアプリを使いながら聴けますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. 基本的に再生中はブラウザ画面を表示していただく必要があります。<br />
									（YouTube Premium会員の方は、バックグラウンド再生機能により、画面を閉じたり他のアプリを操作しながらの再生が可能です）
								</div>
							</details>
							
							<!-- Q5 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. 倍速で聴くことはできますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. はい、可能です。再生画面（プレーヤー）内の歯車マーク（設定）から、再生速度を変更してお楽しみください。
								</div>
							</details>
							
							<!-- Q6 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. Spotifyで朗読は聴けますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. 現在、<strong>朗読本編はYouTubeのみ</strong>での配信となります。Spotifyなどの音楽配信サービスでは、作品の世界観に合わせた「オリジナル主題歌・テーマソング」を配信しています。
								</div>
							</details>
							
							<!-- Q7 -->
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain">
									<span>Q. 読んでほしい作品をリクエストできますか？</span><br />
									<span class="material-icons text-gray-400 rotate-icon">expand_more</span>
								</summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">
									A. はい。YouTubeのコメント欄やお問い合わせフォームより承っております。<br />
									主に著作権保護期間が満了した作品（パブリックドメイン）や、許諾をいただいた作品から選定して制作しています。
								</div>
							</details>
							
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain"><span>Q. 読書アプリのテキストは、自由にコピーしてもいいですか？</span><span class="material-icons text-gray-400 rotate-icon">expand_more</span></summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">A. 青空文庫由来のテキスト（パブリックドメイン作品）については、青空文庫の規定に従って自由に利用可能です。ただし、当サイト独自の解説文やレイアウト、アプリのプログラムコード等の無断転載はご遠慮ください。</div>
							</details>
							
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain"><span>Q. 朗読に合わせたテロップは、どのように作っていますか？</span><span class="material-icons text-gray-400 rotate-icon">expand_more</span></summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">A. 原文のリズムを損なわないよう配慮、青空文庫にないものは七味春五郎がテキスト化。動画にはVrewを利用しています。</div>
							</details>
							
							<details class="group bg-white rounded-lg shadow-sm open:shadow-md transition-all">
								<summary class="flex justify-between items-center font-bold cursor-pointer p-6 list-none text-textMain"><span>Q. スマートフォンでも利用できますか？</span><span class="material-icons text-gray-400 rotate-icon">expand_more</span></summary>
								<div class="text-textSub px-6 pb-6 border-t border-gray-100 pt-4">A. はい。PC、タブレット、スマートフォンのブラウザに対応しています。縦書き・横書きの切り替えも可能です。</div>
							</details>
							
						</div>
					</div>
				</section>
				
				<footer id="marutake-lp-footer" class="bg-primary text-gray-300 py-12 px-4 text-center">
					<div class="max-w-4xl mx-auto">
						<h3 class="text-white text-xl font-serif font-bold mb-4">丸竹書房</h3>
						<p class="text-sm opacity-80 mb-8">読書のよろこびを、音と言葉のかたちで。<br>JASRAC / 自社制作オーディオブックと唄本（Utabon）</p>
						<div class="border-t border-indigo-800 pt-8 text-xs opacity-60">&copy; Marutake Shobou All Rights Reserved.</div>
					</div>
				</footer>
				
				<?php $this->render_app_launcher(); ?>
				<?php wp_footer(); ?>
			</body>
		</html>
		<?php
	}
	
	// =================================================================
	// 2. Reading App LP
	// =================================================================
	private function render_reading_lp() {
		global $post;
		?>
		<!DOCTYPE html>
		<html lang="ja">
			<head>
				<meta charset="UTF-8">
				<meta name="viewport" content="width=device-width, initial-scale=1.0">
				<title><?php wp_title('|', true, 'right'); ?><?php bloginfo('name'); ?></title>
				<?php if ( function_exists('has_post_thumbnail') && has_post_thumbnail( $post->ID ) ): ?>
				<meta property="og:image" content="<?php echo get_the_post_thumbnail_url( $post->ID, 'large' ); ?>">
				<?php endif; ?>
				<script type="application/ld+json">
					{
						"@context": "https://schema.org",
						"@type": "WebApplication",
						"name": "丸竹書房 読書アプリ",
						"description": "文豪作品や歴史小説のテキストを朗読と連動させて表示する、Webベースの読書アプリケーション。",
						"url": "<?php echo esc_url( get_permalink() ); ?>",
						"applicationCategory": "MultimediaApplication",
						"operatingSystem": "WebBrowser",
						"author": { "@type": "Person", "name": "七味春五郎" },
						"provider": { "@type": "Organization", "name": "丸竹書房" }
					}
				</script>
				<?php $this->print_common_head(); ?>
				<?php wp_head(); ?>
			</head>
			<body class="font-sans text-textMain bg-bgBase antialiased">
				<?php wp_body_open(); ?>
				
				<header class="hero-bg-reading text-white min-h-[75vh] flex flex-col items-center justify-center text-center px-4 relative">
					<div class="max-w-4xl z-10">
						<span class="block text-accent font-bold tracking-widest mb-4 uppercase text-sm md:text-base">Marutake Shobou Reading App</span>
						<h1 class="text-3xl md:text-5xl lg:text-6xl font-serif font-black mb-6 leading-tight">読むことと聴くことを、<br>一枚の画面に。</h1>
						<p class="text-lg md:text-2xl font-serif mb-8 text-gray-200">紙の本のように文字を追いながら、<br class="md:hidden">朗読の声に身をあずける——。</p>
						<div class="w-16 h-1 bg-accent mx-auto mb-8"></div>
						<a href="#reader-app" class="btn-primary gap-2 text-lg hover:no-underline"><span class="material-icons">book</span>読書アプリを開く</a>
						<p class="mt-4 text-sm opacity-80 text-white">※ブラウザ・登録不要</p>
					</div>
					<div class="absolute bottom-8 animate-bounce-slow opacity-70"><span class="material-icons text-4xl">expand_more</span></div>
				</header>
				
				<section class="py-16 px-4 bg-white shadow-sm relative z-10 -mt-8 mx-4 md:mx-auto max-w-5xl rounded-lg md:rounded-t-lg">
					<div class="max-w-3xl mx-auto text-center">
						<h2 class="text-2xl font-serif font-bold text-primary mb-6">朗読テロップ付きの「文豪ライブラリ」</h2>
						<p class="text-lg leading-loose text-textMain">
							丸竹書房の読書アプリは、文豪作品・歴史小説・古典的名作を中心にテキスト化し、<br>
							<strong class="text-primary border-b-2 border-accent/30">「読む」と「聴く」を同じ作品で共有できる</strong><br>
							Web読書アプリケーションです。<br><br>
							青空文庫のテキストやオリジナル編集版を、<br>
							朗読の進行に合わせたテロップとしてブラウザ上で快適に楽しめます。
						</p>
					</div>
				</section>
				
				<section class="py-20 px-4 bg-bgBase">
					<div class="max-w-6xl mx-auto">
						<h2 class="text-center text-3xl font-serif font-bold text-primary mb-12">読書アプリの主な機能</h2>
						<div class="grid md:grid-cols-2 gap-8">
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-indigo-50 p-3 rounded-full text-primary"><span class="material-icons text-3xl">subtitles</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-primary">テキスト＋朗読テロップ表示</h3>
									<p class="text-textSub text-sm leading-relaxed">文豪作品のテキストを表示しながら、同じ作品の朗読動画を再生可能。「耳で聴きながら目で楽しむ」読書体験が可能です。</p>
								</div>
							</div>
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-indigo-50 p-3 rounded-full text-primary"><span class="material-icons text-3xl">history_edu</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-primary">文豪・歴史小説に特化</h3>
									<p class="text-textSub text-sm leading-relaxed">吉川英治、野村胡堂ほか、歴史・時代・文芸作品を中心に展開しています。七味春五郎本人の作品も収録予定。文豪でない人が混じりますが、ごめんなさい</p>
								</div>
							</div>
						</div>
					</div>
				</section>
				
				<div id="reader-app" class="bg-white py-20 px-4 border-t border-gray-200">
					<div class="max-w-7xl mx-auto">
						<div class="text-center mb-10">
							<span class="text-accent font-bold tracking-widest uppercase">Reading Library</span>
							<h2 class="text-3xl md:text-4xl font-serif font-bold text-primary mt-2">作品を探す</h2>
						</div>
						<div id="reader-app-container" class="min-h-[500px]">
							<?php echo do_shortcode('[reader_library]'); ?>
						</div>
					</div>
				</div>
				
				<section class="py-20 px-4 bg-bgBase">
					<div class="max-w-4xl mx-auto flex flex-col md:flex-row items-center gap-10">
						<div class="w-40 h-40 rounded-full bg-gray-300 flex-shrink-0 overflow-hidden shadow-lg border-4 border-white">
							<div class="w-full h-full flex items-center justify-center bg-primary text-white text-4xl font-serif">七</div>
						</div>
						<div class="text-center md:text-left">
							<span class="text-accent font-bold tracking-widest text-sm">PRODUCER</span>
							<h2 class="text-2xl font-serif font-bold text-primary mb-4">七味 春五郎 <span class="text-base font-normal opacity-70">Shichimi Harugoro</span></h2>
							<p class="text-textSub leading-relaxed mb-4">小説家・作詞家・朗読家。出版社「丸竹書房」代表。<br>朗読者として AudioBook・YouTube チャンネルを運営しています。
							作曲補助plug-inを開発中。DTM作曲にもチャレンジしています。</p>
							<p class="text-sm text-textSub bg-white p-4 rounded shadow-sm"><strong>制作体制について</strong><br>読書アプリの企画・テキスト整形・朗読・唄本（OtobonSong）制作・Webアプリ設計まで、丸竹書房が責任を持って制作・運営しています。</p>
						</div>
					</div>
				</section>
				
				<footer id="marutake-lp-footer" class="bg-primary text-gray-300 py-12 px-4 text-center">
					<div class="max-w-4xl mx-auto">
						<h3 class="text-white text-xl font-serif font-bold mb-4">丸竹書房</h3>
						<p class="text-sm opacity-80 mb-8">読書のよろこびを、音と言葉のかたちで。<br>JASRAC / 自社制作オーディオブックと唄本（Utabon）</p>
						<div class="border-t border-indigo-800 pt-8 text-xs opacity-60">&copy; Marutake Shobou All Rights Reserved.</div>
					</div>
				</footer>
				
				<?php $this->render_app_launcher(); ?>
				<?php wp_footer(); ?>
			</body>
		</html>
		<?php
	}
	
	// =================================================================
	// 3. Utabon (唄本) LP
	// =================================================================
	private function render_themesong_lp() {
		global $post;
		?>
		<!DOCTYPE html>
		<html lang="ja">
			<head>
				<meta charset="UTF-8">
				<meta name="viewport" content="width=device-width, initial-scale=1.0">
				<title><?php wp_title('|', true, 'right'); ?><?php bloginfo('name'); ?></title>
				<meta name="description" content="唄本（Utabon）は、丸竹書房の作品世界を彩るOtobonSong（MP3/MP4）を集めたライブラリです。">
				<?php if ( function_exists('has_post_thumbnail') && has_post_thumbnail( $post->ID ) ): ?>
				<meta property="og:image" content="<?php echo get_the_post_thumbnail_url( $post->ID, 'large' ); ?>">
				<?php endif; ?>
				<script type="application/ld+json">
					{
						"@context": "https://schema.org",
						"@type": "MusicPlaylist",
						"name": "唄本（Utabon）",
						"url": "<?php echo esc_url( get_permalink() ); ?>",
						"description": "丸竹書房の作品世界を彩るOtobonSong（MP3/MP4）を集めたライブラリ。",
						"provider": { "@type": "Organization", "name": "丸竹書房" }
					}
				</script>
				<?php $this->print_common_head(); ?>
				<?php wp_head(); ?>
			</head>
			<body class="font-sans text-textMain bg-bgBase antialiased">
				<?php wp_body_open(); ?>
				
				<header class="hero-bg-music text-white min-h-[75vh] flex flex-col items-center justify-center text-center px-4 relative">
					<div class="max-w-4xl z-10">
						<span class="block text-yellow-200 font-bold tracking-widest mb-4 uppercase text-sm md:text-base">Marutake Utabon（唄本）</span>
					<h1 class="text-3xl md:text-5xl lg:text-6xl font-serif font-black mb-6 leading-tight hero-title-outline">
							物語のための<br>唄本（Utabon）
						</h1>
						<p class="text-lg md:text-2xl font-serif mb-8 text-gray-100">
							作品ごとのテーマ曲、シリーズのイメージソング。<br>
							これらを一つの棚に並べました。
						</p>
						<div class="w-16 h-1 bg-musicAccent mx-auto mb-8"></div>
						
						<a href="#themesong-app" class="btn-music gap-2 text-lg hover:no-underline">
							<span class="material-icons">library_music</span>
							唄本（Utabon）を開く
						</a>
						<p class="mt-4 text-sm opacity-80 text-white">※ローカル音源（MP3/MP4）で再生</p>
					</div>
					<div class="absolute bottom-8 animate-bounce-slow opacity-70"><span class="material-icons text-4xl">expand_more</span></div>
				</header>
				
				<section class="py-16 px-4 bg-white shadow-sm relative z-10 -mt-8 mx-4 md:mx-auto max-w-5xl rounded-lg md:rounded-t-lg border-t-4 border-musicPrimary">
					<div class="max-w-3xl mx-auto text-center">
						<h2 class="text-2xl font-serif font-bold text-musicPrimary mb-6">物語の入口になる「唄本」</h2>
						<p class="text-lg leading-loose text-textMain">
							唄本（Utabon） 　丸竹書房が制作した作品世界をもとに、
							OtobonSong（MP3/MP4）を整理して聴けるようにしたライブラリです。
							ひとつの画面で閲覧・再生できる
							<strong class="text-musicPrimary border-b-2 border-musicAccent/30">音源専用のWebライブラリアプリ</strong>です。<br><br>
							「歌から物語へ」「物語から歌へ」と自由に行き来し、
							文豪たちの世界観をより深く味わうためのハブとして設計しています。
						</p>
					</div>
				</section>
				
				<section class="py-20 px-4 bg-bgBase">
					<div class="max-w-6xl mx-auto">
						<h2 class="text-center text-3xl font-serif font-bold text-musicPrimary mb-12">唄本（Utabon）の特徴</h2>
						<div class="grid md:grid-cols-2 gap-8">
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-purple-100 p-3 rounded-full text-musicPrimary"><span class="material-icons text-3xl">queue_music</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-musicPrimary">作品ごとに音源を一元管理</h3>
									<p class="text-textSub text-sm leading-relaxed">OP/EDテーマ、アレンジ違いなどを含め、「どの物語にどの楽曲が対応しているか」が一目でわかります。</p>
								</div>
							</div>
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-purple-100 p-3 rounded-full text-musicPrimary"><span class="material-icons text-3xl">link</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-musicPrimary">ローカル音源で再生</h3>
									<p class="text-textSub text-sm leading-relaxed">サイト内にアップロードしたMP3/MP4を、そのままブラウザで再生できます。</p>
								</div>
							</div>
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-purple-100 p-3 rounded-full text-musicPrimary"><span class="material-icons text-3xl">local_offer</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-musicPrimary">気分やシーンで探せる</h3>
									<p class="text-textSub text-sm leading-relaxed">「戦いの前」「静かな夜」などのタグで検索可能。物語のテーマだけでなく、作業用BGMとしても選べます。</p>
								</div>
							</div>
							<div class="md-card p-8 flex gap-4 items-start">
								<div class="flex-shrink-0 bg-purple-100 p-3 rounded-full text-musicPrimary"><span class="material-icons text-3xl">import_contacts</span></div>
								<div>
									<h3 class="text-xl font-bold mb-3 text-musicPrimary">物語アプリとの連携</h3>
									<p class="text-textSub text-sm leading-relaxed">Audiobook Libraryや読書アプリへの導線を用意。音楽を通じた「物語の復習・追体験」が可能です。</p>
								</div>
							</div>
						</div>
					</div>
				</section>
				
				<div id="themesong-app" class="bg-gray-900 py-20 px-4 border-t border-gray-800">
					<div class="max-w-7xl mx-auto">
						<div class="text-center mb-10">
							<span class="text-yellow-300 font-bold tracking-widest uppercase">唄本（Utabon）</span>
							<h2 class="text-3xl md:text-4xl font-serif font-bold text-white mt-2">唄本を探す</h2>
						</div>
						<div id="themesong-app-container" class="min-h-[500px]">
							<?php echo do_shortcode('[themesong_library]'); ?>
						</div>
					</div>
				</div>

				<section class="py-16 px-4 bg-gray-900 border-t border-gray-800">
					<div class="max-w-6xl mx-auto text-center text-white">
						<h3 class="text-2xl font-serif font-bold mb-6">OtobonSong Playlist Stage</h3>
						<p class="mb-8 text-sm text-gray-300">視聴者のプレイリスト登録がこのページだけで完結します。OtobonSong ミニプレイヤー内の「プレイリストに追加」を使ってお気に入りを貯め、下のランキング＆プレイリストカードで共有できます。</p>
						<div class="grid md:grid-cols-2 gap-8">
							<div class="bg-black/60 rounded-3xl p-6 border border-white/10 shadow-xl">
								<h4 class="text-xl font-serif mb-4">今月の OtobonSong</h4>
								<?php echo do_shortcode('[themesong_ranking period="monthly" limit="4"]'); ?>
							</div>
							<div class="bg-black/60 rounded-3xl p-6 border border-white/10 shadow-xl">
								<h4 class="text-xl font-serif mb-4">年間ベスト Otobon</h4>
								<?php echo do_shortcode('[themesong_ranking period="yearly" limit="4"]'); ?>
							</div>
						</div>
						<div class="mt-12 bg-white/10 backdrop-blur-sm rounded-2xl p-6">
							<h4 class="text-lg font-serif mb-3 text-yellow-200">プレイリスト共有</h4>
							<p class="text-xs text-gray-300 mb-4">このページで生成した “Otobon Playlist Builder” の JSON を元に、月刊/年間ランキングや共有プレイリストのページを随時更新できます。</p>
							<p class="text-xs text-gray-300">（ランキング JSON は <code>RadioStation/archive/playlist_rankings</code> から出力されています。）</p>
						</div>
					</div>
				</section>
				
				<footer id="marutake-lp-footer" class="bg-musicPrimary text-gray-300 py-12 px-4 text-center">
					<div class="max-w-4xl mx-auto">
						<h3 class="text-white text-xl font-serif font-bold mb-4">丸竹書房</h3>
						<p class="text-sm opacity-80 mb-8">読書のよろこびを、音と言葉のかたちで。<br>JASRAC / 自社制作オーディオブックと唄本（Utabon）を運用中</p>
						<div class="border-t border-purple-800 pt-8 text-xs opacity-60">&copy; Marutake Shobou All Rights Reserved.</div>
					</div>
				</footer>
				
				<?php $this->render_app_launcher(); ?>
				<?php wp_footer(); ?>
			</body>
		</html>
		<?php
		return;
	}

	// =================================================================
	// 4. Otobon Playlist ランキングページ用
	// =================================================================
	private function render_otobon_playlist_lp() {
		$monthly = $this->load_playlist_ranking( 'monthly' );
		$yearly  = $this->load_playlist_ranking( 'yearly' );
		?>
		<!DOCTYPE html>
		<html lang="ja">
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1.0">
			<title>OtobonSong Playlist | <?php bloginfo( 'name' ); ?></title>
			<?php $this->print_common_head(); ?>
			<?php wp_head(); ?>
			<style>
				body { background: #05050a; color: #fff; }
				.otobon-playlist-grid { display: grid; gap: 18px; max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
				.otobon-playlist-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); padding: 22px; border-radius: 18px; box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
				.otobon-playlist-card h3 { margin-top: 0; font-size: 1.6rem; }
				.otobon-playlist-card ul { list-style: none; margin: 0; padding: 0; }
				.otobon-playlist-card li { margin-bottom: 8px; font-size: 0.95rem; }
			</style>
		</head>
		<body>
			<header class="hero-bg-music text-white py-20 text-center">
				<h1 class="text-4xl font-serif font-bold mb-4">OtobonSong Playlist Gallery</h1>
				<p class="text-lg max-w-3xl mx-auto text-white/80">読者がプレイリストとしてシェアした OtobonSong をランキング化し、Jsonベースで管理・公開するページです。最新ランキングへのリンクは LP からも辿れます。</p>
			</header>

			<section class="otobon-playlist-grid">
				<div class="otobon-playlist-card">
					<h3>月間ランキング</h3>
					<?php echo $this->render_playlist_list( $monthly ); ?>
				</div>
				<div class="otobon-playlist-card">
					<h3>年間ランキング</h3>
					<?php echo $this->render_playlist_list( $yearly ); ?>
				</div>
			</section>

			<footer class="text-center py-10 text-white/60">Jsonファイル: <code>RadioStation/archive/playlist_rankings</code></footer>
			<?php wp_footer(); ?>
		</body>
		</html>
		<?php
	}

	private function load_playlist_ranking( $period ) {
		$dir = trailingslashit( plugin_dir_path( __FILE__ ) ) . 'RadioStation/archive/playlist_rankings/';
		$path = $dir . $period . '.json';
		if ( ! file_exists( $path ) ) {
			return array();
		}
		if ( function_exists( 'wp_json_file_decode' ) ) {
			$data = wp_json_file_decode( $path, array( 'associative' => true ) );
		} else {
			$data = json_decode( file_get_contents( $path ), true );
		}
		if ( ! is_array( $data ) ) {
			return array();
		}
		return $data;
	}

	private function render_playlist_list( $entries ) {
		if ( empty( $entries ) ) {
			return '<p>データがありません（cron を実行してください）。</p>';
		}
		ob_start();
		?>
		<ul>
			<?php foreach ( $entries as $entry ) : ?>
				<li>
					<strong><?php echo esc_html( $entry['title'] ?? 'Untitled' ); ?></strong>
					（Score: <?php echo esc_html( $entry['score'] ?? 0 ); ?> pt）
					<?php if ( ! empty( $entry['emotion'] ) ) : ?>
						<span>Emotion: <?php echo esc_html( $entry['emotion'] ); ?></span>
					<?php endif; ?>
				</li>
			<?php endforeach; ?>
		</ul>
		<?php
		return ob_get_clean();
	}
}

new Marutake_LP_Manager();

endif; // class_exists check
