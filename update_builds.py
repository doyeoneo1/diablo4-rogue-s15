from __future__ import annotations

import re
import json
import html as htmlmod
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

INDEX = Path("index.html")
KST = timezone(timedelta(hours=9))

SOURCES = {
    "D4Guides": "https://d4guides.gg/en/builds?class=rogue",
    "Mobalytics": "https://mobalytics.gg/diablo-4/rogue-builds",
}

KNOWN = {
    "penshot": (["penetrating shot poison imbuement", "penetrating shot", "꿰뚫는 사격"], "독 주입 꿰뚫는 사격"),
    "rapid": (["rapid fire", "연발 사격"], "냉기 연발 사격"),
    "dok": (["dance of knives", "칼날의 춤"], "독 주입 칼날의 춤"),
    "roa": (["rain of arrows cold imbuement", "rain of arrows", "화살비"], "냉기 화살비"),
    "death": (["death trap", "죽음의 덫"], "죽음의 덫"),
}

EXTRA = {
    "penetrating-shot-cold": (["penetrating shot cold imbuement"], "냉기 주입 꿰뚫는 사격"),
    "twisting-blades": (["twisting blades"], "회전 칼날"),
    "frostbite-trap": (["frostbite trap"], "동상 덫"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; D4RogueDaily/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_text(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)

def norm(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9가-힣+ ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def nearby(text, labels, radius=350):
    t = norm(text)
    for label in labels:
        n = norm(label)
        pos = t.find(n)
        if pos >= 0:
            return t[max(0, pos-radius):pos+radius]
    return ""

def d4_score(text, labels):
    w = nearby(text, labels)
    if not w:
        return 0, "미등재"
    if "s tier" in w:
        return 100, "S-Tier"
    if "a tier" in w:
        return 80, "A-Tier"
    if "b tier" in w:
        return 60, "B-Tier"
    return 50, "등재"

def mob_score(text, labels):
    w = nearby(text, labels, 450)
    if not w:
        return 0, "미등재"
    score = 55
    tags = []
    if "end game" in w or "endgame" in w:
        score += 10
        tags.append("Endgame")
    if "pushing" in w:
        score += 15
        tags.append("Pushing")
    if "the tower" in w:
        score += 12
        tags.append("Tower")
    if "speed farm" in w:
        score += 5
        tags.append("Speed")
    if "verified" in w:
        score += 5
        tags.append("Verified")
    return score, "/".join(tags) if tags else "등재"

def combine(d4, mob):
    if d4 and mob:
        return round(d4 * 0.6 + mob * 0.4)
    if d4:
        return round(d4 * 0.75)
    if mob:
        return round(mob * 0.70)
    return 0

def build_ranking(texts):
    candidates = {}
    for bid, (labels, display) in KNOWN.items():
        candidates[bid] = (labels, display, True)
    for bid, (labels, display) in EXTRA.items():
        candidates[bid] = (labels, display, False)

    rows = []
    for bid, (labels, display, known) in candidates.items():
        ds, dt = d4_score(texts.get("D4Guides", ""), labels)
        ms, mt = mob_score(texts.get("Mobalytics", ""), labels)
        total = combine(ds, ms)
        if total:
            rows.append({
                "id": bid, "display": display, "known": known,
                "score": total, "d4": ds, "d4_tag": dt,
                "mob": ms, "mob_tag": mt
            })
    rows.sort(key=lambda r: (-r["score"], -r["d4"], -r["mob"], r["display"]))
    return rows

def ensure_css(page):
    if ".daily-meta{" in page:
        return page
    css = '''
.daily-meta{margin-top:12px;border:1px solid #45392d;background:linear-gradient(180deg,#151411,#0d0e0d);padding:16px;box-shadow:0 12px 28px rgba(0,0,0,.55)}
.daily-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.daily-rank-card{display:flex;gap:10px;align-items:center;border:1px solid #39332c;background:#10100f;padding:11px}
.daily-rank-no{font-family:Georgia,serif;font-size:24px;color:#b98856;min-width:38px}
.daily-rank-main b{display:block;color:#ded4c7;font-size:13px}
.daily-rank-main small{display:block;color:#a68e72;font-size:10px;margin-top:3px}
.daily-rank-main span{display:block;color:#746f68;font-size:10px;margin-top:3px}
.daily-warning{margin-top:10px;border-left:3px solid #b66b2d;background:#17110c;padding:10px 12px;color:#c9b49d;font-size:11px;line-height:1.6}
.daily-error{margin-top:10px;border-left:3px solid #8e1d18;background:#170d0d;padding:10px 12px;color:#c7a6a0;font-size:11px}
.daily-method{margin-top:10px;color:#716b63;font-size:10px;line-height:1.6}
@media(max-width:560px){.daily-rank-grid{grid-template-columns:1fr}}
'''
    return page.replace("</style>", css + "\n</style>", 1)

def meta_block(rows, errors):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    count = max(5, min(7, len(rows)))
    top = rows[:count]
    cards = []
    for i, r in enumerate(top, 1):
        status = "상세 세팅 보유" if r["known"] else "신규 상위 빌드 감지"
        cards.append(
            '<div class="daily-rank-card">'
            f'<div class="daily-rank-no">#{i}</div>'
            '<div class="daily-rank-main">'
            f'<b>{htmlmod.escape(r["display"])}</b>'
            f'<small>{status} · 자동점수 {r["score"]}</small>'
            f'<span>D4Guides {htmlmod.escape(r["d4_tag"])} · Mobalytics {htmlmod.escape(r["mob_tag"])}</span>'
            '</div></div>'
        )

    new_names = [htmlmod.escape(r["display"]) for r in top if not r["known"]]
    warn = ""
    if new_names:
        warn = (
            '<div class="daily-warning"><b>신규 상위 빌드 감지:</b> '
            + ", ".join(new_names)
            + ' — 무료 자동화는 검증되지 않은 장비/정복자 정보를 임의 생성하지 않습니다. '
              '상세 세팅 추가 전 수동 검증이 필요합니다.</div>'
        )

    err = ""
    if errors:
        err = '<div class="daily-error">수집 오류: ' + " / ".join(htmlmod.escape(x) for x in errors) + '</div>'

    return (
        '<!-- DAILY_META_START -->'
        '<section class="daily-meta">'
        f'<div class="section-head"><h2>오늘의 도적 고점 메타</h2><small>무료 자동 집계 · {now} KST</small></div>'
        f'<div class="daily-rank-grid">{"".join(cards)}</div>'
        f'{warn}{err}'
        '<div class="daily-method">'
        'D4Guides 시즌15 티어와 Mobalytics Endgame/Pushing/Tower 신호를 합산한 무료 자동 지표입니다. '
        '단일 사이트 순위를 그대로 복사하지 않습니다.'
        '</div></section>'
        '<!-- DAILY_META_END -->'
    )

def inject_meta(page, block):
    pat = re.compile(r"<!-- DAILY_META_START -->.*?<!-- DAILY_META_END -->", re.S)
    if pat.search(page):
        return pat.sub(block, page, count=1)
    marker = '<nav class="build-tabs" id="tabs"></nav>'
    if marker not in page:
        raise RuntimeError("메타 섹션 삽입 위치를 찾지 못했습니다.")
    return page.replace(marker, marker + "\n" + block, 1)

def update_badge(page, source_count):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    page = re.sub(r'<span class="pill">자동화 테스트:.*?</span>', '', page, count=1)
    badge = f'<span class="pill">자동 갱신: {now} · 소스 {source_count}/2</span>'
    if re.search(r'<span class="pill">자동 갱신:.*?</span>', page):
        return re.sub(r'<span class="pill">자동 갱신:.*?</span>', badge, page, count=1)
    return page.replace('<div class="meta">', '<div class="meta">' + badge, 1)

def inject_order(page, rows):
    ids = [r["id"] for r in rows if r["known"]]
    if not ids:
        return page

    page = re.sub(r'const dailyOrder=.*?;\n', '', page)
    marker = 'const tabs=document.getElementById("tabs");'
    page = page.replace(marker, 'const dailyOrder=' + json.dumps(ids, ensure_ascii=False) + ';\n' + marker, 1)

    sort_code = '''builds.sort((a,b)=>{
 const ai=dailyOrder.indexOf(a.id), bi=dailyOrder.indexOf(b.id);
 const av=ai<0?999:ai, bv=bi<0?999:bi;
 return av-bv;
});
'''
    if sort_code not in page:
        page = page.replace('builds.forEach((b,i)=>{', sort_code + 'builds.forEach((b,i)=>{', 1)
    return page

def main():
    if not INDEX.exists():
        raise SystemExit("index.html을 찾을 수 없습니다.")

    texts = {}
    errors = []
    for name, url in SOURCES.items():
        try:
            texts[name] = fetch_text(url)
            print(f"[OK] {name}: {len(texts[name])} chars")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
            print(f"[FAIL] {name}: {e}")

    if not texts:
        raise SystemExit("모든 소스 수집 실패. 기존 사이트를 변경하지 않습니다.")

    rows = build_ranking(texts)
    if len(rows) < 5:
        raise SystemExit(f"유효 빌드 {len(rows)}개만 감지됨. 안전을 위해 변경하지 않습니다.")

    page = INDEX.read_text(encoding="utf-8")
    page = ensure_css(page)
    page = inject_meta(page, meta_block(rows, errors))
    page = inject_order(page, rows)
    page = update_badge(page, len(texts))
    INDEX.write_text(page, encoding="utf-8")

    print("=== Daily ranking ===")
    for i, r in enumerate(rows[:7], 1):
        print(i, r["display"], r["score"], r["d4_tag"], r["mob_tag"])

if __name__ == "__main__":
    main()
