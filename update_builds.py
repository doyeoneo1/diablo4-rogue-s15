from __future__ import annotations

import re
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
    "IcyVeins": "https://www.icy-veins.com/d4/rogue/builds/",
}

KNOWN = {
    "penshot": {"labels": ["penetrating shot poison imbuement", "penetrating shot", "꿰뚫는 사격"], "display": "독 주입 꿰뚫는 사격"},
    "rapid": {"labels": ["rapid fire", "연발 사격"], "display": "냉기 연발 사격"},
    "dok": {"labels": ["dance of knives", "칼날의 춤"], "display": "독 주입 칼날의 춤"},
    "roa": {"labels": ["rain of arrows cold imbuement", "rain of arrows", "화살비"], "display": "냉기 화살비"},
    "death": {"labels": ["death trap", "죽음의 덫"], "display": "죽음의 덫"},
}

EXTRA = {
    "barrage": {"labels": ["barrage"], "display": "탄막"},
    "twisting-blades": {"labels": ["twisting blades"], "display": "회전 칼날"},
    "frostbite-trap": {"labels": ["frostbite trap"], "display": "동상 덫"},
}

DEFAULT_ORDER = ["penshot", "rapid", "dok", "roa", "death"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

DETAILS_JS = r'''
/* FULL_DETAIL_DATA_START */
const detailedBuildData = {
  penshot:{
    source:"Mobalytics · Season 15 · M1PY · 2026-09-18",
    total:"레벨 70 최종 스킬 트리: 83포인트 (레벨 69 + 시즌/명망 14)",
    specialization:"전투 준비",
    skills:[
      {name:"꿰뚫는 사격",points:"15",nodes:["쇠뇌 (Ballista)"],note:"주력. 수리뿔 벽 반사와 연계."},
      {name:"복제된 그림자",points:"15",nodes:["취약 부여/궁극기 보조 분기"],note:"독 주입 모방과 폭딜 창."},
      {name:"독 주입",points:"15",nodes:["독 지속 피해 증폭 분기"],note:"주력 꿰뚫는 사격에 독 피해 부여."},
      {name:"질주",points:"1",nodes:["기동/진입 분기"],note:"팩 진입과 위치 조정."},
      {name:"그림자 걸음",points:"1",nodes:["책략 (Artifice)"],note:"벽 통과/저지 불가/이동."},
      {name:"은폐",points:"2",nodes:["회복 (Recuperate)"],note:"보강·저지 불가·안전한 재배치."}
    ],
    runes:[
      "Cir + Mot — 어둠의 장막 그림자 자동 보충",
      "두 번째 룬어는 기동/극확 상황에 맞춰 구성",
      "룬어는 투구·가슴·바지의 2소켓 조합에 장착"
    ],
    gems:[
      "방어구: 최상급 에메랄드 — 민첩",
      "장신구: 시즌15 고뇌의 파편 / 고통의 파편 / 죄악의 파편 우선",
      "영혼 파편을 쓰지 않는 장신구 슬롯은 부족한 저항 보정",
      "독 변형은 시즌 파편/고유 효과를 일반 보석보다 우선"
    ]
  },

  rapid:{
    source:"Icy Veins · Season 15 Rapid Fire",
    total:"레벨 70 최종 스킬 트리: 83포인트 (레벨 69 + 시즌/명망 14)",
    specialization:"닐푸르의 좁은 눈 5세트 완성 시 연계 점수 / 완성 전 내면의 시야",
    skills:[
      {name:"심장추적자",points:"1",nodes:["합류 (Confluence)"],note:"복수 중첩과 연계 점수/세트 트리거."},
      {name:"연발 사격",points:"15",nodes:["소동 (Ruckus)","고단 광역: 폭발 사격 (Explosive Shot)"],note:"주력 핵심 기술."},
      {name:"질주",points:"1",nodes:["극대화 확률 보조","극확 100%면 약화 분기로 변경"],note:"기동 및 상태이상."},
      {name:"어둠의 장막",points:"15",nodes:["넘쳐흐름 (Overflow)","기력 안정 후 그림자 춤꾼 (Shadow Dancer)"],note:"생존·기력 재생."},
      {name:"냉기 주입",points:"15",nodes:["냉각/빙결 유지 분기"],note:"즉시 빙결과 냉기 배율 활성화."},
      {name:"복제된 그림자",points:"15",nodes:["궁극기 지속/재사용 보조"],note:"높은 가동률로 추가 화력 유지."}
    ],
    runes:[
      "Cir + Vex — 5회 기술 사용 후 +1 기술 등급 10초",
      "Noc + Jah — 군중 제어로 공물 생성, 다음 회피를 순간이동으로 대체",
      "극대화 확률 100% 미만이면 Jah → Gar"
    ],
    gems:[
      "무기: 최상급 사파이어 — 냉기 피해 배율",
      "방어구: 최상급 에메랄드 — 민첩",
      "장신구: 시즌15 고뇌의 파편 / 고통의 파편 / 죄악의 파편",
      "일반 보석 사용 시 최상급 다이아몬드(모든 저항), 요르단의 반지 사용 시 냉기 저항 보정용 사파이어 고려"
    ]
  },

  dok:{
    source:"Mobalytics S15 M1PY + Icy Veins S15",
    total:"레벨 70 최종 스킬 트리: 83포인트",
    specialization:"연계 점수 — 칼날의 춤 채널링 전 3중첩 스냅샷",
    skills:[
      {name:"칼날의 춤",points:"15",nodes:["칼날 부채 (Fan of Knives)","고단 나락: 수류탄 도약 (Grenade Jumper) 변형"],note:"주력 채널링 기술."},
      {name:"복제된 그림자",points:"15",nodes:["궁극기 지속/재사용 보조"],note:"폭딜 창."},
      {name:"은폐",points:"4",nodes:["은폐 해제 공격 보조 분기"],note:"안전 진입과 채널 유지."},
      {name:"어둠의 장막",points:"15",nodes:["넘쳐흐름 → 기력 안정 후 그림자 춤꾼"],note:"생존·기력 유지."},
      {name:"독 주입",points:"15",nodes:["독 지속 피해 증폭 분기"],note:"Mobalytics 독 엔드게임 변형 기준."},
      {name:"질주",points:"1",nodes:["기동 보조"],note:"팩 진입/이동."}
    ],
    runes:[
      "Cir + Vex — +1 기술 등급 유지",
      "Noc + Mot — 군중 제어 시 공물, 어둠의 장막 그림자 자동 보충"
    ],
    gems:[
      "무기: 최상급 사파이어 — 냉기 변형 기준 냉기 피해 배율",
      "방어구: 최상급 에메랄드 — 민첩",
      "장신구: 시즌15 고뇌의 파편 / 고통의 파편 / 죄악의 파편",
      "일반 장신구 보석은 최상급 다이아몬드, 요르단의 반지 사용 시 냉기 저항 사파이어 고려"
    ]
  },

  roa:{
    source:"Mobalytics · Season 15 · Rain of Arrows · 2026-09-15",
    total:"레벨 70 최종 스킬 트리: 83포인트",
    specialization:"전투 준비",
    skills:[
      {name:"화살비",points:"15",nodes:["궁극기 반복/집결 보조 분기"],note:"주력 궁극기."},
      {name:"냉기 주입",points:"15",nodes:["냉각·빙결 보조 분기"],note:"화살비의 냉기 시너지."},
      {name:"그림자 걸음",points:"1",nodes:["기동/저지 불가 분기"],note:"위치 조정."},
      {name:"은폐",points:"15",nodes:["생존·폭딜 준비 분기"],note:"안전한 궁극기 준비."},
      {name:"연막탄",points:"7",nodes:["제어/극대화 보조 분기"],note:"정예·우두머리 피해 창."},
      {name:"어둠의 장막",points:"15",nodes:["생존·기력 재생 분기"],note:"주요 방어층."}
    ],
    runes:[
      "궁극기 반복형: 자원/재사용 보조 룬어 우선",
      "기동형: Noc + Jah 계열 고려",
      "기술 등급이 필요한 변형은 Cir + Vex 고려"
    ],
    gems:[
      "무기: 최상급 사파이어 — 냉기 피해 배율",
      "방어구: 최상급 에메랄드 — 민첩",
      "장신구: 시즌15 영혼 파편 3종 우선",
      "일반 보석 사용 시 부족한 저항을 우선 보정"
    ]
  },

  death:{
    source:"Mobalytics · Season 15 · Death Trap · M1PY · 2026-09-19",
    total:"레벨 70 최종 스킬 트리: 83포인트",
    specialization:"전투 준비",
    skills:[
      {name:"죽음의 덫",points:"15",nodes:["죽음의 구덩이 (Death Pit)","재사용 대기시간 감소 보조"],note:"주력. 최종 세팅은 15초 이하 재사용 대기시간 목표."},
      {name:"어둠의 장막",points:"15",nodes:["5중첩 유지/생존 보조"],note:"상시 방어층."},
      {name:"냉기 주입",points:"15",nodes:["완충 전지 (Buffered Battery) 계열"],note:"보호막·제어 조건."},
      {name:"연막탄",points:"6",nodes:["극대화/제어 보조"],note:"폭딜 창."},
      {name:"그림자 걸음",points:"1",nodes:["책략 (Artifice)","재사용 대기시간 감소"],note:"무한 이동 변형 핵심."},
      {name:"은폐",points:"15",nodes:["저지 불가·초기화 보조"],note:"생존/이동 루프."}
    ],
    runes:[
      "Cir + Que — 보호막 상시 보충, 주력 추천",
      "Zan + Gar — 극대화 확률 100% 접근, 주력 추천",
      "대안: Zan + Jah — 이동 속도/순간이동 강화",
      "대안: Poc + Mot — 어둠의 장막 자동 생성",
      "대안: Cir + Lac — 추가 피해 감소",
      "대안: Cir + Vex — 소폭 추가 피해"
    ],
    gems:[
      "방어구: 최상급 에메랄드 — 민첩",
      "장신구: 시즌15 영혼 파편 우선",
      "저항이 부족하면 장신구 보석을 저항 보정용으로 조절",
      "핵심 브레이크포인트: 죽음의 덫 ≤15초 / 최대 기력 ≥225 / 즉시 225 기력 복구 / 덫 무장 시간 감소"
    ]
  }
};
/* FULL_DETAIL_DATA_END */
'''

FULL_CSS = r'''
/* FULL_DETAIL_CSS_START */
.skill-detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
.skill-detail-card{border:1px solid #3a342d;background:#10100f;padding:12px}
.skill-detail-card h4{margin:0;color:#e0d3c0;font-size:14px}
.skill-detail-card .pts{display:inline-block;margin-top:5px;color:#d0a86e;font-size:11px}
.skill-detail-card .nodes{margin-top:7px;color:#b7afa4;font-size:11px;line-height:1.55}
.skill-detail-card .why{margin-top:6px;color:#7e776e;font-size:10px;line-height:1.5}
.skill-total{margin:0 0 10px;padding:9px 11px;border-left:3px solid #8e3b2d;background:#15110f;color:#bcae9c;font-size:12px;line-height:1.6}
.socket-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.socket-card{border:1px solid #3b352f;background:#10100f;padding:12px}
.socket-card h3{margin:0 0 8px;color:#d8c3a3;font-size:16px;font-family:Georgia,serif}
.socket-card ul{margin:0;padding-left:18px;color:#aaa39a;font-size:11px;line-height:1.7}
.verify-note{margin-top:10px;color:#716b63;font-size:10px;line-height:1.55}
@media(max-width:560px){.skill-detail-grid,.socket-grid{grid-template-columns:1fr}}
/* FULL_DETAIL_CSS_END */
'''

SKILLS_RENDER = r'''<section class="section skills">
   <div class="section-head"><h2>기술 설정</h2><small>레벨 70 · 최종 투자 포인트 · 세부 노드</small></div>
   ${(()=>{const d=detailedBuildData[b.id]; return d?`
   <div class="skill-total"><b>${d.total}</b><br>전문화: ${d.specialization}<br>검증 기준: ${d.source}</div>
   <div class="skill-detail-grid">${d.skills.map((x,i)=>`
      <div class="skill-detail-card">
        <h4>${i+1}. ${x.name}</h4>
        <span class="pts">스킬 트리 투자: ${x.points}포인트</span>
        <div class="nodes"><b>세부 노드:</b> ${x.nodes.join(" → ")}</div>
        <div class="why">${x.note}</div>
      </div>`).join("")}</div>`:""})()}
   <div class="section-head" style="margin-top:14px"><h2 style="font-size:18px">핵심 지속 효과</h2><small>현재 빌드에 포함된 보조 노드</small></div>
   <div class="tree-list">${b.passives.map(s=>`<div class="tree-node"><b>${s[0]}</b><span>${s[1]}</span><div class="node-desc">${s[2]}</div></div>`).join("")}</div>
 </section>'''

SOCKET_SECTION = r'''<section class="section notes" data-full-detail-sockets="1">
   <div class="section-head"><h2>룬어 · 보석 · 영혼 파편</h2><small>부위별 장착 기준</small></div>
   ${(()=>{const d=detailedBuildData[b.id]; return d?`
   <div class="socket-grid">
      <div class="socket-card"><h3>룬어</h3><ul>${d.runes.map(x=>`<li>${x}</li>`).join("")}</ul></div>
      <div class="socket-card"><h3>보석 / 영혼 파편</h3><ul>${d.gems.map(x=>`<li>${x}</li>`).join("")}</ul></div>
   </div>
   <div class="verify-note">룬어는 최대 2세트. 시즌15 장신구는 영혼 파편이 일반 보석보다 우선되는 구성이 많습니다. 조건부 대안은 각 빌드 카드에 별도 표시합니다.</div>`:""})()}
 </section>'''

def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9가-힣+ ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def fetch_text(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    raw = r.text
    soup = BeautifulSoup(raw, "html.parser")
    return norm(raw + " " + " ".join(soup.stripped_strings))

def best_window(text: str, labels: list[str], radius: int = 550) -> str:
    for label in sorted(labels, key=len, reverse=True):
        n = norm(label)
        pos = text.find(n)
        if pos >= 0:
            return text[max(0, pos-radius):pos+radius]
    return ""

def source_score(text: str, labels: list[str]) -> tuple[int, str]:
    w = best_window(text, labels)
    if not w:
        return 0, "미감지"

    score = 40
    tags = ["감지"]

    for pat, pts, label in (
        ("s tier", 45, "S"),
        ("s-tier", 45, "S"),
        ("a tier", 30, "A"),
        ("a-tier", 30, "A"),
        ("b tier", 15, "B"),
        ("b-tier", 15, "B"),
    ):
        if pat in w:
            score += pts
            tags.append(label)
            break

    for pat, pts, label in (
        ("pushing", 20, "Push"),
        ("pit pushing", 20, "Pit"),
        ("the tower", 18, "Tower"),
        ("endgame", 12, "Endgame"),
        ("end game", 12, "Endgame"),
        ("meta", 10, "Meta"),
        ("speed farm", 4, "Speed"),
        ("speedfarm", 4, "Speed"),
        ("verified", 5, "Verified"),
    ):
        if pat in w:
            score += pts
            tags.append(label)

    return min(score, 100), "/".join(dict.fromkeys(tags))

def rank_builds(texts: dict[str, str]) -> list[dict]:
    candidates = {
        **{k: {**v, "known": True} for k, v in KNOWN.items()},
        **{k: {**v, "known": False} for k, v in EXTRA.items()},
    }
    rows = []

    for bid, meta in candidates.items():
        per_source = {}
        positive = []

        for src, text in texts.items():
            score, tag = source_score(text, meta["labels"])
            per_source[src] = {"score": score, "tag": tag}
            if score:
                positive.append(score)

        if not positive:
            continue

        avg = sum(positive) / len(positive)
        bonus = min(12, max(0, len(positive)-1) * 6)

        rows.append({
            "id": bid,
            "display": meta["display"],
            "known": meta["known"],
            "score": round(min(100, avg + bonus)),
            "source_hits": len(positive),
            "sources": per_source,
        })

    rows.sort(key=lambda r: (-r["score"], -r["source_hits"], r["display"]))
    return rows

def apply_korean_terms(page: str) -> str:
    replacements = [
        ("독 주입 관통 사격", "독 주입 꿰뚫는 사격"),
        ("관통 사격", "꿰뚫는 사격"),
        ("칼춤", "칼날의 춤"),
        ("그림자 복제", "복제된 그림자"),
        ("Combo Points", "연계 점수"),
        ("Preparation", "전투 준비"),
        ("Inner Sight", "내면의 시야"),
    ]

    for old, new in replacements:
        page = page.replace(old, new)

    page = page.replace("에너지 회복", "기력 회복")
    page = page.replace("최대 에너지", "최대 기력")
    page = page.replace("에너지 유지", "기력 유지")
    page = page.replace("에너지 복구", "기력 복구")
    return page

def upsert_between(page: str, start: str, end: str, block: str, before: str) -> str:
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)

    if pat.search(page):
        return pat.sub(block.strip(), page, count=1)

    if before not in page:
        raise RuntimeError(f"삽입 기준을 찾지 못했습니다: {before}")

    return page.replace(before, block.strip() + "\n" + before, 1)

def install_detail_data(page: str) -> str:
    return upsert_between(
        page,
        "/* FULL_DETAIL_DATA_START */",
        "/* FULL_DETAIL_DATA_END */",
        DETAILS_JS,
        "const skillDesc = {",
    )

def install_detail_css(page: str) -> str:
    start = "/* FULL_DETAIL_CSS_START */"
    end = "/* FULL_DETAIL_CSS_END */"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)

    if pat.search(page):
        return pat.sub(FULL_CSS.strip(), page, count=1)

    if "</style>" not in page:
        raise RuntimeError("</style>을 찾지 못했습니다.")

    return page.replace("</style>", FULL_CSS.strip() + "\n</style>", 1)

