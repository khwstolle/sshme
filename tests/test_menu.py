import questionary
from sshme import menu
from sshme.menu import _subtitle
from sshme.models import HostInfo

# ── _subtitle ──────────────────────────────────────────────────────────────────


def test_subtitle_all_fields():
    h = HostInfo(name="s", hostname="10.0.0.1", port=2222, user="admin", description="Dev box")
    assert _subtitle(h) == "10.0.0.1:2222 (admin) — Dev box"


def test_subtitle_hostname_only():
    h = HostInfo(name="s", hostname="10.0.0.1")
    assert _subtitle(h) == "10.0.0.1"


def test_subtitle_hostname_and_port():
    h = HostInfo(name="s", hostname="10.0.0.1", port=22)
    assert _subtitle(h) == "10.0.0.1:22"


def test_subtitle_port_only_no_leading_colon():
    h = HostInfo(name="s", port=2222)
    assert _subtitle(h) == "2222"


def test_subtitle_description_only():
    h = HostInfo(name="s", description="My server")
    assert _subtitle(h) == "My server"


def test_subtitle_user_only():
    h = HostInfo(name="s", user="admin")
    assert _subtitle(h) == "(admin)"


def test_subtitle_none_when_all_empty():
    h = HostInfo(name="s")
    assert _subtitle(h) is None


# ── input_wildcard ─────────────────────────────────────────────────────────────


def test_input_wildcard_no_wildcard_returns_same_object():
    host = HostInfo(name="server1", ssh_config_host=True)
    assert menu.input_wildcard(host) is host


def test_input_wildcard_substitutes(monkeypatch):
    monkeypatch.setattr(
        questionary, "text", lambda *a, **kw: type("Q", (), {"ask": lambda self: "prod"})()
    )
    host = HostInfo(name="web-*", hostname="10.0.0.1", ssh_config_host=True)
    result = menu.input_wildcard(host)
    assert result.name == "web-prod"
    assert result.hostname == "10.0.0.1"
    assert result.ssh_config_host is True


def test_input_wildcard_substitutes_first_occurrence_only(monkeypatch):
    monkeypatch.setattr(
        questionary, "text", lambda *a, **kw: type("Q", (), {"ask": lambda self: "x"})()
    )
    host = HostInfo(name="*.*.example.com")
    result = menu.input_wildcard(host)
    assert result.name == "x.*.example.com"


def test_input_wildcard_empty_string_returns_original(monkeypatch):
    monkeypatch.setattr(
        questionary, "text", lambda *a, **kw: type("Q", (), {"ask": lambda self: ""})()
    )
    host = HostInfo(name="web-*")
    assert menu.input_wildcard(host) is host


def test_input_wildcard_cancel_returns_original(monkeypatch):
    monkeypatch.setattr(
        questionary, "text", lambda *a, **kw: type("Q", (), {"ask": lambda self: None})()
    )
    host = HostInfo(name="web-*")
    assert menu.input_wildcard(host) is host


# ── input_key ──────────────────────────────────────────────────────────────────


def test_input_key_returns_selected_path(monkeypatch, tmp_path):
    key = tmp_path / "id_ed25519"
    key.touch()
    monkeypatch.setattr(
        questionary,
        "select",
        lambda *a, **kw: type("Q", (), {"ask": lambda self: key})(),
    )
    result = menu.input_key([key])
    assert result == key


def test_input_key_returns_none_on_cancel(monkeypatch, tmp_path):
    key = tmp_path / "id_ed25519"
    key.touch()
    monkeypatch.setattr(
        questionary,
        "select",
        lambda *a, **kw: type("Q", (), {"ask": lambda self: None})(),
    )
    assert menu.input_key([key]) is None
