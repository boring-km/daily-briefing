from datetime import datetime
from src import main


def test_run_dry_writes_files_no_email(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(main.stocks, "collect", lambda: {"ok": True, "groups": {}})
    monkeypatch.setattr(main.fx, "collect", lambda: {"ok": True, "rates": []})
    monkeypatch.setattr(main.weather, "collect", lambda: {"ok": True, "locations": []})
    monkeypatch.setattr(main.news, "collect",
                        lambda: {"ok": True, "naver_economy": [], "global_semi": []})
    monkeypatch.setattr(main.brief, "generate",
                        lambda raw: {"sections": {"markets": "", "memory": "",
                        "weather": "", "news": ""}, "summary": "요약"})
    sent = {"called": False}
    monkeypatch.setattr(main.mailer, "send",
                        lambda *a, **k: sent.__setitem__("called", True) or True)
    monkeypatch.setattr(main, "_now_kst", lambda: datetime(2026, 6, 19, 7, 0))

    out = main.run(dry_run=True)
    assert out["email_sent"] is False
    assert sent["called"] is False
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "archive" / "2026-06-19-0700.html").exists()


def test_run_sends_email(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DOCS_DIR", str(tmp_path))
    for mod in (main.stocks, main.fx, main.weather, main.news):
        pass
    monkeypatch.setattr(main.stocks, "collect", lambda: {"ok": True, "groups": {}})
    monkeypatch.setattr(main.fx, "collect", lambda: {"ok": True, "rates": []})
    monkeypatch.setattr(main.weather, "collect", lambda: {"ok": True, "locations": []})
    monkeypatch.setattr(main.news, "collect",
                        lambda: {"ok": True, "naver_economy": [], "global_semi": []})
    monkeypatch.setattr(main.brief, "generate",
                        lambda raw: {"sections": {"markets": "", "memory": "",
                        "weather": "", "news": ""}, "summary": "요약"})
    captured = {}
    monkeypatch.setattr(main.mailer, "send",
                        lambda html, subject, recipient: captured.update(
                            {"subject": subject, "to": recipient}) or True)
    monkeypatch.setattr(main, "_now_kst", lambda: datetime(2026, 6, 19, 19, 0))

    out = main.run(dry_run=False)
    assert out["email_sent"] is True
    assert "2026-06-19" in captured["subject"]
