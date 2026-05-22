function avg(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function buildOverview(videos) {
  const total = videos.length;
  const normal = videos.filter((v) => v.formatType === "通常動画").length;
  const shorts = videos.filter((v) => v.formatType === "Short").length;
  const playlists = videos.filter((v) => v.formatType === "再生リスト").length;
  const podcasts = videos.filter((v) => v.formatType === "Podcast").length;
  const liveVideos = videos.filter((v) => v.formatType === "ライブ動画").length;
  const publicCount = videos.filter((v) => v.isPublic).length;
  const unlistedCount = videos.filter((v) => v.isUnlisted).length;
  const privateCount = videos.filter((v) => v.isPrivate).length;
  const totalViews = videos.reduce((s, v) => s + v.views, 0);
  const totalWatched = videos.reduce((s, v) => s + v.estimatedMinutesWatched, 0);
  const avgCtr = avg(videos.map((v) => (v.impressionCtr > 0 && v.impressionCtr <= 1 ? v.impressionCtr * 100 : v.impressionCtr)));
  const avgViewDuration = avg(videos.map((v) => v.averageViewDuration));
  const avgRetention = avg(videos.map((v) => v.averageViewDurationRatio * 100));
  const totalImpressions = videos.reduce((s, v) => s + v.impressions, 0);
  const descriptionComplete = videos.filter(
    (v) => v.hasDescriptionSynopsis && v.hasDescriptionCharacters && v.hasDescriptionGlossary
  ).length;

  return {
    total,
    normal,
    shorts,
    playlists,
    podcasts,
    liveVideos,
    publicCount,
    unlistedCount,
    privateCount,
    totalViews,
    totalWatched,
    avgCtr,
    avgViewDuration,
    avgRetention,
    totalImpressions,
    descriptionCompleteRate: total ? (descriptionComplete / total) * 100 : 0,
  };
}

function buildFormatBreakdown(videos) {
  const formats = ["通常動画", "Short", "再生リスト", "Podcast", "ライブ動画"];
  return formats.map((name) => {
    const items = videos.filter((v) => v.formatType === name);
    const totalViews = items.reduce((s, v) => s + v.views, 0);
    const totalWatched = items.reduce((s, v) => s + v.estimatedMinutesWatched, 0);
    const avgCtr = avg(items.map((v) => (v.impressionCtr > 0 && v.impressionCtr <= 1 ? v.impressionCtr * 100 : v.impressionCtr)));
    const avgDuration = avg(items.map((v) => v.averageViewDuration));
    return {
      format: name,
      count: items.length,
      totalViews,
      totalWatched,
      avgCtr,
      avgDuration,
    };
  });
}

function groupBy(videos, key) {
  const map = new Map();
  videos.forEach((v) => {
    const k = v[key] || "不明";
    if (!map.has(k)) {
      map.set(k, { key: k, count: 0, views: 0, watched: 0, ctrValues: [], avgDurValues: [], anthologyCandidates: 0 });
    }
    const row = map.get(k);
    row.count += 1;
    row.views += v.views;
    row.watched += v.estimatedMinutesWatched;
    const ctr = v.impressionCtr > 0 && v.impressionCtr <= 1 ? v.impressionCtr * 100 : v.impressionCtr;
    if (ctr > 0) row.ctrValues.push(ctr);
    if (v.averageViewDuration > 0) row.avgDurValues.push(v.averageViewDuration);
    if (v.diagnosisTags.includes("総集編候補")) row.anthologyCandidates += 1;
  });

  return Array.from(map.values())
    .map((r) => ({
      label: r.key,
      count: r.count,
      totalViews: r.views,
      totalWatched: r.watched,
      avgCtr: r.ctrValues.length ? avg(r.ctrValues) : 0,
      avgViewDuration: r.avgDurValues.length ? avg(r.avgDurValues) : 0,
      anthologyCandidates: r.anthologyCandidates,
    }))
    .sort((a, b) => b.totalWatched - a.totalWatched);
}
