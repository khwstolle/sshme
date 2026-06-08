from sshme import config
from sshme.config import AppConfig
from sshme.models import HostInfo


def test_no_files(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    result = config.load(cwd=tmp_path)
    assert result == AppConfig(hosts=[])


def test_user_config_parsed(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    (xdg / "sshme").mkdir(parents=True)
    (xdg / "sshme" / "config.toml").write_text(
        '[[hosts]]\nname = "myserver"\nhostname = "10.0.0.1"\nport = 22\nuser = "admin"\ndescription = "My server"\n'
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    result = config.load(cwd=tmp_path)
    assert result.hosts == [
        HostInfo(
            name="myserver", hostname="10.0.0.1", port=22, user="admin", description="My server"
        )
    ]


def test_project_dotfile_found_in_cwd(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "proj"\n')
    result = config.load(cwd=tmp_path)
    assert [h.name for h in result.hosts] == ["proj"]


def test_project_dotfile_wins_over_plain(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "dot"\n')
    (tmp_path / "sshme.toml").write_text('[[hosts]]\nname = "plain"\n')
    result = config.load(cwd=tmp_path)
    assert [h.name for h in result.hosts] == ["dot"]


def test_project_found_in_parent(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "parent-host"\n')
    sub = tmp_path / "sub" / "sub2"
    sub.mkdir(parents=True)
    result = config.load(cwd=sub)
    assert [h.name for h in result.hosts] == ["parent-host"]


def test_project_shadows_user_on_name_conflict(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    (xdg / "sshme").mkdir(parents=True)
    (xdg / "sshme" / "config.toml").write_text('[[hosts]]\nname = "shared"\ndescription = "user"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "shared"\ndescription = "project"\n')
    result = config.load(cwd=tmp_path)
    assert len(result.hosts) == 1
    assert result.hosts[0].description == "project"


def test_user_entries_preserved_if_not_shadowed(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    (xdg / "sshme").mkdir(parents=True)
    (xdg / "sshme" / "config.toml").write_text('[[hosts]]\nname = "user-only"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "proj-only"\n')
    result = config.load(cwd=tmp_path)
    names = [h.name for h in result.hosts]
    assert "proj-only" in names
    assert "user-only" in names


def test_port_parsed_as_int(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "s"\nport = 2222\n')
    result = config.load(cwd=tmp_path)
    assert result.hosts[0].port == 2222
    assert isinstance(result.hosts[0].port, int)


def test_missing_name_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text(
        '[[hosts]]\nhostname = "10.0.0.1"\n\n[[hosts]]\nname = "valid"\n'
    )
    result = config.load(cwd=tmp_path)
    assert [h.name for h in result.hosts] == ["valid"]


def test_unknown_keys_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "s"\nunknown_key = "whatever"\n')
    result = config.load(cwd=tmp_path)
    assert result.hosts[0].name == "s"


def test_malformed_toml_warns_and_returns_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text("this is not toml ][[[")
    result = config.load(cwd=tmp_path)
    assert result == AppConfig(hosts=[])
    assert "could not parse" in capsys.readouterr().err


def test_invalid_port_string_in_toml_returns_none_port(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / ".sshme.toml").write_text('[[hosts]]\nname = "s"\nport = "not-a-number"\n')
    result = config.load(cwd=tmp_path)
    assert result.hosts[0].port is None
