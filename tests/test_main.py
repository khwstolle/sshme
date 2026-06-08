import sys

import pytest
from sshme import config, history, menu, tmux
from sshme.__main__ import main
from sshme.config import AppConfig
from sshme.models import HostInfo


def _h(name: str, **kwargs) -> HostInfo:
    return HostInfo(name=name, ssh_config_host=True, **kwargs)


def _no_config(monkeypatch):
    monkeypatch.setattr(config, "load", lambda **kw: AppConfig(hosts=[]))


@pytest.fixture
def one_host_config(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host server1\n    HostName 10.0.0.1\n")
    return cfg


# ── Error paths ────────────────────────────────────────────────────────────────


def test_main_missing_config_and_no_toml(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", "/nonexistent/config"])
    _no_config(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "Configuration not found" in capsys.readouterr().out


def test_main_empty_config_and_no_toml(monkeypatch, capsys, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg)])
    _no_config(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "No hosts configured" in capsys.readouterr().out


def test_main_missing_ssh_config_with_config_toml_hosts(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", "/nonexistent/config"])
    monkeypatch.setattr(
        config,
        "load",
        lambda **kw: AppConfig(hosts=[HostInfo(name="devbox", hostname="192.168.1.1")]),
    )
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(
        menu, "input_profile", lambda *a, **kw: HostInfo(name="devbox", hostname="192.168.1.1")
    )
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr("sshme.__main__.execvp", lambda prog, args: executed.append((prog, args)))
    main()
    assert executed[0][0] == "ssh"


# ── Cancel ─────────────────────────────────────────────────────────────────────


def test_main_cancel_exits_cleanly(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


# ── SSH direct ─────────────────────────────────────────────────────────────────


def test_main_ssh_exec_direct(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1"])]


def test_main_passthrough_args(monkeypatch, one_host_config):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--", "-L", "8080:localhost:8080"]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "-L", "8080:localhost:8080"])]


# ── -l user flag ───────────────────────────────────────────────────────────────


def test_main_user_flag_direct(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "-l", "root"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "-l", "root"])]


def test_main_user_flag_prompts(monkeypatch, one_host_config):
    import questionary as q

    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "-l"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr(q, "text", lambda *a, **kw: type("Q", (), {"ask": lambda self: "admin"})())
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "-l", "admin"])]


def test_main_user_flag_absent(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1"])]


# ── tmux integration ───────────────────────────────────────────────────────────


def test_main_tmux_selects_existing_window(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: True)
    monkeypatch.setattr(tmux, "find_window", lambda _: "3")
    selected = []
    monkeypatch.setattr(tmux, "select_window", lambda wid: selected.append(wid))
    main()
    assert selected == ["3"]


def test_main_tmux_opens_new_window(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: True)
    monkeypatch.setattr(tmux, "find_window", lambda _: None)
    new_windows = []
    monkeypatch.setattr(tmux, "exec_new_window", lambda name, *cmd: new_windows.append((name, cmd)))
    main()
    assert new_windows == [("SSH:server1", ("ssh", "server1"))]


# ── sftp mode ──────────────────────────────────────────────────────────────────


def test_main_sftp_mode(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "--sftp"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("sftp", ["sftp", "server1"])]


def test_main_sftp_with_user(monkeypatch, one_host_config):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--sftp", "-l", "root"]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("sftp", ["sftp", "root@server1"])]


def test_main_sftp_passthrough_before_host(monkeypatch, one_host_config):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--sftp", "--", "-b", "batch.txt"]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    # extra args come before the target
    assert executed == [("sftp", ["sftp", "-b", "batch.txt", "server1"])]


def test_main_sftp_port_uses_capital_P(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg), "--sftp"])
    monkeypatch.setattr(
        config,
        "load",
        lambda **kw: AppConfig(hosts=[HostInfo(name="devbox", hostname="192.168.1.1", port=2222)]),
    )
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(
        menu,
        "input_profile",
        lambda *a, **kw: HostInfo(name="devbox", hostname="192.168.1.1", port=2222),
    )
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("sftp", ["sftp", "-P", "2222", "192.168.1.1"])]


# ── copy-id mode ───────────────────────────────────────────────────────────────


def test_main_copy_id_mode(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "--copy-id"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh-copy-id", ["ssh-copy-id", "server1"])]


def test_main_copy_id_with_user(monkeypatch, one_host_config):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--copy-id", "-l", "root"]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh-copy-id", ["ssh-copy-id", "root@server1"])]


def test_main_sftp_copy_id_mutually_exclusive(monkeypatch, one_host_config, capsys):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--sftp", "--copy-id"]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


# ── config-only host ───────────────────────────────────────────────────────────


def test_main_config_only_host_by_hostname(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg)])
    monkeypatch.setattr(
        config,
        "load",
        lambda **kw: AppConfig(
            hosts=[HostInfo(name="devbox", hostname="192.168.1.42", port=2222, user="dev")]
        ),
    )
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(
        menu,
        "input_profile",
        lambda *a, **kw: HostInfo(name="devbox", hostname="192.168.1.42", port=2222, user="dev"),
    )
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    # ssh_config_host=False: connects by hostname with user@host format and -p
    assert executed == [("ssh", ["ssh", "dev@192.168.1.42", "-p", "2222"])]


