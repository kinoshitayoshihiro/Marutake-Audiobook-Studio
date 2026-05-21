import { parseCsv, toCsv } from "../../../packages/youtube-analytics/csv.js";
import { normalizeVideo, runDiagnosis } from "../../../packages/channel-report-engine/diagnosis.js";
import { buildOverview, buildFormatBreakdown, groupBy } from "../../../packages/channel-report-engine/metrics.js";

const state = {
  videos: [],
  diagnosed: [],
  filteredTag: "すべて",
  focusedSeries: "すべて",
  focusedPlaylist: "すべて",
  sortMetric: null,
  sortDir: "desc",
  channelName: "未選択",
};
const LAST_LOADED_KEY = "channel_report_last_loaded_file";

const PRESETS = {
  analysisReady: "../../../2tb/youtube_channel_report/ninjo_channel_report/analysis_ready_normal_video.csv",
  analysisReadyTorimono: "../../../2tb/youtube_channel_report/old_channel_report/analysis_ready_normal_video.csv",
  analysisReadyNinjo: "../../../2tb/youtube_channel_report/ninjo_channel_report/analysis_ready_normal_video.csv",
  all: "../../../data/youtube/reports/current_channel_last_90_days_all_videos.csv",
  normal: "../../../data/youtube/reports/current_channel_last_90_days_normal_video.csv",
  short: "../../../data/youtube/reports/current_channel_last_90_days_short_candidate.csv",
  inventory: "../../../data/youtube/inventory/current_channel_upload_inventory.csv",
  author: "../../../data/youtube/by-author/current_channel_videos_by_author.csv",
  sample: "../../../2tb/youtube_channel_report/ninjo_channel_report/youtube_video_report_last_90_days_all_videos.csv",
  torimono: "../../../2tb/youtube_channel_report/old_channel_report/youtube_video_report_last_90_days_all_videos.csv",
  ninjoDirect: "../../../2tb/youtube_channel_report/ninjo_channel_report/youtube_video_report_last_90_days_all_videos.csv",
};

function fmt(n) {
  return Number(n || 0).toLocaleString("ja-JP", { maximumFractionDigits: 2 });
}

function fmtInt(n) {
  return Number(n || 0).toLocaleString("ja-JP");
}

function fmtPct(n) {
  return `${Number(n || 0).toFixed(2)}%`;
}

function toCtrPercent(v) {
  return v > 0 && v <= 1 ? v * 100 : v;
}

