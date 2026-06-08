from sshme import tmux


def test_is_active_true(monkeypatch):
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    assert tmux.is_active() is True


def test_is_active_false(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    assert tmux.is_active() is False


def test_find_window_found(monkeypatch):
    monkeypatch.setattr(tmux, "list_windows", lambda: ["0,base", "1,SSH:myserver", "2,other"])
    assert tmux.find_window("SSH:myserver") == "1"


def test_find_window_not_found(monkeypatch):
    monkeypatch.setattr(tmux, "list_windows", lambda: ["0,base", "1,other"])
    assert tmux.find_window("SSH:missing") is None


def test_find_window_name_with_comma(monkeypatch):
    # maxsplit=1 ensures names containing commas are matched correctly.
    monkeypatch.setattr(tmux, "list_windows", lambda: ["0,SSH:user@host,2222"])
    assert tmux.find_window("SSH:user@host,2222") == "0"
