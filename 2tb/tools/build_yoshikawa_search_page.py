#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
CATALOG_PATH = REPORTS_DIR / "yoshikawa_works_catalog.csv"
SEED_PATH = REPORTS_DIR / "yoshikawa_seed_shortworks.csv"
OUT_PATH = REPORTS_DIR / "yoshikawa_search.html"


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_payload() -> dict[str, object]:
    works = load_csv_rows(CATALOG_PATH)
    seeds = load_csv_rows(SEED_PATH)
    genres = sorted({str(row.get("primary_genre", "")).strip() for row in works if str(row.get("primary_genre", "")).strip()})
    eras = sorted({str(row.get("primary_era", "")).strip() for row in works if str(row.get("primary_era", "")).strip()})
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "works": works,
        "seeds": seeds,
        "genres": genres,
        "eras": eras,
    }


def render_html(payload: dict[str, object]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    html = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>吉川英治 Search</title>
  <style>
    :root {
      --bg: #f5efe4;
      --panel: rgba(255, 251, 245, 0.92);
      --panel-2: rgba(252, 246, 237, 0.98);
      --text: #2a2118;
      --muted: #6a5746;
      --border: rgba(122, 84, 48, 0.18);
      --accent: #8b3a2e;
      --accent-2: #c97b3d;
      --good: #226c49;
      --shadow: 0 18px 44px rgba(82, 54, 23, 0.12);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Hiragino Mincho ProN", "Yu Mincho", serif; background: radial-gradient(circle at top left, #fff7eb, #f3eadb 55%, #eadbc2 100%); color: var(--text); }
    .page { max-width: 1400px; margin: 0 auto; padding: 28px; }
    .hero { background: linear-gradient(135deg, rgba(139,58,46,0.95), rgba(201,123,61,0.88)); color: #fff9f2; border-radius: 28px; padding: 28px; box-shadow: var(--shadow); position: relative; overflow: hidden; }
    .hero::after { content: ""; position: absolute; inset: auto -80px -120px auto; width: 240px; height: 240px; border-radius: 50%; background: rgba(255,255,255,0.09); }
    .hero h1 { margin: 0 0 8px; font-size: 34px; }
    .hero p { margin: 0; max-width: 860px; line-height: 1.8; color: rgba(255,249,242,0.9); }
    .meta-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-top: 20px; }
    .meta-card { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.16); border-radius: 18px; padding: 14px 16px; }
    .meta-card strong { display: block; font-size: 22px; margin-bottom: 4px; }
    .layout { display: grid; grid-template-columns: 340px 1fr; gap: 20px; margin-top: 22px; }
    .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 24px; box-shadow: var(--shadow); }
    .sidebar { padding: 18px; position: sticky; top: 18px; height: fit-content; }
    .section-title { font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }
    .control { display: grid; gap: 8px; margin-bottom: 16px; }
    .control input, .control select { width: 100%; border: 1px solid var(--border); background: #fffdf9; border-radius: 14px; padding: 11px 12px; font: inherit; color: var(--text); }
    .checkline { display: flex; gap: 8px; align-items: center; font-size: 14px; color: var(--muted); margin-bottom: 8px; }
    .content { display: grid; gap: 20px; }
    .seed-panel, .works-panel { padding: 18px; }
    .seed-list { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; }
    .seed-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 20px; padding: 16px; display: grid; gap: 10px; }
    .seed-rank { color: var(--accent); font-weight: 700; font-size: 24px; }
    .seed-card h3 { margin: 0; font-size: 22px; line-height: 1.35; }
    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .badge { border-radius: 999px; padding: 5px 10px; font-size: 12px; background: rgba(201,123,61,0.12); color: #75431a; border: 1px solid rgba(201,123,61,0.18); }
    .badge.good { background: rgba(34,108,73,0.12); color: var(--good); border-color: rgba(34,108,73,0.2); }
    .seed-links { display: flex; flex-wrap: wrap; gap: 8px; }
    .seed-links a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(139,58,46,0.25); }
    .works-toolbar { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; margin-bottom: 12px; }
    .works-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; }
    .work-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 20px; padding: 16px; display: grid; gap: 10px; }
    .work-card h3 { margin: 0; font-size: 21px; line-height: 1.35; }
    .meta-line { color: var(--muted); font-size: 14px; line-height: 1.6; }
    .summary { font-size: 14px; line-height: 1.7; color: var(--muted); }
    .empty { padding: 18px; border-radius: 18px; border: 1px dashed var(--border); color: var(--muted); background: rgba(255,255,255,0.46); }
    .footer { margin-top: 18px; color: var(--muted); font-size: 12px; text-align: right; }
    @media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } .sidebar { position: static; } }
    @media (max-width: 800px) { .meta-grid, .seed-list, .works-grid { grid-template-columns: 1fr; } .page { padding: 16px; } .hero h1 { font-size: 28px; } }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>吉川英治 Catalog Search</h1>
      <p>catalog・seed shortworks・候補レビューを一画面で見比べるためのローカル検索ページです。シリーズ、短編、本文の有無、短尺候補レポート掲載状況で絞り込みできます。</p>
      <div class="meta-grid">
        <div class="meta-card"><strong id="metaWorks">0</strong><span>works</span></div>
        <div class="meta-card"><strong id="metaSeeds">0</strong><span>seed rows</span></div>
        <div class="meta-card"><strong id="metaTexts">0</strong><span>local texts</span></div>
        <div class="meta-card"><strong id="metaPriority">0</strong><span>report priority</span></div>
      </div>
    </section>
    <div class="layout">
      <aside class="panel sidebar">
        <div class="section-title">Filters</div>
        <label class="control">
          <span>検索</span>
          <input id="queryInput" type="search" placeholder="作品名・代表表記・メモ" />
        </label>
        <label class="control">
          <span>種別</span>
          <select id="typeFilter">
            <option value="">すべて</option>
            <option value="シリーズ">シリーズ</option>
            <option value="単発">単発</option>
          </select>
        </label>
        <label class="control">
          <span>主ジャンル</span>
          <select id="genreFilter"><option value="">すべて</option></select>
        </label>
        <label class="control">
          <span>主時代</span>
          <select id="eraFilter"><option value="">すべて</option></select>
        </label>
        <label class="checkline"><input id="priorityOnly" type="checkbox" />短尺候補レポートありだけ</label>
        <label class="checkline"><input id="textOnly" type="checkbox" />ローカル本文ありだけ</label>
      </aside>
      <main class="content">
        <section class="panel seed-panel">
          <div class="works-toolbar">
            <div>
              <div class="section-title">Seed Shortworks</div>
              <div class="meta-line" id="seedSummary"></div>
            </div>
          </div>
          <div id="seedList" class="seed-list"></div>
        </section>
        <section class="panel works-panel">
          <div class="works-toolbar">
            <div>
              <div class="section-title">Works</div>
              <div class="meta-line" id="worksSummary"></div>
            </div>
          </div>
          <div id="worksGrid" class="works-grid"></div>
        </section>
      </main>
    </div>
    <div class="footer">Generated at __GENERATED_AT__ / source: __CATALOG_NAME__ + __SEED_NAME__</div>
  </div>
  <script>
    const APP_DATA = __DATA_JSON__;
    const works = Array.isArray(APP_DATA.works) ? APP_DATA.works : [];
    const seeds = Array.isArray(APP_DATA.seeds) ? APP_DATA.seeds : [];
    const els = {
      metaWorks: document.getElementById('metaWorks'),
      metaSeeds: document.getElementById('metaSeeds'),
      metaTexts: document.getElementById('metaTexts'),
      metaPriority: document.getElementById('metaPriority'),
      queryInput: document.getElementById('queryInput'),
      typeFilter: document.getElementById('typeFilter'),
      genreFilter: document.getElementById('genreFilter'),
      eraFilter: document.getElementById('eraFilter'),
      priorityOnly: document.getElementById('priorityOnly'),
      textOnly: document.getElementById('textOnly'),
      seedSummary: document.getElementById('seedSummary'),
      seedList: document.getElementById('seedList'),
      worksSummary: document.getElementById('worksSummary'),
      worksGrid: document.getElementById('worksGrid'),
    };

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }

    function populateSelect(select, values) {
      values.forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
    }

    function workMatches(row) {
      const query = String(els.queryInput.value || '').trim().toLowerCase();
      const haystack = [row.title, row.representative_clean_titles, row.normalization_note].join(' ').toLowerCase();
      if (query && !haystack.includes(query)) return false;
      if (els.typeFilter.value && row.work_type !== els.typeFilter.value) return false;
      if (els.genreFilter.value && row.primary_genre !== els.genreFilter.value) return false;
      if (els.eraFilter.value && row.primary_era !== els.eraFilter.value) return false;
      if (els.priorityOnly.checked && row.report_priority !== 'yes') return false;
      if (els.textOnly.checked && row.has_local_text !== 'yes') return false;
      return true;
    }

    function renderSeedCard(row) {
      const badges = [
        `<span class="badge">score ${escapeHtml(row.seed_score)}</span>`,
        `<span class="badge">${escapeHtml(row.work_type || '-')}</span>`,
        `<span class="badge">videos ${escapeHtml(row.video_count || '0')}</span>`,
        row.has_local_text === 'yes' ? `<span class="badge good">本文あり</span>` : '',
        row.report_priority === 'yes' ? `<span class="badge good">report優先</span>` : '',
      ].filter(Boolean).join('');
      const links = [
        row.candidate_csv ? `<a href="${escapeHtml(row.candidate_csv)}">candidate csv</a>` : '',
        row.review_md ? `<a href="${escapeHtml(row.review_md)}">review md</a>` : '',
      ].filter(Boolean).join('');
      return `
        <article class="seed-card">
          <div class="seed-rank">#${escapeHtml(row.rank || '-')}</div>
          <h3>${escapeHtml(row.seed_title || '')}</h3>
          <div class="badge-row">${badges}</div>
          <div class="meta-line">${escapeHtml(row.primary_genre || '不明')} / ${escapeHtml(row.primary_era || '不明')} / ${escapeHtml(row.first_published || '-')} - ${escapeHtml(row.last_published || '-')}</div>
          <div class="seed-links">${links}</div>
        </article>`;
    }

    function renderWorkCard(row) {
      const badges = [
        `<span class="badge">${escapeHtml(row.work_type || '-')}</span>`,
        `<span class="badge">videos ${escapeHtml(row.video_count || '0')}</span>`,
        row.report_priority === 'yes' ? `<span class="badge good">report優先</span>` : '',
        row.has_local_text === 'yes' ? `<span class="badge good">本文 ${escapeHtml(row.local_text_count || '0')}件</span>` : '',
      ].filter(Boolean).join('');
      return `
        <article class="work-card">
          <h3>${escapeHtml(row.title || '')}</h3>
          <div class="badge-row">${badges}</div>
          <div class="meta-line">${escapeHtml(row.primary_genre || '不明')} / ${escapeHtml(row.primary_era || '不明')}</div>
          <div class="meta-line">${escapeHtml(row.first_published || '-')} - ${escapeHtml(row.last_published || '-')}</div>
          <div class="summary">${escapeHtml(row.representative_clean_titles || '')}</div>
          ${row.local_text_paths ? `<div class="meta-line">text: ${escapeHtml(row.local_text_paths)}</div>` : ''}
          ${row.normalization_note ? `<div class="meta-line">note: ${escapeHtml(row.normalization_note)}</div>` : ''}
        </article>`;
    }

    function renderSeeds() {
      els.seedSummary.textContent = `${seeds.length}件 / 先頭 seed は ${seeds[0] ? seeds[0].seed_title : 'なし'}`;
      els.seedList.innerHTML = seeds.length ? seeds.map(renderSeedCard).join('') : '<div class="empty">seed summary はまだありません。</div>';
    }

    function renderWorks() {
      const filtered = works.filter(workMatches);
      els.worksSummary.textContent = `${filtered.length} / ${works.length}件表示`;
      els.worksGrid.innerHTML = filtered.length ? filtered.map(renderWorkCard).join('') : '<div class="empty">条件に一致する作品がありません。</div>';
    }

    function renderMeta() {
      els.metaWorks.textContent = String(works.length);
      els.metaSeeds.textContent = String(seeds.length);
      els.metaTexts.textContent = String(works.filter((row) => row.has_local_text === 'yes').length);
      els.metaPriority.textContent = String(works.filter((row) => row.report_priority === 'yes').length);
    }

    populateSelect(els.genreFilter, Array.isArray(APP_DATA.genres) ? APP_DATA.genres : []);
    populateSelect(els.eraFilter, Array.isArray(APP_DATA.eras) ? APP_DATA.eras : []);
    [els.queryInput, els.typeFilter, els.genreFilter, els.eraFilter, els.priorityOnly, els.textOnly].forEach((el) => el.addEventListener('input', renderWorks));
    renderMeta();
    renderSeeds();
    renderWorks();
  </script>
</body>
</html>
"""
    return (
        html.replace("__DATA_JSON__", data_json)
        .replace("__GENERATED_AT__", escape(str(payload["generated_at"])))
        .replace("__CATALOG_NAME__", escape(CATALOG_PATH.name))
        .replace("__SEED_NAME__", escape(SEED_PATH.name))
    )


def main() -> int:
    payload = build_payload()
    OUT_PATH.write_text(render_html(payload), encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())