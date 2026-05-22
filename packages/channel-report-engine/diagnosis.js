const AUTHOR_PATTERNS = [
  ["野村胡堂", /野村胡堂|銭形平次/],
  ["納言恭平", /納言恭平|七之助/],
  ["山本周五郎", /山本周五郎/],
  ["吉川英治", /吉川英治|新書太閤記/],
  ["芥川龍之介", /芥川龍之介/],
  ["島崎藤村", /島崎藤村|夜明け前/],
  ["江戸川乱歩", /江戸川乱歩/],
];

const SERIES_PATTERNS = [
  ["銭形平次捕物控", /銭形平次/],
  ["七之助捕物帳", /七之助/],
  ["山本周五郎アワー", /山本周五郎/],
  ["新書太閤記", /新書太閤記/],
  ["夜明け前", /夜明け前/],
];

const PLAYLIST_PATTERNS = [
  ["銭形平次捕物控", /銭形平次/],
  ["七之助捕物帳", /七之助/],
  ["山本周五郎朗読", /山本周五郎/],
  ["吉川英治朗読", /吉川英治|新書太閤記/],
  ["怪談・ミステリー", /怪談|ミステリー|謎|怪事件/],
  ["睡眠・作業用", /睡眠|作業用/],
  ["総集編", /総集編|傑作選|まとめ|第一集|第二集|第三集/],
];

function detectAuthor(title) {
  for (const [name, re] of AUTHOR_PATTERNS) {
    if (re.test(title)) return name;
  }
  return "不明";
}

function detectSeries(title) {
  for (const [name, re] of SERIES_PATTERNS) {
    if (re.test(title)) return name;
  }
  return "その他";
}

function detectPlaylistName(row, title) {
  const explicit = row.playlist_title || row.playlistTitle || row.playlist_name || row.playlistName;
  if (explicit && String(explicit).trim()) return String(explicit).trim();
  for (const [name, re] of PLAYLIST_PATTERNS) {
    if (re.test(title)) return name;
  }
  return "未分類";
}

function round(value, digits = 2) {
  const p = 10 ** digits;
  return Math.round(value * p) / p;
}

function detectFormatType(row, title, isShort) {
  const bucket = String(row.content_type_bucket || "").toLowerCase();
  const liveFlag = String(row["snippet.liveBroadcastContent"] || "").toLowerCase();
  const videoFormat = String(row.video_format || row.videoFormat || "").toLowerCase();
  const seriesSub = String(row.series_sub || row.seriesSub || "").toLowerCase();
  const liveOrOnDemand = String(row.live_or_on_demand || row.liveOrOnDemand || "").toLowerCase();

  if (videoFormat.includes("podcast") || seriesSub.includes("podcast")) {
    return "Podcast";
  }
  if (videoFormat.includes("聴くドラマ") || videoFormat.includes("一人でドラマ")) {
    return "Podcast";
  }
  if (liveOrOnDemand === "live") {
    return "ライブ動画";
  }
  if (liveFlag === "live" || liveFlag === "upcoming" || bucket === "live_related" || /ライブ|生配信/.test(title)) {
    return "ライブ動画";
  }
  if (/podcast|ポッドキャスト|ラジオ|トーク/.test(title)) {
    return "Podcast";
  }
  if (/再生リスト|playlist/.test(title)) {
    return "再生リスト";
  }
  if (/総集編|傑作選|まとめ|第一集|第二集|第三集/.test(title)) {
    return "再生リスト";
  }
  if (isShort || bucket === "short_candidate") {
    return "Short";
  }
  return "通常動画";
}