def install_skill_render(page: str) -> str:
    pat = re.compile(
        r'<section class="section skills">.*?</section>\s*'
        r'(?=<section class="section gear">)',
        re.S,
    )

    if not pat.search(page):
        raise RuntimeError("기술 설정 섹션을 찾지 못했습니다.")

    return pat.sub(SKILLS_RENDER + "\n ", page, count=1)

def install_socket_section(page: str) -> str:
    pat = re.compile(
        r'<section class="section notes" data-full-detail-sockets="1">.*?</section>\s*'
        r'(?=<section class="section paragon">)',
        re.S,
    )

    if pat.search(page):
        return pat.sub(SOCKET_SECTION + "\n ", page, count=1)

    marker = '<section class="section paragon">'

    if marker not in page:
        raise RuntimeError("정복자 섹션을 찾지 못했습니다.")

    return page.replace(marker, SOCKET_SECTION + "\n " + marker, 1)

def fix_build_specializations(page: str) -> str:
    replacements = {
        "penshot": "전투 준비",
        "rapid": "닐푸르 5세트: 연계 점수 / 이전: 내면의 시야",
        "dok": "연계 점수",
        "roa": "전투 준비",
        "death": "전투 준비",
    }

    for bid, value in replacements.items():
        page = re.sub(
            rf'(id:"{re.escape(bid)}".*?spec:")[^"]*(")',
            rf'\1{value}\2',
            page,
            count=1,
            flags=re.S,
        )

    return page

