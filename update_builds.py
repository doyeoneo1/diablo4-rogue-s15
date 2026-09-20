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
    "penshot": {
        "labels": [
            "penetrating shot poison imbuement",
            "penetrating shot",
            "꿰뚫는 사격",
        ],
        "display": "독 주입 꿰뚫는 사격",
    },
    "rapid": {
        "labels": [
            "rapid fire",
            "연발 사격",
        ],
        "display": "냉기 연발 사격",
    },
    "dok": {
        "labels": [
            "dance of knives",
            "칼날의 춤",
        ],
        "display": "독 주입 칼날의 춤",
    },
    "roa": {
        "labels": [
            "rain of arrows cold imbuement",
            "rain of arrows",
            "화살비",
        ],
        "display": "냉기 화살비",
    },
    "death": {
        "labels": [
            "death trap",
            "죽음의 덫",
        ],
        "display": "죽음의 덫",
    },
}

EXTRA = {
    "twisting-blades": {
        "labels": [
            "twisting blades",
        ],
        "display": "회전 칼날",
    },
    "frostbitten": {
        "labels": [
            "frostbitten",
            "frostbite trap",
        ],
        "display": "동상 계열",
    },
    "barrage": {
        "labels": [
            "barrage",
        ],
        "display": "탄막",
    },
}

DEFAULT_ORDER = [
    "penshot",
    "rapid",
    "dok",
    "roa",
    "death",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) "
        "AppleWebKit/537.36 "
        "Chrome/124.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9가-힣+ ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_text(url: str) -> str:
    r = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()

    raw = r.text

    soup = BeautifulSoup(
        raw,
        "html.parser",
    )

    visible = " ".join(
        soup.stripped_strings
    )

    return norm(
        raw + " " + visible
    )


def best_window(
    text: str,
    labels: list[str],
    radius: int = 550,
) -> str:

    for label in sorted(
        labels,
        key=len,
        reverse=True,
    ):

        n = norm(label)

        pos = text.find(n)

        if pos >= 0:
            return text[
                max(
                    0,
                    pos - radius,
                ):
                pos + radius
            ]

    return ""


def source_score(
    source: str,
    text: str,
    labels: list[str],
) -> tuple[int, str]:

    w = best_window(
        text,
        labels,
    )

    if not w:
        return 0, "미감지"

    score = 40
    tags = ["감지"]

    tier_patterns = (
        (
            "s tier",
            45,
            "S",
        ),
        (
            "s-tier",
            45,
            "S",
        ),
        (
            "a tier",
            30,
            "A",
        ),
        (
            "a-tier",
            30,
            "A",
        ),
        (
            "b tier",
            15,
            "B",
        ),
        (
            "b-tier",
            15,
            "B",
        ),
    )

    for (
        pat,
        pts,
        label,
    ) in tier_patterns:

        if pat in w:

            score += pts

            tags.append(
                label
            )

            break

    signals = (
        (
            "pushing",
            20,
            "Push",
        ),
        (
            "pit pushing",
            20,
            "Pit",
        ),
        (
            "the tower",
            18,
            "Tower",
        ),
        (
            "endgame",
            12,
            "Endgame",
        ),
        (
            "end game",
            12,
            "Endgame",
        ),
        (
            "meta",
            10,
            "Meta",
        ),
        (
            "speedfarm",
            4,
            "Speed",
        ),
        (
            "speed farm",
            4,
            "Speed",
        ),
        (
            "verified",
            5,
            "Verified",
        ),
    )

    for (
        pat,
        pts,
        label,
    ) in signals:

        if pat in w:

            score += pts

            tags.append(
                label
            )

    return (
        min(
            score,
            100,
        ),
        "/".join(
            dict.fromkeys(
                tags
            )
        ),
    )


