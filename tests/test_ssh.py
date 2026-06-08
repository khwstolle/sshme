from sshme import ssh
from sshme.models import HostInfo


def _names(infos):
    return [h.name for h in infos]


def test_read_host_infos_basic(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host server1\n    HostName 10.0.0.1\nHost server2\n    HostName 10.0.0.2\n")
    assert _names(ssh.read_host_infos(str(config))) == ["server1", "server2"]


def test_read_host_infos_missing_file():
    assert ssh.read_host_infos("/nonexistent/path/config") is None


def test_read_host_infos_empty(tmp_path):
    config = tmp_path / "config"
    config.write_text("")
    assert ssh.read_host_infos(str(config)) == []


def test_read_host_infos_single_char_host_included(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host a\n    HostName 10.0.0.1\nHost myserver\n    HostName 10.0.0.2\n")
    assert _names(ssh.read_host_infos(str(config))) == ["a", "myserver"]


def test_read_host_infos_wildcard_included(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host *\n    ServerAliveInterval 60\nHost myserver\n    HostName 10.0.0.1\n")
    assert _names(ssh.read_host_infos(str(config))) == ["*", "myserver"]


def test_read_host_infos_does_not_match_hostname_directive(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host myserver\n    HostName 192.168.1.1\n")
    assert _names(ssh.read_host_infos(str(config))) == ["myserver"]


def test_read_host_infos_metadata(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host server1\n    HostName 10.0.0.1\n    Port 2222\n    User admin\n")
    infos = ssh.read_host_infos(str(config))
    assert infos == [
        HostInfo(
            name="server1",
            hostname="10.0.0.1",
            port=2222,
            user="admin",
            ssh_config_host=True,
        )
    ]


def test_read_host_infos_metadata_case_insensitive(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host server1\n    hostname 10.0.0.1\n    PORT 22\n    USER root\n")
    infos = ssh.read_host_infos(str(config))
    assert infos[0].hostname == "10.0.0.1"
    assert infos[0].port == 22
    assert infos[0].user == "root"


def test_read_host_infos_multi_alias(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host a b\n    HostName 10.0.0.1\n    User shared\n")
    infos = ssh.read_host_infos(str(config))
    assert _names(infos) == ["a", "b"]
    assert infos[0].hostname == "10.0.0.1"
    assert infos[1].hostname == "10.0.0.1"
    assert infos[0].user == "shared"
    assert infos[1].user == "shared"


def test_read_host_infos_directives_scoped_to_block(tmp_path):
    config = tmp_path / "config"
    config.write_text("Host server1\n    HostName 10.0.0.1\nHost server2\n    HostName 10.0.0.2\n")
    infos = ssh.read_host_infos(str(config))
    assert infos[0].hostname == "10.0.0.1"
    assert infos[1].hostname == "10.0.0.2"


def test_read_host_infos_with_include(tmp_path):
    included = tmp_path / "extra"
    included.write_text("Host server2\n")
    config = tmp_path / "config"
    config.write_text(f"Include {included}\nHost server1\n")
    assert _names(ssh.read_host_infos(str(config))) == ["server2", "server1"]


def test_read_host_infos_include_glob(tmp_path):
    conf_d = tmp_path / "conf.d"
    conf_d.mkdir()
    (conf_d / "work.conf").write_text("Host work-server\n")
    (conf_d / "home.conf").write_text("Host home-server\n")
    config = tmp_path / "config"
    config.write_text(f"Include {conf_d}/*.conf\nHost main\n")
    names = _names(ssh.read_host_infos(str(config)))
    assert "work-server" in names
    assert "home-server" in names
    assert "main" in names


def test_read_host_infos_include_circular(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text(f"Include {b}\nHost server-a\n")
    b.write_text(f"Include {a}\nHost server-b\n")
    assert _names(ssh.read_host_infos(str(a))) == ["server-b", "server-a"]


def test_read_host_infos_include_missing(tmp_path):
    config = tmp_path / "config"
    config.write_text(f"Include {tmp_path}/nonexistent.conf\nHost server1\n")
    assert _names(ssh.read_host_infos(str(config))) == ["server1"]


def test_read_host_infos_invalid_port_warns(tmp_path, capsys):
    config = tmp_path / "config"
    config.write_text("Host server1\n    Port notanumber\n")
    infos = ssh.read_host_infos(str(config))
    assert infos[0].port is None
    assert "invalid Port" in capsys.readouterr().err


def test_cmd_basic():
    assert ssh.cmd("server") == ["ssh", "server"]


def test_cmd_with_extra_args():
    assert ssh.cmd("server", "-p", "2222") == ["ssh", "server", "-p", "2222"]