def ensure_daily_css(page: str) -> str:
    if ".daily-meta{" in page:
        return page

    css = r'''
.daily-meta{margin-top:12px;border:1px solid #45392d;background:linear-gradient(180deg,#151411,#0d0e0d);padding:16px}
.daily-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.daily-rank-card{display:flex;gap:10px;align-items:center;border:1px solid #39332c;background:#10100f;padding:11px}
.daily-rank-no{font-family:Georgia,serif;font-size:24px;color:#b98856;min-width:38px}
.daily-rank-main b{display:block;color:#ded4c7;font-size:13px}
.daily-rank-main small,.daily-rank-main span{display:block;font-size:10px;margin-top:3px}
.daily-rank-main small{color:#a68e72}.daily-rank-main span{color:#746f68;line-height:1.5}
.daily-warning{margin-top:10px;border-left:3px solid #b66b2d;background:#17110c;padding:10px 12px;color:#c9b49d;font-size:11px;line-height:1.6}
.daily-error{margin-top:10px;border-left:3px solid #8e1d18;background:#170d0d;padding:10px 12px;color:#c7a6a0;font-size:11px;line-height:1.6}
.daily-method{margin-top:10px;color:#716b63;font-size:10px;line-height:1.6}
@media(max-width:560px){.daily-rank-grid{grid-template-columns:1fr}}
'''

    return page.replace("</style>", css + "\n</style>", 1)