def rank_builds(
    source_texts: dict[str, str],
) -> list[dict]:

    candidates = {}

    for (
        bid,
        meta,
    ) in KNOWN.items():

        candidates[bid] = {
            **meta,
            "known": True,
        }

    for (
        bid,
        meta,
    ) in EXTRA.items():

        candidates[bid] = {
            **meta,
            "known": False,
        }

    rows = []

    for (
        bid,
        meta,
    ) in candidates.items():

        per_source = {}

        positive = []

        for (
            source,
            text,
        ) in source_texts.items():

            (
                score,
                tag,
            ) = source_score(
                source,
                text,
                meta["labels"],
            )

            per_source[
                source
            ] = {
                "score": score,
                "tag": tag,
            }

            if score > 0:

                positive.append(
                    score
                )

        if not positive:
            continue

        avg = (
            sum(
                positive
            )
            / len(
                positive
            )
        )

        consensus_bonus = min(
            12,
            max(
                0,
                len(
                    positive
                ) - 1,
            )
            * 6,
        )

        total = round(
            min(
                100,
                avg
                + consensus_bonus,
            )
        )

        rows.append(
            {
                "id": bid,
                "display": meta[
                    "display"
                ],
                "known": meta[
                    "known"
                ],
                "score": total,
                "sources": per_source,
                "source_hits": len(
                    positive
                ),
            }
        )

    rows.sort(
        key=lambda r: (
            -r[
                "score"
            ],
            -r[
                "source_hits"
            ],
            r[
                "display"
            ],
        )
    )

    return rows


def ensure_css(
    page: str,
) -> str:

    if ".daily-meta{" in page:
        return page

    css = """
.daily-meta{
    margin-top:12px;
    border:1px solid #45392d;
    background:linear-gradient(
        180deg,
        #151411,
        #0d0e0d
    );
    padding:16px;
    box-shadow:
        0 12px 28px
        rgba(
            0,
            0,
            0,
            .55
        );
}

.daily-rank-grid{
    display:grid;
    grid-template-columns:
        repeat(
            2,
            minmax(
                0,
                1fr
            )
        );
    gap:8px;
}

.daily-rank-card{
    display:flex;
    gap:10px;
    align-items:center;
    border:
        1px solid
        #39332c;
    background:#10100f;
    padding:11px;
}

.daily-rank-no{
    font-family:
        Georgia,
        serif;
    font-size:24px;
    color:#b98856;
    min-width:38px;
}

.daily-rank-main b{
    display:block;
    color:#ded4c7;
    font-size:13px;
}

.daily-rank-main small{
    display:block;
    color:#a68e72;
    font-size:10px;
    margin-top:3px;
}

.daily-rank-main span{
    display:block;
    color:#746f68;
    font-size:10px;
    margin-top:3px;
    line-height:1.5;
}

.daily-warning{
    margin-top:10px;
    border-left:
        3px solid
        #b66b2d;
    background:#17110c;
    padding:10px 12px;
    color:#c9b49d;
    font-size:11px;
    line-height:1.6;
}

.daily-error{
    margin-top:10px;
    border-left:
        3px solid
        #8e1d18;
    background:#170d0d;
    padding:10px 12px;
    color:#c7a6a0;
    font-size:11px;
    line-height:1.6;
}

.daily-method{
    margin-top:10px;
    color:#716b63;
    font-size:10px;
    line-height:1.6;
}

@media(max-width:560px){

    .daily-rank-grid{
        grid-template-columns:1fr;
    }

}
"""

    return page.replace(
        "</style>",
        css
        + "\n</style>",
        1,
    )


def source_summary(
    row: dict,
) -> str:

    bits = []

    for src in (
        "D4Guides",
        "Mobalytics",
        "IcyVeins",
    ):

        info = row[
            "sources"
        ].get(
            src
        )

        if (
            info
            and info[
                "score"
            ] > 0
        ):

            bits.append(
                f'{src} '
                f'{htmlmod.escape(info["tag"])}'
            )

    if bits:

        return (
            " · ".join(
                bits
            )
        )

    return (
        "감지 소스 없음"
    )


