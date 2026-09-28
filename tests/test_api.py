from moon_tracker import api


class _Resp:
    def __init__(self, status, body=None, json_raises=False):
        self.status_code = status
        self._body = body
        self._raises = json_raises
        self.ok = 200 <= status < 300

    def json(self):
        if self._raises:
            raise ValueError("no json")
        return self._body


def test_full_ack(monkeypatch):
    monkeypatch.setattr(
        api.requests, "post", lambda *a, **k: _Resp(200, {"ok": True, "accepted": ["activity:1"]}))
    r = api.post_activities("https://x", "t", [{"client_id": "activity:1"}])
    assert r.ok and r.accepted_ids == ["activity:1"]


def test_all_or_nothing_fallback(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _Resp(200, {"ok": True}))
    r = api.post_activities("https://x", "t", [{"client_id": "activity:1"}])
    assert r.ok and r.accepted_ids is None


def test_partial_ack_passes_through(monkeypatch):
    monkeypatch.setattr(
        api.requests, "post",
        lambda *a, **k: _Resp(200, {"ok": True, "accepted": ["activity:1"]}))
    r = api.post_activities("https://x", "t",
                            [{"client_id": "activity:1"}, {"client_id": "activity:2"}])
    assert r.ok and r.accepted_ids == ["activity:1"]


def test_retryable_vs_auth(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _Resp(500, {}))
    assert api.post_activities("https://x", "t", []).retryable is True
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _Resp(401, {}))
    r = api.post_activities("https://x", "t", [])
    assert r.retryable is False and r.auth_error is True
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _Resp(429, {}))
    assert api.post_activities("https://x", "t", []).retryable is True


def test_timeout_retryable(monkeypatch):
    import requests as rq

    def _boom(*a, **k):
        raise rq.Timeout()

    monkeypatch.setattr(api.requests, "post", _boom)
    assert api.post_activities("https://x", "t", []).retryable is True


def test_no_base_no_retry():
    r = api.post_activities("", "t", [])
    assert r.ok is False and r.retryable is False