def source_summary(row: dict) -> str:
    bits = []

    for src in ("D4Guides", "Mobalytics", "IcyVeins"):
        info = row["sources"].get(src)
        if info and info["score"]:
            bits.append(f'{src} {htmlmod.escape(info["tag"])}')

    return " · ".join(bits) if bits else "감지 소스 없음"

def meta_block(rows: list[dict], errors: list[str], degraded: bool) -> str:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    top = rows[:max(5, min(7, len(rows)))] if rows else []

    cards = []

    for i, r in enumerate(top, 1):
        state = "상세 세팅 보유" if r["known"] else "신규 상위 빌드 감지"
        cards.append(
            '<div class="daily-rank-card">'
            f'<div class="daily-rank-no">#{i}</div>'
            '<div class="daily-rank-main">'
            f'<b>{htmlmod.escape(r["display"])}</b>'
            f'<small>{state} · 자동점수 {r["score"]}</small>'
            f'<span>{source_summary(r)}</span>'
            '</div></div>'
        )

    notices = []
    new_names = [r["display"] for r in top if not r["known"]]

    if new_names:
        notices.append(
            '<div class="daily-warning"><b>신규 상위 빌드 감지:</b> '
            + ", ".join(htmlmod.escape(x) for x in new_names)
            + " — 상세 스킬/장비는 검증 전 자동 생성하지 않습니다.</div>"
        )

    if degraded:
        notices.append(
            '<div class="daily-warning"><b>안전 모드:</b> '
            '2개 이상 소스에서 기존 5개 빌드가 충분히 확인되지 않아 기존 상세 빌드 순서를 유지합니다.</div>'
        )

    if errors:
        notices.append(
            '<div class="daily-error"><b>수집 실패:</b> '
            + " / ".join(htmlmod.escape(x) for x in errors)
            + "</div>"
        )

    if not cards:
        cards.append(
            '<div class="daily-rank-card"><div class="daily-rank-no">–</div>'
            '<div class="daily-rank-main"><b>자동 순위 산출 보류</b>'
            '<small>기존 세팅 유지</small><span>다음 실행에서 재수집</span></div></div>'
        )

    return (
        '<!-- DAILY_META_START --><section class="daily-meta">'
        f'<div class="section-head"><h2>오늘의 도적 고점 메타</h2><small>무료 자동 집계 · {now} KST</small></div>'
        f'<div class="daily-rank-grid">{"".join(cards)}</div>'
        + "".join(notices)
        + '<div class="daily-method">D4Guides · Mobalytics · Icy Veins 공개 페이지의 '
          'Tier / Pushing / Tower / Endgame 신호를 교차 집계합니다.</div>'
          '</section><!-- DAILY_META_END -->'
    )

