import os
import sys
from datetime import datetime, timezone, timedelta

from src import config, brief, render, mailer
from src.collectors import stocks, fx, weather, news

DOCS_DIR = "docs"
_KST = timezone(timedelta(hours=9))


def _now_kst() -> datetime:
    return datetime.now(_KST)


def run(dry_run: bool = False) -> dict:
    raw = {
        "stocks": stocks.collect(),
        "fx": fx.collect(),
        "weather": weather.collect(),
        "news": news.collect(),
    }
    b = brief.generate(raw)

    now = _now_kst()
    generated_at = now.strftime("%Y-%m-%d %H:%M KST")
    stamp = now.strftime("%Y-%m-%d-%H%M")
    date_str = now.strftime("%Y-%m-%d")

    web_url = config.SETTINGS["pages_base_url"].rstrip("/") + "/"
    web_html = render.render_web(raw, b, generated_at)
    email_html = render.render_email(b, web_url, generated_at)

    os.makedirs(os.path.join(DOCS_DIR, "archive"), exist_ok=True)
    web_path = os.path.join(DOCS_DIR, "index.html")
    archive_path = os.path.join(DOCS_DIR, "archive", f"{stamp}.html")
    for p in (web_path, archive_path):
        with open(p, "w", encoding="utf-8") as f:
            f.write(web_html)

    email_sent = False
    if not dry_run:
        subject = f"[AI 브리핑] {date_str} {now.strftime('%H:%M')}"
        email_sent = mailer.send(email_html, subject, config.SETTINGS["recipients"])

    return {"web_path": web_path, "archive_path": archive_path,
            "email_sent": email_sent}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = run(dry_run=dry)
    print(result)
