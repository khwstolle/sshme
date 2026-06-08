"""
Utility methods for interacting with OpenSSH.
"""

import glob
import re
import sys
from os import execvp, path

from .models import HostInfo

__all__ = ["HostInfo", "read_host_infos", "cmd", "exec"]

SSH_EXE = "ssh"
DEFAULT_CONFIG_PATH = "~/.ssh/config"

_RE_HOST = re.compile(r"^host\s+(.*)", re.IGNORECASE)
_RE_INCLUDE = re.compile(r"^include\s+(.*)", re.IGNORECASE)
_RE_DIRECTIVE = re.compile(r"^\s+(hostname|port|user)\s+(.*)", re.IGNORECASE)

_SSH_DIR = path.expanduser("~/.ssh")


def read_host_infos(config_path: str) -> list[HostInfo] | None:
    config_path = path.expanduser(config_path)
    if not path.isfile(config_path):
        return None
    return _read_config(config_path, set())


def _read_config(config_path: str, visited: set[str]) -> list[HostInfo]:
    real = path.realpath(config_path)
    if real in visited:
        return []
    visited.add(real)

    with open(config_path) as fh:
        lines = fh.read().splitlines()

    results: list[HostInfo] = []
    # Aliases from the current open Host block, and the accumulated directives.
    current_aliases: list[str] = []
    current_hostname: str | None = None
    current_port: int | None = None
    current_user: str | None = None

    def _flush() -> None:
        for alias in current_aliases:
            results.append(
                HostInfo(
                    name=alias,
                    hostname=current_hostname,
                    port=current_port,
                    user=current_user,
                    ssh_config_host=True,
                )
            )

    for line in lines:
        include_match = _RE_INCLUDE.match(line)
        if include_match:
            _flush()
            current_aliases, current_hostname, current_port, current_user = [], None, None, None
            pattern = path.expanduser(include_match.group(1).strip())
            if not path.isabs(pattern):
                pattern = path.join(_SSH_DIR, pattern)
            for included in sorted(glob.glob(pattern)):
                if path.isfile(included):
                    results.extend(_read_config(included, visited))
            continue

        host_match = _RE_HOST.match(line)
        if host_match:
            _flush()
            current_aliases = [h for h in host_match.group(1).split() if h]
            current_hostname, current_port, current_user = None, None, None
            continue

        directive_match = _RE_DIRECTIVE.match(line)
        if directive_match and current_aliases:
            key = directive_match.group(1).lower()
            value = directive_match.group(2).strip()
            if key == "hostname":
                current_hostname = value
            elif key == "port":
                try:
                    current_port = int(value)
                except ValueError:
                    print(
                        f"sshme: warning: invalid Port value {value!r} in {config_path}, ignoring",
                        file=sys.stderr,
                    )
            elif key == "user":
                current_user = value

    _flush()
    return results


def cmd(host: str, *args: str) -> list[str]:
    return [SSH_EXE, host, *args]


def exec(*args: str, **kwargs: str) -> None:
    argv = cmd(*args, **kwargs)
    execvp(argv[0], args=argv)