def inject_meta(page: str, block: str) -> str:
    pat = re.compile(r"<!-- DAILY_META_START -->.*?<!-- DAILY_META_END -->", re.S)

    if pat.search(page):
        return pat.sub(block, page, count=1)

    marker = '<nav class="build-tabs" id="tabs"></nav>'

    if marker not in page:
        raise RuntimeError("메타 삽입 위치를 찾지 못했습니다.")

    return page.replace(marker, marker + "\n" + block, 1)

def remove_meta_ui(page: str) -> str:
    page = re.sub(
        r"<!-- DAILY_META_START -->.*?<!-- DAILY_META_END -->\s*",
        "",
        page,
        flags=re.S,
    )
    return page

def install_ingame_item_ui(page: str) -> str:
    css = '/* INGAME_ITEM_UI_START */\n.item{background:linear-gradient(180deg,#17120d 0%,#0a0a09 55%,#070707 100%);border:1px solid #6b4a28;padding:13px 13px 13px 50px;box-shadow:inset 0 1px 0 rgba(255,214,150,.06),0 8px 18px rgba(0,0,0,.28)}\n.item:before{top:13px;width:30px;height:40px;border-color:#6b5535;background:radial-gradient(circle at 50% 35%,#251b11,#080808 72%);color:#9a7b52}\n.item .slot{font-size:10px;color:#807467;letter-spacing:.08em}\n.item-rarity{margin-top:3px;font-size:10px;color:#b77a3e;letter-spacing:.1em}\n.item .name{font-family:Georgia,"Times New Roman",serif;font-size:15px;color:#d99549;line-height:1.3;margin-top:2px}\n.item.unique{border-color:#9a6a36}.item.unique .name,.item.unique .item-rarity{color:#d59a52}\n.item.mythic{border-color:#7f5797}.item.mythic .name,.item.mythic .item-rarity{color:#c58ee6}\n.affix-preview{margin-top:8px;padding-top:7px;border-top:1px solid #332c25;color:#9f968a;line-height:1.55}\n.item-detail{margin-top:9px;padding:10px 0 0;border-top:1px solid #3a3027;background:transparent;color:#c1b7aa;font-size:11px;line-height:1.7;white-space:normal}\n.item-detail br{display:block;content:"";margin-top:5px}\n/* INGAME_ITEM_UI_END */'

    start = "/* INGAME_ITEM_UI_START */"
    end = "/* INGAME_ITEM_UI_END */"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)

    if pat.search(page):
        page = pat.sub(css, page, count=1)
    elif "</style>" in page:
        page = page.replace("</style>", css + "\n</style>", 1)

    helper = 'function formatItemText(t){ return (t||"").replace(/\\\\n/g,"<br>"); }'
    if "function formatItemText(" not in page:
        page = page.replace(
            "function tooltipText(name, desc){",
            helper + "\n\nfunction tooltipText(name, desc){",
            1,
        )

    old = '<div class="slot">${g[0]}</div><div class="name">${g[1]}</div>\n      <div class="affix-preview">${(g[4]||[]).slice(0,2).join(" · ")}</div>\n      <div class="item-detail">${g[3]}</div>'
    new = '<div class="slot">${g[0]}</div><div class="item-rarity">${g[2]==="mythic"?"신화 고유":g[2]==="unique"?"고유":"전설"}</div><div class="name">${g[1]}</div>\n      <div class="affix-preview">${(g[4]||[]).slice(0,2).join(" · ")}</div>\n      <div class="item-detail">${formatItemText(g[3])}</div>'
    page = page.replace(old, new)
    return page