def test_main_config_host_annotates_ssh_host(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host server1\n    HostName 10.0.0.1\n")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg)])
    monkeypatch.setattr(
        config,
        "load",
        lambda **kw: AppConfig(hosts=[HostInfo(name="server1", description="Production")]),
    )
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    # Capture what input_profile receives to verify description was merged
    received = []

    def mock_input_profile(*hosts, **kw):
        received.extend(hosts)
        return hosts[0]

    monkeypatch.setattr(menu, "input_profile", mock_input_profile)
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr("sshme.__main__.execvp", lambda prog, args: None)
    main()
    # The merged host should be ssh_config_host=True (from SSH config) with description from config.toml
    assert received[0].ssh_config_host is True
    assert received[0].description == "Production"
    assert received[0].hostname == "10.0.0.1"


# ── MRU history ordering ───────────────────────────────────────────────────────


def test_main_recent_hosts_ordered_first(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host server1\nHost server2\nHost server3\n")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: ["server3", "server1"])
    monkeypatch.setattr(history, "record", lambda _: None)
    seen_order = []

    def mock_input_profile(*hosts, **kw):
        seen_order.extend(hosts)
        return hosts[0]

    monkeypatch.setattr(menu, "input_profile", mock_input_profile)
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr("sshme.__main__.execvp", lambda prog, args: None)
    main()
    assert [h.name for h in seen_order[:3]] == ["server3", "server1", "server2"]


def test_main_records_profile_not_expanded_host(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host prod-*\n")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg)])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    recorded = []
    monkeypatch.setattr(history, "record", lambda h: recorded.append(h))
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("prod-*"))
    monkeypatch.setattr(
        menu,
        "input_wildcard",
        lambda h: HostInfo(name=h.name.replace("*", "1"), ssh_config_host=True),
    )
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr("sshme.__main__.execvp", lambda prog, args: None)
    main()
    assert recorded == ["prod-*"]


# ── --tmux remote session flag ─────────────────────────────────────────────────


def test_main_tmux_flag_adds_remote_session_cmd(monkeypatch, one_host_config):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "--tmux"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "tmux new-session -As ssh"])]


# ── alias vs IP: sftp and copy-id must not bypass SSH config ───────────────────


def test_main_sftp_uses_alias_not_hostname(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host myalias\n    HostName 10.0.0.5\n    Port 2222\n")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg), "--sftp"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(
        menu, "input_profile", lambda *a, **kw: _h("myalias", hostname="10.0.0.5", port=2222)
    )
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("sftp", ["sftp", "myalias"])]


def test_main_copy_id_uses_alias_not_hostname(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host myalias\n    HostName 10.0.0.5\n")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg), "--copy-id"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("myalias", hostname="10.0.0.5"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh-copy-id", ["ssh-copy-id", "myalias"])]


def test_main_copy_id_direct_host_with_port(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("")
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(cfg), "--copy-id"])
    monkeypatch.setattr(
        config,
        "load",
        lambda **kw: AppConfig(hosts=[HostInfo(name="devbox", hostname="192.168.1.1", port=2222)]),
    )
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(
        menu,
        "input_profile",
        lambda *a, **kw: HostInfo(name="devbox", hostname="192.168.1.1", port=2222),
    )
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh-copy-id", ["ssh-copy-id", "-p", "2222", "192.168.1.1"])]


# ── -i identity file flag ──────────────────────────────────────────────────────


def test_main_key_flag_direct(monkeypatch, one_host_config):
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "-i", "/home/user/.ssh/work_key"]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "-i", "/home/user/.ssh/work_key"])]


def test_main_key_flag_prompts(monkeypatch, one_host_config, tmp_path):
    key = tmp_path / "id_ed25519"
    key.touch()
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "-i"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr("sshme.__main__._discover_keys", lambda: [key])
    monkeypatch.setattr(menu, "input_key", lambda keys: keys[0])
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh", ["ssh", "server1", "-i", str(key)])]


def test_main_key_flag_no_keys_found(monkeypatch, one_host_config, capsys):
    monkeypatch.setattr(sys, "argv", ["sshme", "--config", str(one_host_config), "-i"])
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    monkeypatch.setattr(tmux, "is_active", lambda: False)
    monkeypatch.setattr("sshme.__main__._discover_keys", lambda: [])
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert "no identity files" in capsys.readouterr().err
    assert executed == [("ssh", ["ssh", "server1"])]


def test_main_sftp_with_key(monkeypatch, one_host_config, tmp_path):
    key = tmp_path / "id_ed25519"
    key.touch()
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--sftp", "-i", str(key)]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("sftp", ["sftp", "-i", str(key), "server1"])]


def test_main_copy_id_with_key(monkeypatch, one_host_config, tmp_path):
    key = tmp_path / "id_ed25519"
    key.touch()
    monkeypatch.setattr(
        sys, "argv", ["sshme", "--config", str(one_host_config), "--copy-id", "-i", str(key)]
    )
    _no_config(monkeypatch)
    monkeypatch.setattr(history, "load", lambda: [])
    monkeypatch.setattr(history, "record", lambda _: None)
    monkeypatch.setattr(menu, "input_profile", lambda *a, **kw: _h("server1"))
    monkeypatch.setattr(menu, "input_wildcard", lambda h: h)
    executed = []
    monkeypatch.setattr(
        "sshme.__main__.execvp", lambda prog, args: executed.append((prog, list(args)))
    )
    main()
    assert executed == [("ssh-copy-id", ["ssh-copy-id", "-i", str(key), "server1"])]