function fmtDurationSec(sec) {
  const s = Math.max(0, Math.floor(Number(sec || 0)));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}時間${m}分${r}秒`;
  if (m > 0) return `${m}分${r}秒`;
  return `${r}秒`;
}

function tagClass(tag) {
  if (tag === "総集編候補") return "tag-anthology";
  if (tag === "隠れ名作") return "tag-hidden";
  if (tag === "サムネ改善候補") return "tag-thumb";
  if (tag === "概要欄補強候補") return "tag-desc";
  if (tag === "X再投稿候補") return "tag-x";
  if (tag === "検索強化候補") return "tag-search";
  if (tag === "長尺適性") return "tag-long";
  return "tag-default";
}

function tagsHtml(tags) {
  return tags.map((t) => `<span class="tag ${tagClass(t)}">${t}</span>`).join("");
}

function actionsText(actions) {
  return actions.map(localizeAction).join(" / ");
}

function localizeAction(action) {
  const map = {
    "X再投稿": "Xで再投稿する",
    "固定コメントで再誘導": "固定コメントで再誘導する",
    "サムネ差し替え": "サムネイルを見直す",
    "タイトル再設計": "タイトルの事件性を強める",
    "総集編シードに追加": "総集編候補に追加する",
    "長尺枠で再編集": "長尺向けに再編集する",
    "X投稿ドラフト生成": "X投稿文を作成する",
    "説明欄テンプレ補完": "概要欄に不足要素を追加する",
    "概要欄SEO補強": "検索向けに概要欄を補強する",
  };
  return map[action] || action;
}

function renderOverview() {
  const o = buildOverview(state.diagnosed);
  const formats = buildFormatBreakdown(state.diagnosed);
  const podcastCount = formats.find((f) => f.format === "Podcast")?.count || 0;
  const today = {
    hidden: state.diagnosed.filter((v) => v.diagnosisTags.includes("隠れ名作")).length,
    thumb: state.diagnosed.filter((v) => v.diagnosisTags.includes("サムネ改善候補")).length,
    desc: state.diagnosed.filter((v) => v.diagnosisTags.includes("概要欄補強候補")).length,
    anthology: state.diagnosed.filter((v) => v.diagnosisTags.includes("総集編候補")).length,
    x: state.diagnosed.filter((v) => v.diagnosisTags.includes("X再投稿候補")).length,
  };
  document.querySelector("#overview").innerHTML = `
    <h2>今日見るべき候補</h2>
    <div class="grid">
      <article class="card card-click" data-filter-tag="隠れ名作"><h3>隠れ名作</h3><p>${today.hidden}</p></article>
      <article class="card card-click" data-filter-tag="サムネ改善候補"><h3>サムネ改善候補</h3><p>${today.thumb}</p></article>
      <article class="card card-click" data-filter-tag="概要欄補強候補"><h3>概要欄補強候補</h3><p>${today.desc}</p></article>
      <article class="card card-click" data-filter-tag="総集編候補"><h3>総集編候補</h3><p>${today.anthology}</p></article>
      <article class="card card-click" data-filter-tag="X再投稿候補"><h3>X再投稿候補</h3><p>${today.x}</p></article>
    </div>
    <h2>チャンネル全体</h2>
    <div class="grid">
      ${[
        ["総動画数", o.total], ["通常動画", o.normal], ["Short", o.shorts], ["再生リスト", o.playlists], ["Podcast", o.podcasts], ["ライブ動画", o.liveVideos],
        ["公開", o.publicCount], ["限定公開", o.unlistedCount], ["非公開", o.privateCount],
        ["総再生数", fmtInt(o.totalViews)], ["総再生時間(分)", fmtInt(o.totalWatched)],
        ["平均CTR", fmtPct(o.avgCtr)], ["平均視聴時間", fmtDurationSec(o.avgViewDuration)],
        ["平均視聴率(%)", fmt(o.avgRetention)], ["インプレッション合計", fmt(o.totalImpressions)],
        ["概要欄整備率(%)", fmt(o.descriptionCompleteRate)],
      ].map(([k, v]) => `<article class="card"><h3>${k}</h3><p>${v}</p></article>`).join("")}
    </div>
    <h2>チャンネル全体レポート（種別別）</h2>
    ${podcastCount === 0 ? `<p class="note warn">Podcastが0件です。現在のCSVにPodcast判定列が無い場合、タイトル・video_formatベースの推定になります。</p>` : ""}
    <div class="table-wrap"><table><thead><tr>
      <th>動画種別</th><th>本数</th><th>再生数</th><th>総再生時間（分）</th><th>平均CTR</th><th>平均視聴時間</th>
    </tr></thead><tbody>
      ${formats.map((f) => `<tr>
        <td>${f.format}</td>
        <td>${fmtInt(f.count)}</td>
        <td>${fmtInt(f.totalViews)}</td>
        <td>${fmtInt(f.totalWatched)}</td>
        <td>${fmtPct(f.avgCtr)}</td>
        <td>${fmtDurationSec(f.avgDuration)}</td>
      </tr>`).join("")}
    </tbody></table></div>
  `;

  document.querySelectorAll(".card-click").forEach((el) => {
    el.addEventListener("click", () => {
      state.filteredTag = el.dataset.filterTag;
      document.querySelector('[data-tab="videos"]').click();
      renderVideos();
    });
  });
}

function currentFilters() {
  return {
    author: document.querySelector("#filterAuthor")?.value || "すべて",
    series: document.querySelector("#filterSeries")?.value || state.focusedSeries || "すべて",
    playlist: document.querySelector("#filterPlaylist")?.value || state.focusedPlaylist || "すべて",
    tag: document.querySelector("#filterTag")?.value || state.filteredTag || "すべて",
    type: document.querySelector("#filterType")?.value || "すべて",
    descMissing: document.querySelector("#filterDescMissing")?.value || "すべて",
    sort: document.querySelector("#filterSort")?.value || "総再生時間順",
  };
}

function buildFilterOptions(list, key) {
  return ["すべて", ...new Set(list.map((v) => v[key]).filter(Boolean))];
}

function applyFilters(list, f) {
  let out = list.slice();
  if (f.author !== "すべて") out = out.filter((v) => v.author === f.author);
  if (f.series !== "すべて") out = out.filter((v) => v.series === f.series);
  if (f.playlist !== "すべて") out = out.filter((v) => v.playlistName === f.playlist);
  if (f.tag !== "すべて") out = out.filter((v) => v.diagnosisTags.includes(f.tag));
  if (f.type === "通常動画のみ") out = out.filter((v) => !v.isShortCandidate);
  if (f.type === "Short候補のみ") out = out.filter((v) => v.isShortCandidate);
  if (f.type === "再生リストのみ") out = out.filter((v) => v.formatType === "再生リスト");
  if (f.type === "Podcastのみ") out = out.filter((v) => v.formatType === "Podcast");
  if (f.type === "ライブ動画のみ") out = out.filter((v) => v.formatType === "ライブ動画");
  if (f.descMissing === "あり") {
    out = out.filter((v) => !v.hasDescriptionSynopsis || !v.hasDescriptionCharacters || !v.hasDescriptionGlossary);
  }
  if (f.descMissing === "なし") {
    out = out.filter((v) => v.hasDescriptionSynopsis && v.hasDescriptionCharacters && v.hasDescriptionGlossary);
  }
  const defaultSort = (items) => {
    if (f.sort === "総再生時間順") items.sort((a, b) => b.estimatedMinutesWatched - a.estimatedMinutesWatched);
    if (f.sort === "表示回数順") items.sort((a, b) => b.impressions - a.impressions);
    if (f.sort === "CTR順") items.sort((a, b) => toCtrPercent(b.impressionCtr) - toCtrPercent(a.impressionCtr));
    if (f.sort === "平均視聴時間順") items.sort((a, b) => b.averageViewDuration - a.averageViewDuration);
    if (f.sort === "公開日順") items.sort((a, b) => String(b.publishedAt).localeCompare(String(a.publishedAt)));
  };

  if (state.sortMetric) {
    const metricMap = {
      views: (v) => v.views,
      watched: (v) => v.estimatedMinutesWatched,
      avgView: (v) => v.averageViewDuration,
      impressions: (v) => v.impressions,
      ctr: (v) => toCtrPercent(v.impressionCtr),
      duration: (v) => v.durationSeconds,
    };
    const getter = metricMap[state.sortMetric];
    const dir = state.sortDir === "asc" ? 1 : -1;
    out.sort((a, b) => (getter(a) - getter(b)) * dir);
  } else {
    defaultSort(out);
  }
  return out;
}

function sortIndicator(metric) {
  if (state.sortMetric !== metric) return "";
  return state.sortDir === "asc" ? " ↑" : " ↓";
}

function shortActions(actions) {
  if (actions.length <= 2) return actionsText(actions);
  const head = actionsText(actions.slice(0, 2));
  const rest = actionsText(actions.slice(2));
  return `${head}<details><summary>詳細</summary><div>${rest}</div></details>`;
}

function renderVideos() {
  const filters = currentFilters();
  const filtered = applyFilters(state.diagnosed, filters);
  const rows = filtered
    .map((v) => `
      <tr>
        <td>${v.videoId}</td>
        <td>${v.title}</td>
        <td>${v.author}</td>
        <td>${v.series}</td>
        <td>${v.publishedAt}</td>
        <td>${fmtInt(v.views)}</td>
        <td>${fmtInt(v.estimatedMinutesWatched)}分</td>
        <td>${fmtDurationSec(v.averageViewDuration)}</td>
        <td>${fmtInt(v.impressions)}</td>
        <td>${fmtPct(toCtrPercent(v.impressionCtr))}</td>
        <td>${fmtDurationSec(v.durationSeconds)}</td>
        <td>${v.isShortCandidate}</td>
        <td>${v.formatType}</td>
        <td>${v.hasDescriptionSynopsis}</td>
        <td>${v.hasDescriptionCharacters}</td>
        <td>${v.hasDescriptionGlossary}</td>
        <td>${tagsHtml(v.diagnosisTags)}</td>
        <td>${shortActions(v.recommendedActions)}</td>
      </tr>`).join("");

  const authors = buildFilterOptions(state.diagnosed, "author");
  const series = buildFilterOptions(state.diagnosed, "series");
  const tags = ["すべて", ...new Set(state.diagnosed.flatMap((v) => v.diagnosisTags))];
  const playlists = buildFilterOptions(state.diagnosed, "playlistName");
  const select = (id, options, current) =>
    `<select id="${id}">${options.map((o) => `<option ${o === current ? "selected" : ""}>${o}</option>`).join("")}</select>`;

  document.querySelector("#videos").innerHTML = `
    <div class="filters">
      <label>作家 ${select("filterAuthor", authors, filters.author)}</label>
      <label>シリーズ ${select("filterSeries", series, filters.series)}</label>
      <label>再生リスト ${select("filterPlaylist", playlists, filters.playlist)}</label>
      <label>診断タグ ${select("filterTag", tags, filters.tag)}</label>
      <label>動画種別 ${select("filterType", ["すべて", "通常動画のみ", "Short候補のみ", "再生リストのみ", "Podcastのみ", "ライブ動画のみ"], filters.type)}</label>
      <label>概要欄不足 ${select("filterDescMissing", ["すべて", "あり", "なし"], filters.descMissing)}</label>
      <label>並び順 ${select("filterSort", ["総再生時間順", "表示回数順", "CTR順", "平均視聴時間順", "公開日順"], filters.sort)}</label>
    </div>
    <p class="note">表示件数: ${filtered.length} / ${state.diagnosed.length}</p>
    ${tableShell(rows)}
  `;
  document.querySelectorAll("#videos select").forEach((s) => s.addEventListener("change", () => {
    state.filteredTag = document.querySelector("#filterTag")?.value || "すべて";
    state.focusedSeries = document.querySelector("#filterSeries")?.value || "すべて";
    state.focusedPlaylist = document.querySelector("#filterPlaylist")?.value || "すべて";
    state.sortMetric = null;
    renderVideos();
  }));

  document.querySelectorAll("#videos [data-sort]").forEach((h) => {
    h.addEventListener("click", () => {
      const metric = h.dataset.sort;
      if (state.sortMetric === metric) {
        state.sortDir = state.sortDir === "desc" ? "asc" : "desc";
      } else {
        state.sortMetric = metric;
        state.sortDir = "desc";
      }
      renderVideos();
    });
  });
}

function renderPlaylistSplit() {
  const rows = groupBy(state.diagnosed, "playlistName").sort((a, b) => b.totalWatched - a.totalWatched);
  document.querySelector("#playlist").innerHTML = `
    <h2>再生リスト別切り替え</h2>
    <p class="note">再生リストごとの実績を確認し、ワンクリックで動画診断へ切り替えできます。</p>
    <div class="series-grid">
      ${rows.map((r) => `
        <article class="card series-card">
          <h3>${r.label}</h3>
          <p>本数: ${fmtInt(r.count)}本</p>
          <p>総再生数: ${fmtInt(r.totalViews)}</p>
          <p>総再生時間: ${fmtInt(r.totalWatched)}分</p>
          <p>平均CTR: ${fmtPct(r.avgCtr)}</p>
          <p>平均視聴時間: ${fmtDurationSec(r.avgViewDuration)}</p>
          <button data-playlist-filter="${r.label}">この再生リストで動画診断</button>
        </article>
      `).join("")}
    </div>
  `;

  document.querySelectorAll("[data-playlist-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.focusedPlaylist = btn.dataset.playlistFilter || "すべて";
      state.focusedSeries = "すべて";
      state.filteredTag = "すべて";
      state.sortMetric = null;
      document.querySelector('[data-tab="videos"]').click();
      renderVideos();
    });
  });
}

function renderSeriesSplit() {
  const seriesRows = groupBy(state.diagnosed, "series").sort((a, b) => b.totalWatched - a.totalWatched);
  document.querySelector("#series").innerHTML = `
    <h2>シリーズ分割</h2>
    <p class="note">シリーズごとの本数・視聴規模を比較し、動画診断へ絞り込みできます。</p>
    <div class="series-grid">
      ${seriesRows.map((r) => `
        <article class="card series-card">
          <h3>${r.label}</h3>
          <p>本数: ${fmtInt(r.count)}本</p>
          <p>総再生数: ${fmtInt(r.totalViews)}</p>
          <p>総再生時間: ${fmtInt(r.totalWatched)}分</p>
          <p>平均CTR: ${fmtPct(r.avgCtr)}</p>
          <p>平均視聴時間: ${fmtDurationSec(r.avgViewDuration)}</p>
          <p>総集編候補: ${fmtInt(r.anthologyCandidates)}本</p>
          <button data-series-filter="${r.label}">このシリーズで動画診断</button>
        </article>
      `).join("")}
    </div>
  `;

  document.querySelectorAll("[data-series-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.focusedSeries = btn.dataset.seriesFilter || "すべて";
      state.focusedPlaylist = "すべて";
      state.filteredTag = "すべて";
      state.sortMetric = null;
      document.querySelector('[data-tab="videos"]').click();
      renderVideos();
    });
  });
}

function tableShell(rows) {
  return `<div class="table-wrap"><table><thead><tr>
    <th>動画ID</th><th>タイトル</th><th>作家</th><th>シリーズ</th><th>公開日</th>
    <th data-sort="views" class="sort">再生数${sortIndicator("views")}</th>
    <th data-sort="watched" class="sort">総再生時間（分）${sortIndicator("watched")}</th>
    <th data-sort="avgView" class="sort">平均視聴時間${sortIndicator("avgView")}</th>
    <th data-sort="impressions" class="sort">表示回数${sortIndicator("impressions")}</th>
    <th data-sort="ctr" class="sort">CTR${sortIndicator("ctr")}</th>
    <th data-sort="duration" class="sort">動画尺${sortIndicator("duration")}</th>
    <th>Short候補</th><th>動画種別</th><th>あらすじ</th><th>登場人物</th><th>用語集</th><th>診断タグ</th><th>推奨アクション</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderFiltered() {
  const hidden = state.diagnosed.filter((v) => v.diagnosisTags.includes("隠れ名作"));
  const thumb = state.diagnosed.filter((v) => v.diagnosisTags.includes("サムネ改善候補"));
  const desc = state.diagnosed.filter((v) => v.diagnosisTags.includes("概要欄補強候補"));
  const anthology = state.diagnosed.filter((v) => v.diagnosisTags.includes("総集編候補"));
  document.querySelector("#hidden").innerHTML = sectionRows(hidden);
  document.querySelector("#thumb").innerHTML = sectionRows(thumb);
  document.querySelector("#desc").innerHTML = sectionRows(desc);
  document.querySelector("#anthology").innerHTML = sectionRows(anthology);
}