def build_meta_block(
    rows: list[dict],
    errors: list[str],
    degraded: bool,
) -> str:

    now = datetime.now(
        KST
    ).strftime(
        "%Y-%m-%d %H:%M"
    )

    if rows:

        top_count = max(
            5,
            min(
                7,
                len(
                    rows
                ),
            ),
        )

        top = rows[
            :top_count
        ]

    else:

        top = []

    cards = []

    for (
        i,
        row,
    ) in enumerate(
        top,
        1,
    ):

        if row[
            "known"
        ]:

            state = (
                "상세 세팅 보유"
            )

        else:

            state = (
                "신규 상위 빌드 감지"
            )

        cards.append(
            '<div class="daily-rank-card">'
            f'<div class="daily-rank-no">'
            f'#{i}'
            f'</div>'
            '<div class="daily-rank-main">'
            f'<b>'
            f'{htmlmod.escape(row["display"])}'
            f'</b>'
            f'<small>'
            f'{state}'
            f' · 자동점수 '
            f'{row["score"]}'
            f'</small>'
            f'<span>'
            f'{source_summary(row)}'
            f'</span>'
            '</div>'
            '</div>'
        )

    notices = []

    new_builds = [
        r[
            "display"
        ]
        for r
        in top
        if not r[
            "known"
        ]
    ]

    if new_builds:

        notices.append(
            '<div class="daily-warning">'
            '<b>'
            '신규 상위 빌드 감지:'
            '</b> '
            + ", ".join(
                htmlmod.escape(
                    x
                )
                for x
                in new_builds
            )
            + " — 무료 자동화는 "
            "검증되지 않은 "
            "장비·정복자 세팅을 "
            "임의 생성하지 않습니다."
            "</div>"
        )

    if degraded:

        notices.append(
            '<div class="daily-warning">'
            '<b>'
            '안전 모드:'
            '</b> '
            '오늘 수집 데이터가 '
            '충분하지 않아 '
            '기존 상세 빌드 순서는 '
            '유지했습니다. '
            '잘못된 순위로 '
            '덮어쓰지 않습니다.'
            '</div>'
        )

    if errors:

        notices.append(
            '<div class="daily-error">'
            '<b>'
            '수집 실패:'
            '</b> '
            + " / ".join(
                htmlmod.escape(
                    x
                )
                for x
                in errors
            )
            + '</div>'
        )

    if not cards:

        cards.append(
            '<div class="daily-rank-card">'
            '<div class="daily-rank-no">'
            '–'
            '</div>'
            '<div class="daily-rank-main">'
            '<b>'
            '오늘 자동 순위 산출 보류'
            '</b>'
            '<small>'
            '기존 상세 빌드는 그대로 유지'
            '</small>'
            '<span>'
            '다음 자동 실행에서 '
            '다시 수집합니다.'
            '</span>'
            '</div>'
            '</div>'
        )

    return (
        '<!-- DAILY_META_START -->'
        '<section class="daily-meta">'

        f'<div class="section-head">'
        f'<h2>'
        f'오늘의 도적 고점 메타'
        f'</h2>'
        f'<small>'
        f'무료 자동 집계 · '
        f'{now} KST'
        f'</small>'
        f'</div>'

        f'<div class="daily-rank-grid">'
        f'{"".join(cards)}'
        f'</div>'

        + "".join(
            notices
        )

        + '<div class="daily-method">'
        'D4Guides · '
        'Mobalytics · '
        'Icy Veins의 '
        '공개 페이지에서 '
        '빌드명과 '
        'Tier / Pushing / '
        'Tower / Endgame '
        '신호를 교차 집계합니다. '
        '사이트 구조가 바뀌거나 '
        '데이터가 부족하면 '
        '순서를 임의 변경하지 않습니다.'
        '</div>'

        '</section>'
        '<!-- DAILY_META_END -->'
    )


def inject_meta(
    page: str,
    block: str,
) -> str:

    pat = re.compile(
        r"<!-- DAILY_META_START -->"
        r".*?"
        r"<!-- DAILY_META_END -->",
        re.S,
    )

    if pat.search(
        page
    ):

        return pat.sub(
            block,
            page,
            count=1,
        )

    marker = (
        '<nav class="build-tabs" '
        'id="tabs"></nav>'
    )

    if marker not in page:

        raise RuntimeError(
            "메타 섹션 "
            "삽입 위치를 "
            "찾지 못했습니다."
        )

    return page.replace(
        marker,
        marker
        + "\n"
        + block,
        1,
    )


