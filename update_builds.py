from pathlib import Path
from datetime import datetime, timezone, timedelta

path = Path("index.html")
html = path.read_text(encoding="utf-8")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst).strftime("%Y-%m-%d %H:%M")

marker = '<span class="pill">자동화 테스트:'
new_badge = f'<span class="pill">자동화 테스트: {now}</span>'

if marker in html:
    import re
    html = re.sub(
        r'<span class="pill">자동화 테스트:.*?</span>',
        new_badge,
        html
    )
else:
    target = '<div class="meta">'
    html = html.replace(target, target + new_badge, 1)

path.write_text(html, encoding="utf-8")

print(f"index.html updated: {now}")
