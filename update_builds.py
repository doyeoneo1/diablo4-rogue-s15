
from __future__ import annotations
import re, html, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

INDEX = Path("index.html")
KST = timezone(timedelta(hours=9))

CLASSES = [
    ("barbarian","야만용사","Barbarian","https://d4guides.gg/en/builds?class=barbarian"),
    ("druid","드루이드","Druid","https://d4guides.gg/en/builds?class=druid"),
    ("necromancer","강령술사","Necromancer","https://d4guides.gg/en/builds?class=necromancer"),
    ("rogue","도적","Rogue","https://d4guides.gg/en/builds?class=rogue"),
    ("sorcerer","원소술사","Sorcerer","https://d4guides.gg/en/builds?class=sorcerer"),
    ("spiritborn","혼령사","Spiritborn","https://d4guides.gg/en/builds?class=spiritborn"),
    ("paladin","성기사","Paladin","https://d4guides.gg/en/builds?class=paladin"),
    ("warlock","흑마법사","Warlock","https://d4guides.gg/en/builds?class=warlock"),
]

HEADERS = {
    "User-Agent":"Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36",
    "Accept-Language":"en-US,en;q=0.9",
}

KO = {
    "Whirlwind":"회오리바람","Hammer of the Ancients":"선조의 망치","Rallying Cry":"집결의 함성",
    "Challenging Shout":"도전의 외침","War Cry":"전장의 함성","Wrath of the Berserker":"광전사의 진노",
    "Iron Skin":"철갑 피부","Leap":"도약","Call of the Ancients":"선조의 귀환","Lunging Strike":"달려들기",
    "Storm Shred":"폭풍 칼날 발톱","Landslide":"산사태","Companion":"동료","Lightning Storm":"번개 폭풍",
    "Golem":"골렘","Army of the Dead":"망자의 군대","Bone Spirit":"뼈 영혼","Blood Wave":"피의 파도",
    "Blight":"마름병","Sever":"절단","Bone Prison":"뼈 감옥","Decrepify":"노화","Iron Maiden":"가시 박힌 철관",
    "Penetrating Shot":"꿰뚫는 사격","Rapid Fire":"연발 사격","Dance of Knives":"칼날의 춤",
    "Rain of Arrows":"화살비","Death Trap":"죽음의 덫","Poison Imbuement":"독 주입","Cold Imbuement":"냉기 주입",
    "Shadow Clone":"복제된 그림자","Dark Shroud":"어둠의 장막","Concealment":"은폐","Smoke Grenade":"연막탄",
    "Ring of Fire":"화염 고리","Firewall":"화염벽","Ball Lightning":"구상 번개","Meteor":"운석 낙하",
    "Ice Shards":"얼음 파편","Blizzard":"눈보라","Hydra":"히드라","Teleport":"순간이동","Ice Armor":"얼음 갑옷",
    "Unstable Currents":"불안정한 전류","Lightning Spear":"번개 창",
    "Pestilent Swarm":"역병 떼","Counterattack":"반격","Scourge":"재앙","Toxic Skin":"독성 피부",
    "Rushing Claw":"돌진 발톱","Ravager":"유린자","The Devourer":"포식자",
    "Hammerdin":"해머딘","Auradin":"오라딘","Shield of Retribution":"응징의 방패",
    "Blessed Hammer":"축복받은 망치","Apocalypse":"종말","Blazing Scream":"타오르는 비명",
    "Dread Claws":"공포의 발톱","Lunatic":"광인","Road Runner":"로드 러너",
}

def tr(x):
    return KO.get(x.strip(), x.strip())

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.text

def soup_text(soup):
    return "\n".join(x.strip() for x in soup.stripped_strings if x.strip())

def first(pat, text, default=""):
    m = re.search(pat, text, re.I|re.M|re.S)
    return m.group(1).strip() if m else default