def update_badge(page: str, source_ok: int) -> str:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    page = re.sub(r'<span class="pill">자동화 테스트:.*?</span>', "", page, count=1)
    badge = f'<span class="pill">자동 갱신: {now}</span>'

    if re.search(r'<span class="pill">자동 갱신:.*?</span>', page):
        return re.sub(r'<span class="pill">자동 갱신:.*?</span>', badge, page, count=1)

    return page.replace('<div class="meta">', '<div class="meta">' + badge, 1)

def inject_order(page: str, ids: list[str]) -> str:
    if not ids:
        ids = DEFAULT_ORDER[:]

    array = "[" + ",".join(f'"{x}"' for x in ids) + "]"
    page = re.sub(r'const dailyOrder=\[[^\]]*\];\s*', "", page, count=1)
    marker = 'const tabs=document.getElementById("tabs");'

    if marker not in page:
        return page

    page = page.replace(marker, f"const dailyOrder={array};\n" + marker, 1)

    sort_code = '''builds.sort((a,b)=>{
 const ai=dailyOrder.indexOf(a.id), bi=dailyOrder.indexOf(b.id);
 const av=ai<0?999:ai, bv=bi<0?999:bi;
 return av-bv;
});
'''

    if sort_code not in page:
        page = page.replace(
            'builds.forEach((b,i)=>{',
            sort_code + 'builds.forEach((b,i)=>{',
            1,
        )

    return page