def update_badge(
    page: str,
    source_ok: int,
) -> str:

    now = datetime.now(
        KST
    ).strftime(
        "%Y-%m-%d %H:%M"
    )

    page = re.sub(
        r'<span class="pill">'
        r'자동화 테스트:.*?'
        r'</span>',
        "",
        page,
        count=1,
    )

    badge = (
        '<span class="pill">'
        f'자동 갱신: {now}'
        f' · 소스 {source_ok}/3'
        '</span>'
    )

    if re.search(
        r'<span class="pill">'
        r'자동 갱신:.*?'
        r'</span>',
        page,
    ):

        return re.sub(
            r'<span class="pill">'
            r'자동 갱신:.*?'
            r'</span>',
            badge,
            page,
            count=1,
        )

    return page.replace(
        '<div class="meta">',
        '<div class="meta">'
        + badge,
        1,
    )


def inject_order(
    page: str,
    ordered_ids: list[str],
) -> str:

    if not ordered_ids:

        ordered_ids = (
            DEFAULT_ORDER[:]
        )

    array_text = (
        "["
        + ",".join(
            f'"{x}"'
            for x
            in ordered_ids
        )
        + "]"
    )

    page = re.sub(
        r'const dailyOrder='
        r'\[[^\]]*\];'
        r'\s*',
        "",
        page,
        count=1,
    )

    marker = (
        'const tabs='
        'document.'
        'getElementById("tabs");'
    )

    if marker not in page:

        return page

    page = page.replace(
        marker,
        f'const dailyOrder='
        f'{array_text};'
        f'\n'
        + marker,
        1,
    )

    sort_code = """
builds.sort((a,b)=>{
 const ai=dailyOrder.indexOf(a.id);
 const bi=dailyOrder.indexOf(b.id);

 const av=ai<0?999:ai;
 const bv=bi<0?999:bi;

 return av-bv;
});
"""

    if sort_code not in page:

        page = page.replace(
            'builds.forEach((b,i)=>{',
            sort_code
            + 'builds.forEach((b,i)=>{',
            1,
        )

    return page


def main() -> int:

    if not INDEX.exists():

        print(
            "[ERROR] "
            "index.html을 "
            "찾을 수 없습니다."
        )

        return 0

    texts = {}

    errors = []

    for (
        name,
        url,
    ) in SOURCES.items():

        try:

            texts[
                name
            ] = fetch_text(
                url
            )

            print(
                f"[OK] {name}: "
                f"{len(texts[name])} chars"
            )

        except Exception as e:

            errors.append(
                f"{name}: "
                f"{type(e).__name__}"
            )

            print(
                f"[WARN] "
                f"{name}: "
                f"{e}"
            )

    if texts:

        rows = rank_builds(
            texts
        )

    else:

        rows = []

    ranked_known = [
        r
        for r
        in rows
        if r[
            "known"
        ]
    ]

    enough_for_reorder = (
        len(
            ranked_known
        ) >= 5
        and
        len(
            texts
        ) >= 2
    )

    if enough_for_reorder:

        ordered_ids = [
            r[
                "id"
            ]
            for r
            in ranked_known
        ]

        degraded = False

        print(
            "[INFO] "
            "충분한 데이터 확보: "
            "상세 빌드 순서 갱신"
        )

    else:

        ordered_ids = (
            DEFAULT_ORDER[:]
        )

        degraded = True

        print(
            "[SAFE] "
            "데이터 부족: "
            "기존 상세 빌드 "
            "순서 유지 "
            f"(known="
            f"{len(ranked_known)}, "
            f"sources="
            f"{len(texts)})"
        )

    page = INDEX.read_text(
        encoding="utf-8"
    )

    page = ensure_css(
        page
    )

    page = inject_meta(
        page,
        build_meta_block(
            rows,
            errors,
            degraded,
        ),
    )

    page = update_badge(
        page,
        len(
            texts
        ),
    )

    page = inject_order(
        page,
        ordered_ids,
    )

    INDEX.write_text(
        page,
        encoding="utf-8",
    )

    print(
        "=== Detected ranking ==="
    )

    if rows:

        for (
            i,
            row,
        ) in enumerate(
            rows[:7],
            1,
        ):

            print(
                i,
                row[
                    "display"
                ],
                "score=",
                row[
                    "score"
                ],
                "hits=",
                row[
                    "source_hits"
                ],
            )

    else:

        print(
            "No ranked builds "
            "detected; "
            "page updated "
            "in safe mode."
        )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