function normalizeVideo(row) {
  const title = row.title || "";
  const views = Number(row.views || 0);
  const minutes = Number(row.estimatedMinutesWatched || 0);
  const avgViewDuration = Number(row.averageViewDuration || 0);
  const impressions = Number(row.impressions || 0);
  const impressionCtr = Number(row.impressionCtr || 0);
  const durationSeconds = Number(row.duration_seconds || 0);
  const isShort = String(row.is_short_candidate).toLowerCase() === "true";
  const hasSynopsis = String(row.has_description_synopsis).toLowerCase() === "true";
  const hasCharacters = String(row.has_description_characters).toLowerCase() === "true";
  const hasGlossary = String(row.has_description_glossary).toLowerCase() === "true";
  const privacy = String(row.status?.privacyStatus || row["status.privacyStatus"] || "").toLowerCase();
  const retention = durationSeconds > 0 ? avgViewDuration / durationSeconds : 0;
  const formatType = detectFormatType(row, title, isShort);
  const playlistName = detectPlaylistName(row, title);

  return {
    videoId: row.videoId || "",
    title,
    description: row.description || "",
    author: detectAuthor(title),
    series: detectSeries(title),
    publishedAt: row.publishedAt || "",
    views,
    estimatedMinutesWatched: minutes,
    averageViewDuration: avgViewDuration,
    averageViewDurationRatio: retention,
    impressions,
    impressionCtr,
    durationSeconds,
    isShortCandidate: isShort,
    formatType,
    playlistName,
    isPublic: privacy === "public" || String(row.is_public).toLowerCase() === "true",
    isUnlisted: privacy === "unlisted" || String(row.is_unlisted).toLowerCase() === "true",
    isPrivate: privacy === "private" || String(row.is_private).toLowerCase() === "true",
    contentTypeBucket: row.content_type_bucket || "",
    hasDescriptionSynopsis: hasSynopsis,
    hasDescriptionCharacters: hasCharacters,
    hasDescriptionGlossary: hasGlossary,
    diagnosisTags: [],
    recommendedActions: [],
  };
}

function pushUnique(list, value) {
  if (!list.includes(value)) list.push(value);
}

function runDiagnosis(videos) {
  const impressionValues = videos.map((v) => v.impressions).filter((v) => v > 0).sort((a, b) => a - b);
  const highImpression = impressionValues[Math.floor(impressionValues.length * 0.75)] || 0;
  const lowImpression = impressionValues[Math.floor(impressionValues.length * 0.25)] || 0;

  return videos.map((v) => {
    const tags = [];
    const actions = [];
    const ctrPercent = v.impressionCtr > 0 && v.impressionCtr <= 1 ? v.impressionCtr * 100 : v.impressionCtr;
    const watchPerImpression = v.impressions > 0 ? v.estimatedMinutesWatched / v.impressions : 0;

    if (ctrPercent >= 7 && v.averageViewDurationRatio >= 0.4 && v.impressions > 0 && v.impressions <= lowImpression) {
      pushUnique(tags, "隠れ名作");
      pushUnique(actions, "X再投稿");
      pushUnique(actions, "固定コメントで再誘導");
    }
    if (v.impressions >= highImpression && ctrPercent > 0 && ctrPercent < 4) {
      pushUnique(tags, "サムネ改善候補");
      pushUnique(tags, "タイトル改善候補");
      pushUnique(actions, "サムネ差し替え");
      pushUnique(actions, "タイトル再設計");
    }
    if (!v.isShortCandidate && v.estimatedMinutesWatched >= 3000) {
      pushUnique(tags, "総集編候補");
      pushUnique(actions, "総集編シードに追加");
    }
    if (v.averageViewDuration >= 1200) {
      pushUnique(tags, "長尺適性");
      pushUnique(actions, "長尺枠で再編集");
    }
    if (v.isShortCandidate) {
      pushUnique(tags, "Short除外");
    }
    if (ctrPercent >= 6 || watchPerImpression >= 0.8) {
      pushUnique(tags, "X再投稿候補");
      pushUnique(actions, "X投稿ドラフト生成");
    }
    if (!v.hasDescriptionSynopsis || !v.hasDescriptionCharacters || !v.hasDescriptionGlossary) {
      pushUnique(tags, "概要欄補強候補");
      pushUnique(actions, "説明欄テンプレ補完");
    }
    if (v.isPrivate || v.isUnlisted) {
      pushUnique(tags, "メンバー限定注意");
    }
    if (v.impressions > 0 && ctrPercent >= 5 && v.averageViewDurationRatio >= 0.25) {
      pushUnique(tags, "検索強化候補");
      pushUnique(actions, "概要欄SEO補強");
    }

    const score =
      v.estimatedMinutesWatched * 0.4 +
      v.views * 0.2 +
      (ctrPercent || 0) * 30 +
      v.averageViewDuration * 0.05 +
      (v.impressions > 0 ? Math.log10(v.impressions + 1) * 20 : 0);

    return {
      ...v,
      diagnosisTags: tags,
      recommendedActions: actions,
      anthologySeedScore: round(score, 2),
    };
  });
}
