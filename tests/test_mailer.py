from src import mailer


def test_send_success_multiple_recipients(monkeypatch):
    sent = {}
    def fake_send(msg):
        sent["to"] = msg["To"]
        sent["subject"] = msg["Subject"]
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(mailer, "_smtp_send", fake_send)
    ok = mailer.send("<p>hi</p>", "제목", ["a@x.com", "b@y.com"])
    assert ok is True
    assert sent["to"] == "a@x.com, b@y.com"
    assert sent["subject"] == "제목"


def test_send_empty_recipients_returns_false(monkeypatch):
    monkeypatch.setattr(mailer, "_smtp_send",
                        lambda msg: (_ for _ in ()).throw(AssertionError("should not send")))
    assert mailer.send("<p>hi</p>", "제목", []) is False


def test_send_retries_then_fails(monkeypatch):
    calls = {"n": 0}
    def boom(msg):
        calls["n"] += 1
        raise OSError("smtp down")
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(mailer, "_smtp_send", boom)
    ok = mailer.send("<p>hi</p>", "제목", ["you@gmail.com"])
    assert ok is False
    assert calls["n"] == 2  # 최초 + 재시도 1회