def apply_full_detail(page: str) -> str:
    page = apply_korean_terms(page)
    page = fix_build_specializations(page)
    page = install_detail_css(page)
    page = install_detail_data(page)
    page = install_skill_render(page)
    page = install_socket_section(page)

    phrase = "모바일에서 바로 확인할 수 있도록 모든 설명을 항상 펼쳐서 표시합니다."
    extra = (
        phrase
        + " 기술별 최종 투자 포인트·세부 노드·룬어·보석/영혼 파편까지 함께 표시합니다."
    )

    if phrase in page and extra not in page:
        page = page.replace(phrase, extra, 1)

    return page

def main() -> int:
    if not INDEX.exists():
        print("[ERROR] index.html 없음")
        return 0

    texts = {}
    errors = []

    for name, url in SOURCES.items():
        try:
            texts[name] = fetch_text(url)
            print(f"[OK] {name}: {len(texts[name])}")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
            print(f"[WARN] {name}: {e}")

    rows = rank_builds(texts) if texts else []
    ranked_known = [r for r in rows if r["known"]]
    enough = len(ranked_known) >= 5 and len(texts) >= 2

    ordered = [r["id"] for r in ranked_known] if enough else DEFAULT_ORDER[:]
    degraded = not enough

    page = INDEX.read_text(encoding="utf-8")
    page = apply_full_detail(page)
    page = remove_meta_ui(page)
    page = install_ingame_item_ui(page)
    page = update_badge(page, len(texts))
    page = inject_order(page, ordered)
    INDEX.write_text(page, encoding="utf-8")

    print("[DONE] 상세 세팅 + 한국어 용어 + 룬/보석 + 인게임형 장비 UI 갱신")
    print("[MODE]", "정상 순위 갱신" if enough else "안전 모드")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
