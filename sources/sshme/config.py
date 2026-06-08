"""
Project-local and user-local config.toml loading.
"""

import dataclasses
import os
import sys
import tomllib
from pathlib import Path

from .models import HostInfo

__all__ = ["AppConfig", "load"]


@dataclasses.dataclass
class AppConfig:
    hosts: list[HostInfo] = dataclasses.field(default_factory=list)


def _user_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return base / "sshme" / "config.toml"


def _project_config_path(cwd: Path) -> Path | None:
    for directory in [cwd, *cwd.parents]:
        for name in (".sshme.toml", "sshme.toml"):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def _parse_file(path: Path) -> list[HostInfo]:
    try:
        text = path.read_text()
    except FileNotFoundError:
        return []
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        print(f"sshme: warning: could not parse {path}: {exc}", file=sys.stderr)
        return []
    hosts = []
    for entry in data.get("hosts", []):
        name = entry.get("name")
        if not name:
            continue
        port_raw = entry.get("port")
        try:
            port = int(port_raw) if port_raw is not None else None
        except (TypeError, ValueError):
            port = None
        hosts.append(
            HostInfo(
                name=name,
                hostname=entry.get("hostname"),
                port=port,
                user=entry.get("user"),
                description=entry.get("description"),
                ssh_config_host=False,
            )
        )
    return hosts


def load(cwd: Path | None = None) -> AppConfig:
    if cwd is None:
        cwd = Path.cwd()

    user_hosts = _parse_file(_user_config_path())
    project_path = _project_config_path(cwd)
    project_hosts = _parse_file(project_path) if project_path else []

    # Project-local shadows user-local by name.
    project_names = {h.name for h in project_hosts}
    merged = [*project_hosts, *(h for h in user_hosts if h.name not in project_names)]
    return AppConfig(hosts=merged)