function sectionRows(items) {
  const rows = items.map((v) => `
    <tr><td>${v.videoId}</td><td>${v.title}</td><td>${v.author}</td><td>${v.series}</td>
    <td>${fmtInt(v.views)}</td><td>${fmtInt(v.estimatedMinutesWatched)}分</td>
    <td>${fmtPct(toCtrPercent(v.impressionCtr))}</td>
    <td>${tagsHtml(v.diagnosisTags)}</td><td>${shortActions(v.recommendedActions)}</td></tr>`).join("");
  return `<p class="note">件数: ${items.length}</p><div class="table-wrap"><table><thead><tr>
    <th>動画ID</th><th>タイトル</th><th>作家</th><th>シリーズ</th><th>再生数</th><th>総再生時間（分）</th><th>CTR</th><th>診断タグ</th><th>推奨アクション</th>
  </tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderAuthorSeries() {
  const author = groupBy(state.diagnosed, "author");
  const series = groupBy(state.diagnosed, "series");
  const draw = (items, label) => `<h3>${label}</h3><div class="table-wrap"><table><thead><tr>
    <th>${label}</th><th>本数</th><th>総再生時間</th><th>平均CTR</th><th>平均視聴時間</th><th>総集編候補</th>
  </tr></thead><tbody>${
    items.map((r) => `<tr><td>${r.label}</td><td>${r.count}</td><td>${fmt(r.totalWatched)}</td><td>${fmt(r.avgCtr)}</td><td>${fmt(r.avgViewDuration)}</td><td>${r.anthologyCandidates}</td></tr>`).join("")
  }</tbody></table></div>`;
  document.querySelector("#author").innerHTML = `${draw(author, "作家")}<br/>${draw(series, "シリーズ")}`;
}

function triggerDownload(name, text, type = "text/csv") {
  const blob = new Blob([text], { type: `${type};charset=utf-8` });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function exportRows(filterFn) {
  return state.diagnosed.filter(filterFn).map((v) => ({
    videoId: v.videoId,
    title: v.title,
    author: v.author,
    series: v.series,
    views: v.views,
    estimatedMinutesWatched: v.estimatedMinutesWatched,
    averageViewDuration: v.averageViewDuration,
    impressions: v.impressions,
    impressionCtr: v.impressionCtr,
    diagnosisTags: v.diagnosisTags.join("|"),
    recommendedActions: v.recommendedActions.join("|"),
    anthologySeedScore: v.anthologySeedScore,
  }));
}

function renderExport() {
  const defs = [
    ["hidden_gems.csv", "隠れ名作を書き出す", (v) => v.diagnosisTags.includes("隠れ名作")],
    ["thumbnail_fix_candidates.csv", "サムネ改善候補を書き出す", (v) => v.diagnosisTags.includes("サムネ改善候補")],
    ["description_audit_candidates.csv", "概要欄補強候補を書き出す", (v) => v.diagnosisTags.includes("概要欄補強候補")],
    ["anthology_seed_candidates.csv", "総集編候補を書き出す", (v) => v.diagnosisTags.includes("総集編候補")],
    ["x_repost_candidates.csv", "X再投稿候補を書き出す", (v) => v.diagnosisTags.includes("X再投稿候補")],
  ];
  const headers = [
    "videoId", "title", "author", "series", "views", "estimatedMinutesWatched", "averageViewDuration",
    "impressions", "impressionCtr", "diagnosisTags", "recommendedActions", "anthologySeedScore",
  ];
  document.querySelector("#export").innerHTML = `
    <div class="export-list">
      ${defs.map(([name, label, fn]) => `<article class="card"><h3>${name}</h3>
      <p>${exportRows(fn).length} rows</p>
      <button data-export="${name}">${label}</button>
      <button data-json="${name.replace(".csv", ".json")}">JSONを書き出す</button></article>`).join("")}
    </div>`;

  document.querySelectorAll("[data-export]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.export;
      const def = defs.find(([n]) => n === name);
      const rows = exportRows(def[2]);
      triggerDownload(name, toCsv(rows, headers), "text/csv");
    });
  });
  document.querySelectorAll("[data-json]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const jsonName = btn.dataset.json;
      const csvName = jsonName.replace(".json", ".csv");
      const def = defs.find(([n]) => n === csvName);
      const rows = exportRows(def[2]);
      triggerDownload(jsonName, JSON.stringify(rows, null, 2), "application/json");
    });
  });
}

function renderAll() {
  renderOverview();
  renderVideos();
  renderSeriesSplit();
  renderPlaylistSplit();
  renderFiltered();
  renderAuthorSeries();
  renderExport();
}

async function loadCsvText(text) {
  state.videos = parseCsv(text).map(normalizeVideo);
  state.diagnosed = runDiagnosis(state.videos);
  updateChannelLabel();
  renderAll();
}

function setLastLoaded(name) {
  localStorage.setItem(LAST_LOADED_KEY, name);
  document.querySelector("#lastLoaded").textContent = `前回読み込んだファイル: ${name}`;
}

function restoreLastLoaded() {
  const last = localStorage.getItem(LAST_LOADED_KEY);
  if (last) {
    document.querySelector("#lastLoaded").textContent = `前回読み込んだファイル: ${last}`;
  }
}

async function loadPreset(path, label, options = {}) {
  const { silent = false } = options;
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error("fetch failed");
    const text = await res.text();
    await loadCsvText(text);
    setLastLoaded(label);
  } catch (e) {
    if (!silent) {
      alert("固定パスの読み込みに失敗しました。file:// では制限される場合があります。CSVファイル選択で読み込んでください。");
    }
    throw e;
  }
}

function updateChannelLabel() {
  document.querySelector("#currentChannel").textContent = `現在: ${state.channelName}`;
}

async function switchChannel(path, label, name) {
  state.channelName = name;
  await loadPreset(path, label);
}

async function switchChannelWithFallback(primaryPath, primaryLabel, fallbackPath, fallbackLabel, name) {
  state.channelName = name;
  try {
    await loadPreset(primaryPath, primaryLabel, { silent: true });
  } catch (e) {
    await loadPreset(fallbackPath, fallbackLabel, { silent: false });
  }
}

document.querySelector("#allCsv").addEventListener("change", async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  const txt = await f.text();
  await loadCsvText(txt);
  setLastLoaded(f.name);
});

document.querySelector("#loadSample").addEventListener("click", async () => {
  await loadPreset(PRESETS.sample, "ninjo_channel_report/youtube_video_report_last_90_days_all_videos.csv");
});
document.querySelector("#loadPresetAnalysisReady").addEventListener("click", async () => {
  await loadPreset(PRESETS.analysisReady, "ninjo_channel_report/analysis_ready_normal_video.csv");
});
document.querySelector("#loadPresetAll").addEventListener("click", async () => loadPreset(PRESETS.all, PRESETS.all));
document.querySelector("#loadPresetNormal").addEventListener("click", async () => loadPreset(PRESETS.normal, PRESETS.normal));
document.querySelector("#loadPresetShort").addEventListener("click", async () => loadPreset(PRESETS.short, PRESETS.short));
document.querySelector("#loadPresetInventory").addEventListener("click", async () => loadPreset(PRESETS.inventory, PRESETS.inventory));
document.querySelector("#loadPresetAuthor").addEventListener("click", async () => loadPreset(PRESETS.author, PRESETS.author));
document.querySelector("#switchTorimono").addEventListener("click", async () => {
  await switchChannelWithFallback(
    PRESETS.analysisReadyTorimono,
    "old_channel_report/analysis_ready_normal_video.csv",
    PRESETS.torimono,
    "old_channel_report/youtube_video_report_last_90_days_all_videos.csv",
    "捕物朗読チャンネル"
  );
});
document.querySelector("#switchNinjo").addEventListener("click", async () => {
  await switchChannelWithFallback(
    PRESETS.analysisReadyNinjo,
    "ninjo_channel_report/analysis_ready_normal_video.csv",
    PRESETS.ninjoDirect,
    "ninjo_channel_report/youtube_video_report_last_90_days_all_videos.csv",
    "人情朗読チャンネル"
  );
});

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.querySelector(`#${btn.dataset.tab}`).classList.add("active");
  });
});

restoreLastLoaded();

const isLocalhost = location.protocol.startsWith("http") && ["localhost", "127.0.0.1"].includes(location.hostname);
if (isLocalhost) {
  switchChannelWithFallback(
    PRESETS.analysisReadyNinjo,
    "ninjo_channel_report/analysis_ready_normal_video.csv",
    PRESETS.all,
    PRESETS.all,
    "固定パス（Podcast対応）"
  );
}
