from sshme import history


def test_load_empty_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "_HISTORY_PATH", tmp_path / "nonexistent.json")
    assert history.load() == []


def test_record_and_load(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "_HISTORY_PATH", tmp_path / "history.json")
    history.record("server1")
    assert history.load() == ["server1"]


def test_recent_first(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "_HISTORY_PATH", tmp_path / "history.json")
    history.record("server1")
    history.record("server2")
    assert history.load() == ["server2", "server1"]


def test_deduplicates(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "_HISTORY_PATH", tmp_path / "history.json")
    history.record("server1")
    history.record("server2")
    history.record("server1")
    assert history.load() == ["server1", "server2"]


def test_truncated_to_max(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "_HISTORY_PATH", tmp_path / "history.json")
    for i in range(history.HISTORY_MAX + 5):
        history.record(f"server{i}")
    assert len(history.load()) == history.HISTORY_MAX