def discover_builds(class_url, class_en):
    soup = BeautifulSoup(fetch(class_url), "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = " ".join(a.stripped_strings)
        if "/en/build/" not in href:
            continue
        if class_en.lower() not in (label + " " + href).lower():
            continue
        if "Endgame" not in label and "endgame" not in href.lower():
            continue
        u = urljoin(class_url, href)
        if u not in [x[0] for x in found]:
            found.append((u, label))
    return found[:5]

def parse_build(url):
    soup = BeautifulSoup(fetch(url), "html.parser")
    text = soup_text(soup)
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else url.rstrip("/").split("/")[-1]
    name = title.split("·")[0].replace("Build Guide","").strip()
    tier = first(r"\b([SABC][+-]?-Tier)\b", text, "—")

    skills = []
    for n, rank in re.findall(r"^\s*([A-Za-z][A-Za-z0-9 '&/\-]+?)\s+\(Rank\s+(\d+)\)\s*$", text, re.M):
        item = [tr(n), int(rank)]
        if item not in skills:
            skills.append(item)
    skills = skills[:14]

    bar = []
    sb = first(r"skill bar runs\s+(.+?)\.", text, "")
    if sb:
        bar = [tr(x.strip()) for x in re.split(r",\s*|\s+and\s+", sb) if x.strip()]

    gear = []
    cg = first(r"Core gear:\s*(.+?)\.\s*Key aspects:", text, "")
    if cg:
        gear = [x.strip() for x in re.split(r",\s*|\s+and\s+", cg) if x.strip()]

    aspects = []
    ka = first(r"Key aspects:\s*(.+?)\.\s*Paragon uses", text, "")
    if ka:
        ka = re.sub(r"\(\+\d+ more\)", "", ka)
        aspects = [x.strip() for x in re.split(r",\s*|\s+and\s+", ka) if x.strip()]

    boards = []
    mb = re.search(r"### Paragon Boards\s*(.*?)(?:### Glyphs|### Mercenaries|Notes)", text, re.S|re.I)
    if mb:
        boards = [x.strip(" *-\t") for x in mb.group(1).splitlines() if x.strip(" *-\t")][:6]

    glyphs = []
    mg = re.search(r"### Glyphs\s*(.*?)(?:### Mercenaries|Notes)", text, re.S|re.I)
    if mg:
        glyphs = [x.strip(" *-\t") for x in mg.group(1).splitlines() if x.strip(" *-\t")][:6]

    return {
        "name": tr(name),
        "en": name,
        "tier": tier,
        "purpose": "Endgame",
        "skillbar": bar,
        "skills": skills,
        "gear": gear,
        "aspects": aspects,
        "boards": boards,
        "glyphs": glyphs,
        "url": url,
    }

def safe_class(cid, ko, en, url):
    try:
        builds = []
        for u, _ in discover_builds(url, en):
            try:
                builds.append(parse_build(u))
            except Exception as e:
                builds.append({"name":"상세 수집 실패","en":u.split("/")[-1],"tier":"—","purpose":"Endgame",
                               "skillbar":[],"skills":[],"gear":[],"aspects":[],"boards":[],"glyphs":[],
                               "url":u,"error":type(e).__name__})
        return {"id":cid,"name":ko,"en":en,"url":url,"builds":builds}
    except Exception as e:
        return {"id":cid,"name":ko,"en":en,"url":url,"builds":[],"error":type(e).__name__}

def render(data):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    payload = json.dumps(data, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>디아블로 IV 시즌 15 · 8직업 엔드게임 라이브러리</title>
<style>
:root{{--bg:#070707;--p:#12110f;--line:#493a2c;--gold:#c58e4d;--text:#ddd4c8;--muted:#8d8378}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 50% -15%,#2a2119,#080808 44%,#040404 80%);color:var(--text);font-family:"Malgun Gothic",system-ui,sans-serif}}
.shell{{max-width:1500px;margin:auto;padding:10px 10px 60px}}header,.hero,.section{{border:1px solid #44372b;background:linear-gradient(180deg,#17130f,#0b0c0c);box-shadow:0 12px 30px #000}}
header{{padding:17px}}.k{{font-size:10px;letter-spacing:.2em;color:var(--gold)}}h1{{font:500 clamp(25px,5vw,43px) Georgia,serif;margin:6px 0}}.sub{{font-size:12px;line-height:1.7;color:#999187}}
.tabs{{display:flex;gap:7px;overflow:auto;padding:9px 1px;scrollbar-width:none}}#classTabs{{position:sticky;top:0;z-index:20;background:rgba(7,7,7,.95);backdrop-filter:blur(8px)}}
.btn{{flex:0 0 auto;border:1px solid #493d32;background:#151412;color:#bcb1a4;padding:10px 12px;font-weight:700}}.btn.active{{border-color:#aa7442;color:#f1e4d5;box-shadow:inset 0 -2px #a83729}}
.hero{{padding:16px;margin-top:3px}}.hero h2{{font:500 30px Georgia,serif;margin:2px 0}}.badges{{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}}.badge{{border:1px solid #594633;background:#13110f;padding:5px 8px;font-size:10px;color:#c3a983}}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:10px;margin-top:10px}}.section{{grid-column:span 6;padding:14px}}.wide{{grid-column:span 12}}
.section h3{{font:500 19px Georgia,serif;color:#d6bb99;margin:0 0 10px;border-bottom:1px solid #302a24;padding-bottom:8px}}
.skillgrid,.itemgrid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}}.skill,.item{{border:1px solid #3d342c;background:#0f0f0e;padding:10px}}
.skill b,.item b{{color:#dfd2c2;font-size:12px}}.rank{{color:#d09a5e;font-size:10px;margin-top:4px}}.item{{border-color:#6c4c2d;background:linear-gradient(180deg,#17120d,#0a0a09)}}.item .rarity{{font-size:9px;color:#b77c42;letter-spacing:.1em}}.item b{{display:block;color:#d89b52;margin-top:3px;font-family:Georgia,serif}}
ul{{padding-left:18px;margin:0}}li{{font-size:11px;color:#aaa198;line-height:1.7}}.empty{{font-size:11px;color:#6f6962}}.note{{font-size:10px;color:#79716a;line-height:1.6;margin-top:8px}}a{{color:#bd9363;text-decoration:none}}
@media(max-width:760px){{.section{{grid-column:span 12}}.skillgrid,.itemgrid{{grid-template-columns:1fr}}.shell{{padding:8px 8px 45px}}.btn{{font-size:12px;padding:9px 10px}}}}
</style>
</head>
<body>
<div class="shell">
<header>
<div class="k">DIABLO IV · SEASON 15 · ALL CLASS ENDGAME LIBRARY</div>
<h1>시즌 15 · 8직업 엔드게임 라이브러리</h1>
<div class="sub">자동 갱신 {now} · 각 직업 상위 엔드게임 빌드를 자동 수집합니다. 한국어 공식 명칭이 확실한 항목만 한국어로 표시하고, 불확실한 신규 용어는 영문을 유지합니다.</div>
</header>
<div class="tabs" id="classTabs"></div><div id="app"></div>
</div>
<script>
const DATA={payload};
let cid="rogue", bi=0;
function list(xs){{return xs&&xs.length?`<ul>${{xs.map(x=>`<li>${{x}}</li>`).join("")}}</ul>`:`<div class="empty">수집 데이터 없음</div>`}}
function render(){{
 const c=DATA.find(x=>x.id===cid)||DATA[0], b=c.builds[bi]||c.builds[0];
 if(!b){{document.getElementById("app").innerHTML=`<section class="hero"><h2>${{c.name}}</h2><div class="note">오늘 빌드 상세 수집 실패. 다음 자동 실행에서 재시도합니다.</div></section>`;return}}
 document.getElementById("app").innerHTML=`
 <section class="hero"><div class="k">${{c.en.toUpperCase()}} · ${{b.tier}}</div><h2>${{b.name}}</h2>
 <div class="badges"><span class="badge">${{b.en}}</span><span class="badge">${{b.purpose}}</span><span class="badge">${{b.tier}}</span></div>
 <div class="tabs" id="buildTabs"></div></section>
 <main class="grid">
 <section class="section"><h3>스킬바</h3>${{list(b.skillbar)}}</section>
 <section class="section"><h3>스킬 포인트 / 세부 노드</h3><div class="skillgrid">${{b.skills&&b.skills.length?b.skills.map(s=>`<div class="skill"><b>${{s[0]}}</b><div class="rank">Rank ${{s[1]}}</div></div>`).join(""):`<div class="empty">상세 포인트 수집 데이터 없음</div>`}}</div>
 <div class="note">원본 빌드 페이지에 공개된 Rank를 그대로 반영합니다. 추측값은 넣지 않습니다.</div></section>
 <section class="section"><h3>핵심 장비</h3><div class="itemgrid">${{b.gear&&b.gear.length?b.gear.map(x=>`<div class="item"><div class="rarity">CORE ITEM</div><b>${{x}}</b></div>`).join(""):`<div class="empty">핵심 장비 수집 데이터 없음</div>`}}</div></section>
 <section class="section"><h3>핵심 위상</h3>${{list(b.aspects)}}</section>
 <section class="section"><h3>정복자 보드</h3>${{list(b.boards)}}</section>
 <section class="section"><h3>문장</h3>${{list(b.glyphs)}}</section>
 <section class="section wide"><h3>원본 / 검증</h3><a href="${{b.url}}" target="_blank" rel="noopener">D4Guides 원본 빌드 열기</a>
 <div class="note">자동 수집에 실패한 항목은 비워두고 다음 실행에서 다시 시도합니다.</div></section>
 </main>`;
 const bt=document.getElementById("buildTabs");
 c.builds.forEach((x,i)=>{{const q=document.createElement("button");q.className="btn"+(i===bi?" active":"");q.textContent=x.name;q.onclick=()=>{{bi=i;render()}};bt.appendChild(q)}})
}}
const ct=document.getElementById("classTabs");
DATA.forEach(c=>{{const q=document.createElement("button");q.className="btn"+(c.id===cid?" active":"");q.textContent=c.name;q.onclick=()=>{{cid=c.id;bi=0;document.querySelectorAll("#classTabs .btn").forEach(x=>x.classList.remove("active"));q.classList.add("active");render()}};ct.appendChild(q)}})
render();
</script>
</body>
</html>'''

def main():
    data = []
    for cid,ko,en,url in CLASSES:
        print("[CLASS]", ko)
        data.append(safe_class(cid,ko,en,url))
    INDEX.write_text(render(data), encoding="utf-8")
    print("[DONE] 8직업 페이지 생성")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
